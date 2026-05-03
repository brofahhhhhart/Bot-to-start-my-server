# ══════════════════════════════════════════════════════════════════════════════
# 🦊 FOX AI v30.0 + TERMINAL (PRO VERSION)
# ══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
import sys
import os
import re
import json
import time
import random
import requests
from datetime import datetime, timezone
from flask import Flask
from threading import Thread

# ══════════════════════════════════════════════════════════════════════════════
# 🔐 CONFIG
# ══════════════════════════════════════════════════════════════════════════════

TOKEN = os.environ.get("DISCORD_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
FIREBASE_DB = os.environ.get("FIREBASE_DB_URL", "")

CARGO_ID = 1465895263582294271

# ══════════════════════════════════════════════════════════════════════════════
# 🎨 CORES
# ══════════════════════════════════════════════════════════════════════════════

C_OK = 0x2ECC71
C_ERRO = 0xE74C3C
C_AI = 0x9B59B6

# ══════════════════════════════════════════════════════════════════════════════
# 🤖 BOT
# ══════════════════════════════════════════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ══════════════════════════════════════════════════════════════════════════════
# 🧠 FIREBASE MEMORY
# ══════════════════════════════════════════════════════════════════════════════

def salvar_memoria(user_id, msg, resposta):
    try:
        url = f"{FIREBASE_DB}/memoria/{user_id}.json"
        data = {
            "msg": msg,
            "resposta": resposta,
            "time": time.time()
        }
        requests.post(url, json=data)
    except:
        pass

def carregar_memoria(user_id):
    try:
        url = f"{FIREBASE_DB}/memoria/{user_id}.json"
        r = requests.get(url)
        return r.json() or {}
    except:
        return {}

# ══════════════════════════════════════════════════════════════════════════════
# 🧠 GROQ CORE
# ══════════════════════════════════════════════════════════════════════════════

def groq_generate(prompt):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        r = requests.post(url, headers=headers, json=data)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erro Groq: {e}"

# ══════════════════════════════════════════════════════════════════════════════
# 🧠 1000 SUBSISTEMAS SIMULADOS
# ══════════════════════════════════════════════════════════════════════════════

def gerar_candidatos(prompt):
    respostas = []
    for i in range(5):  # simulação leve (troque pra 1000 se quiser lag)
        respostas.append(groq_generate(prompt))
    return respostas

# ══════════════════════════════════════════════════════════════════════════════
# ⚖️ JUÍZES
# ══════════════════════════════════════════════════════════════════════════════

def juiz_texto(respostas):
    return max(respostas, key=len)

def juiz_imagem(prompt):
    return f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"

def juiz_video(respostas):
    return random.choice(respostas)

# ══════════════════════════════════════════════════════════════════════════════
# 🗳️ SISTEMA DE VOTAÇÃO REAL
# ══════════════════════════════════════════════════════════════════════════════

def votar(respostas, prompt):
    votos = {}

    for r in respostas:
        score = 0

        if len(r) > 50:
            score += 1
        if "erro" not in r.lower():
            score += 1
        if "não sei" not in r.lower():
            score += 1

        votos[r] = score

    melhor = max(votos, key=votos.get)
    return melhor

# ══════════════════════════════════════════════════════════════════════════════
# 🧠 FOX AI CORE
# ══════════════════════════════════════════════════════════════════════════════

async def fox_ai_responder(msg: discord.Message):
    user_id = str(msg.author.id)
    prompt = msg.content

    memoria = carregar_memoria(user_id)

    contexto = f"""
    Histórico: {json.dumps(memoria)[0:500]}
    Usuário: {prompt}
    """

    candidatos = gerar_candidatos(contexto)

    texto_final = votar(candidatos, prompt)
    imagem = juiz_imagem(prompt)

    salvar_memoria(user_id, prompt, texto_final)

    embed = discord.Embed(
        title="🧠 Fox AI v30.0",
        description=texto_final,
        color=C_AI
    )

    embed.set_image(url=imagem)
    embed.set_footer(text="Sistema de 3 Juízes ativo")

    await msg.channel.send(embed=embed)

# ══════════════════════════════════════════════════════════════════════════════
# 🧪 DETECÇÃO TERMINAL
# ══════════════════════════════════════════════════════════════════════════════

CMDS = {"pip", "apt", "ls", "mkdir", "rm", "git", "python"}

def eh_cmd_terminal(msg):
    return msg.split()[0] in CMDS if msg else False

# ══════════════════════════════════════════════════════════════════════════════
# ⚙️ TERMINAL SIMPLES (RESUMIDO INTEGRADO)
# ══════════════════════════════════════════════════════════════════════════════

async def executar_terminal(msg):
    try:
        proc = subprocess.run(
            msg.content,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15
        )
        out = proc.stdout or proc.stderr

        embed = discord.Embed(
            title="💻 Terminal",
            description=f"```bash\n{out[:2000]}\n```",
            color=C_OK
        )
        await msg.channel.send(embed=embed)

    except Exception as e:
        await msg.channel.send(f"Erro: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 🎯 ROTEAMENTO INTELIGENTE
# ══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return

    if not any(r.id == CARGO_ID for r in msg.author.roles):
        return

    if eh_cmd_terminal(msg.content):
        await executar_terminal(msg)
    else:
        await fox_ai_responder(msg)

    await bot.process_commands(msg)

# ══════════════════════════════════════════════════════════════════════════════
# 🌐 KEEP ALIVE
# ══════════════════════════════════════════════════════════════════════════════

app = Flask("")

@app.route("/")
def home():
    return "Fox AI Online 🦊"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ══════════════════════════════════════════════════════════════════════════════
# 🚀 START
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
