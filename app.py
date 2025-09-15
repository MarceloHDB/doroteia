from flask import Flask, render_template, request
from rag_utils import buscar_documento, perguntar_ollama
import re

app = Flask(__name__)

def normalizar_pergunta(pergunta):
    substituicoes = {
        "fechado": "encerrado",
        "foi fechado": "foi encerrado",
        "fechou": "encerrado",
        "data de fechamento": "data de encerramento"
    }
    for original, novo in substituicoes.items():
        pergunta = pergunta.replace(original, novo)
    return pergunta

def extrair_filtros(pergunta):
    filtros = {}

    # Filtro ano
    ano_match = re.search(r"(?:em\s+)?(\d{4})", pergunta)
    if ano_match:
        filtros["ano"] = ano_match.group(1)

    # Filtro área
    area_match = re.search(r"área\s+(\w+)", pergunta, re.IGNORECASE)
    if area_match:
        filtros["área"] = area_match.group(1).lower()

    # Filtro responsável
    responsavel_match = re.search(r"responsável\s+([\w\s]+)", pergunta, re.IGNORECASE)
    if responsavel_match:
        filtros["responsável"] = responsavel_match.group(1).strip().lower()

    return filtros

@app.route("/", methods=["GET", "POST"])
def index():
    resposta = ""
    contextos = []
    pergunta = ""

    if request.method == "POST":
        pergunta = request.form["pergunta"]
        pergunta_normalizada = normalizar_pergunta(pergunta)
        contextos = buscar_documento(pergunta_normalizada)

        filtros = extrair_filtros(pergunta_normalizada)

        # Contagem de pontos encerrados
        if re.search(r"quantos?\s+pontos?.*encerrados?", pergunta_normalizada.lower()):
            total = 0
            for ctx in contextos:
                if "ano" in filtros and not re.search(r"Encerramento:\s*\d{2}/\d{2}/" + filtros["ano"], ctx):
                    continue
                if "área" in filtros and f"área: {filtros['área']}" not in ctx.lower():
                    continue
                if "responsável" in filtros and f"responsável: {filtros['responsável']}" not in ctx.lower():
                    continue
                total += 1
            resposta = f"Foram encontrados {total} pontos encerrados"
            if "ano" in filtros:
                resposta += f" em {filtros['ano']}"
            if "área" in filtros:
                resposta += f" na área {filtros['área'].capitalize()}"
            if "responsável" in filtros:
                resposta += f" com responsável {filtros['responsável'].capitalize()}"
            resposta += "."
        else:
            resposta = perguntar_ollama(contextos, pergunta_normalizada)

    return render_template("index.html", resposta=resposta, contexto=contextos, pergunta=pergunta)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=True)

