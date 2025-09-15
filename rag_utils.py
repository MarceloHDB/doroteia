import json
import os
import hashlib
import numpy as np
import faiss
import requests
import re
from sentence_transformers import SentenceTransformer
from datetime import datetime

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# === Variáveis globais ===
modelo = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
DOCUMENTOS = []
INDEX = None
ULTIMO_HASH = None
ARQUIVO_JSON = "dados.json"

# === Prompt do sistema para o modelo Mistral ===
SYSTEM_PROMPT = """
Você é um assistente especializado em responder perguntas sobre riscos e deficiências de segurança da informação com base em dados estruturados fornecidos.

📌 Regras obrigatórias:
- Use apenas as informações explicitamente fornecidas no contexto.
- Nunca invente, deduza ou estimule inferências sobre status, datas ou responsáveis.
- Não combine ou cruze dados de pontos diferentes. Cada ponto deve ser tratado individualmente.
"""

# === Funções auxiliares ===
def calcular_hash_arquivo(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def extrair_observacao_mais_recente(texto):
    if not texto or not texto.strip():
        return "Sem observacoes"

    pattern = r'(\d{2}/\d{2}/\d{4}).*?(?=\n|$)'
    matches = list(re.finditer(pattern, texto, flags=re.DOTALL))

    if not matches:
        return texto.strip()

    partes = []
    for match in matches:
        data_str = match.group(1)
        try:
            data = datetime.strptime(data_str, "%d/%m/%Y")
            inicio = match.start()
            fim = next((m.start() for m in matches if m.start() > inicio), len(texto))
            partes.append((data, texto[inicio:fim].strip()))
        except ValueError:
            continue

    if partes:
        partes.sort(key=lambda x: x[0], reverse=True)
        return partes[0][1]
    else:
        return texto.strip()

def format_entry(entry):
    id_ = entry.get('id_deficiencia') or entry.get('ID DEFICIÊNCIA') or "Não informado"
    area = entry.get('area_de_origem') or entry.get('ÁREA DE ORIGEM') or "Não informado"
    risco = entry.get('deficiencia') or entry.get('DEFICIÊNCIA') or entry.get('RISCO') or "Não informado"
    status = entry.get('status') or entry.get('STATUS') or "Não informado"
    observacao = extrair_observacao_mais_recente(
        entry.get('observacao') or entry.get('OBSERVAÇÃO') or entry.get('update') or ""
    )
    responsavel = entry.get('gerente_responsavel') or entry.get('GERENTE RESPONSÁVEL') or "Não informado"
    criticidade = entry.get('criticidade') or entry.get('CRITICIDADE') or "Não informado"
    abertura = entry.get('data_abertura_deficiencia') or entry.get('DATA ABERTURA DEFICIÊNCIA') or "Data não informada"
    encerramento = entry.get('data_encerramento') or entry.get('DATA ENCERRAMENTO') or "Não informado"
    
    prazo_area = "Não informado"  # campo removido da versão anterior

    def extrair_ano(data):
        if data and isinstance(data, str) and len(data) >= 4 and "/" in data:
            return data[-4:]
        return "Ano não informado"

    ano_abertura = extrair_ano(abertura)
    ano_encerramento = extrair_ano(encerramento)

    return (
        f"ID: {id_}\n"
        f"Área: {area}\n"
        f"Responsável: {responsavel}\n"
        f"Risco: {risco}\n"
        f"Status: {status}\n"
        f"Criticidade: {criticidade}\n"
        f"Prazo da área: {prazo_area}\n"
        f"Abertura: {abertura}\n"
        f"Ano de abertura: {ano_abertura}\n"
        f"Encerramento: {encerramento}\n"
        f"Ano de encerramento: {ano_encerramento}\n"
        f"Observação: {observacao}"
    )

def extrair_ids(pergunta: str):
    p = pergunta.lower()
    candidatos = re.findall(r"\b\d{3,6}\b", p)
    ids_validos = []

    for num in candidatos:
        if 1900 <= int(num) <= 2100:
            if re.search(rf"(id|ponto|risco|deficiência)[^\d]{{0,5}}{num}\b", p):
                ids_validos.append(num)
        else:
            ids_validos.append(num)

    return list(dict.fromkeys(ids_validos))[:3]

def carregar_index_if_needed():
    global DOCUMENTOS, INDEX, ULTIMO_HASH
    hash_atual = calcular_hash_arquivo(ARQUIVO_JSON)

    if hash_atual != ULTIMO_HASH:
        print("📦 JSON atualizado. Recarregando dados...")
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        DOCUMENTOS = [format_entry(entry) for entry in data]
        embeddings = modelo.encode(DOCUMENTOS, show_progress_bar=False)
        INDEX = faiss.IndexFlatL2(embeddings[0].shape[0])
        INDEX.add(np.array(embeddings))
        ULTIMO_HASH = hash_atual
    else:
        print("✅ JSON não mudou. Usando cache.")

def _escolher_top_k(pergunta: str) -> int:
    p = pergunta.lower()
    if re.search(r"\bquantos?\b", p):
        return 50
    if re.search(r"\b(quais|liste?|lista|mostre?)\b", p):
        return 20
    return 10

def buscar_documento(pergunta: str):
    carregar_index_if_needed()
    ids_extraidos = extrair_ids(pergunta)

    if ids_extraidos:
        print(f"🔎 IDs detectados na pergunta: {ids_extraidos}")
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        encontrados = []
        for id_ in ids_extraidos:
            id_limpo = id_.strip().lower()
            match = next((
                format_entry(entry) for entry in data
                if str(entry.get("id_deficiencia", "")).strip().lower() == id_limpo
            ), None)
            encontrados.append(match or f"ID {id_} não encontrado")

        return encontrados

    top_k = _escolher_top_k(pergunta)
    query_emb = modelo.encode([pergunta])
    dist, idx = INDEX.search(np.array(query_emb), top_k)
    return [DOCUMENTOS[i] for i in idx[0]]

def perguntar_ollama(contextos, pergunta):
    if not contextos or all(c.strip() == "" for c in contextos):
        return "Contexto não encontrado."

    if isinstance(contextos, list):
        contexto_formatado = "\n\n".join([f"[Contexto do ponto {i+1}]\n{ctx}" for i, ctx in enumerate(contextos)])
    else:
        contexto_formatado = contextos

    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{contexto_formatado}\n\nPergunta: {pergunta}"}
        ],
        "stream": False
    }

    response = requests.post("http://localhost:11434/api/chat", json=payload)
    result = response.json()
    return result.get("message", {}).get("content", "Erro ao gerar resposta.")

