import discord
from discord.ext import commands
import subprocess
import asyncio
import os
import requests
import time
import psutil
import platform
import shutil
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
FIREBASE_URL = os.getenv("FIREBASE_URL")
CARGO_ID = 1465895263582294271
CATEGORIA = "TERMINAL"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= FIREBASE =================
def fb_get():
    try:
        r = requests.get(f"{FIREBASE_URL}/packages.json")
        data = r.json()
        return list(data.values()) if isinstance(data, dict) else data if isinstance(data, list) else []
    except:
        return []

def fb_save(data):
    try:
        requests.put(f"{FIREBASE_URL}/packages.json", json=list(set(data)))
    except:
        pass

def autorizado(member):
    return any(role.id == CARGO_ID for role in member.roles)

# ================= LOADER MELHORADO =================
async def loader(msg, texto="Processando..."):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(22):
        frame = frames[i % len(frames)]
        barra = "█" * (i // 3) + "░" * (10 - i // 3)
        await msg.edit(content=f"```{frame} {texto}\n[{barra}] {min(i*5, 100)}%```")
        await asyncio.sleep(0.18)

# ================= COMANDOS DO TERMINAL =================
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:
        return

    content = msg.content.strip()
    if not content or content.startswith("!"):
        await bot.process_commands(msg)
        return

    comando_lower = content.lower()

    # Só ativa em comandos específicos (conversa normal ignorada)
    triggers = ["pip install ", "mkdir ", "bnd", "status", "help", "ping", "uptime", "sys", "ls", "clear"]
    if not any(comando_lower.startswith(t) for t in triggers):
        return

    if not autorizado(msg.author):
        return await msg.reply("❌ Sem permissão.")

    loading = await msg.reply("```🔄 Iniciando terminal...```")
    await loader(loading)

    # ================= COMANDOS =================
    if comando_lower.startswith("pip install "):
        pkg = content[12:].strip()
        install_msg = await msg.channel.send(f"```📦 Installing {pkg}...```")
        try:
            proc = subprocess.run(f"pip install {pkg}", shell=True, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                lista = fb_get()
                if pkg not in lista:
                    lista.append(pkg)
                    fb_save(lista)
                await install_msg.edit(content=f"```✅ {pkg} instalado com sucesso!```")
            else:
                await install_msg.edit(content=f"```❌ Falha na instalação:\n{proc.stderr[:900]}```")
        except Exception as e:
            await install_msg.edit(content=f"```❌ Erro: {e}```")
        return

    elif comando_lower.startswith("bnd"):
        lista = fb_get()
        pacotes = "\n".join([f"• {p}" for p in lista]) or "Nenhum pacote."
        embed = discord.Embed(title="📦 Banco de Pacotes", description=pacotes, color=0x00ff00)
        try:
            disco = psutil.disk_usage('/')
            embed.add_field(name="💾 Disco", value=f"{disco.free//(1024**3)}GB livre", inline=True)
        except:
            pass
        await loading.edit(content=None, embed=embed)
        return

    elif comando_lower == "status" or comando_lower == "sys":
        embed = discord.Embed(title="🖥️ System Status", color=0x0099ff)
        embed.add_field(name="CPU", value=f"{psutil.cpu_percent()}%", inline=True)
        embed.add_field(name="RAM", value=f"{psutil.virtual_memory().percent}%", inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="SO", value=platform.system(), inline=True)
        await loading.edit(content=None, embed=embed)
        return

    elif comando_lower.startswith("ping"):
        latency = round(bot.latency * 1000, 2)
        await loading.edit(content=f"```🏓 Ping: {latency}ms```")
        return

    elif comando_lower == "help":
        ajuda = """```
Comandos Disponíveis:

pip install <pacote>   → Instala pacote
bnd                    → Banco de pacotes
status / sys           → Status do servidor
ping                   → Latência do bot
uptime                 → Tempo online
help                   → Esta mensagem
        ```"""
        await loading.edit(content=ajuda)
        return

    # Comando genérico
    try:
        proc = subprocess.run(content, shell=True, capture_output=True, text=True, timeout=30)
        output = proc.stdout + proc.stderr or "✔ Executado."
        await loading.edit(content=f"```\n$ {content}\n\n{output[:1900]}\n```")
    except Exception as e:
        await loading.edit(content=f"```❌ {e}```")

# ================= KEEP ALIVE =================
from flask import Flask
from threading import Thread
app = Flask("")
@app.route("/") 
def home(): return "🦊 Terminal Online"
def keep_alive(): Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
