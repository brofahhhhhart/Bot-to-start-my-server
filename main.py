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
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io

# ====================== CONFIG ======================
TOKEN = os.getenv("DISCORD_TOKEN")
FIREBASE_URL = os.getenv("FIREBASE_URL")
UPTIMEROBOT_API = os.getenv("UPTIMEROBOT_API_KEY")

CARGO_ID = 1465895263582294271
CATEGORIA = "TERMINAL"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
start_time = datetime.utcnow()

# ====================== PERMISSÃO ======================
def autorizado(member):
    return any(role.id == CARGO_ID for role in member.roles)

# ====================== LOADER ======================
async def loader(msg, texto="Processando..."):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(25):
        frame = frames[i % len(frames)]
        barra = "█" * (i // 2) + "░" * (12 - i // 2)
        await msg.edit(content=f"```{frame} {texto}\n[{barra}] {min(i*4, 100)}%```")
        await asyncio.sleep(0.2)

# ====================== FIREBASE ======================
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

def get_firebase_size():
    try:
        r = requests.get(FIREBASE_URL + ".json?shallow=true")
        return len(str(r.content)) // 1024
    except:
        return "N/A"

# ====================== UPTIMEROBOT ======================
async def get_uptime_info():
    if not UPTIMEROBOT_API:
        return "API não configurada"
    try:
        payload = {"api_key": UPTIMEROBOT_API, "format": "json"}
        data = requests.post("https://api.uptimerobot.com/v2/getMonitors", data=payload).json()
        monitors = data.get("monitors", [])
        return "\n".join([f"• {m['friendly_name']}: {'✅ Online' if m.get('status') == 2 else '❌ Offline'}" for m in monitors])
    except:
        return "Erro ao consultar"

# ====================== MKDIR ======================
async def criar_mkdir(msg, nome):
    cat = discord.utils.get(msg.guild.categories, name=CATEGORIA) or await msg.guild.create_category(CATEGORIA)
    canal = await msg.guild.create_text_channel(nome, category=cat)
    try:
        os.makedirs(f"./{nome}", exist_ok=True)
        with open(f"./{nome}/info.txt", "w") as f:
            f.write(f"Pasta criada via terminal\nData: {datetime.now()}")
    except Exception as e:
        print(e)
    return canal

# ====================== ON_READY ======================
@bot.event
async def on_ready():
    print(f"🦊 Bot Online: {bot.user}")
    await bot.change_presence(activity=discord.Game("Terminal Avançado"))

# ====================== ON_MESSAGE ======================
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:
        return

    content = msg.content.strip()
    if not content or content.startswith("!"):
        await bot.process_commands(msg)
        return

    comando_lower = content.lower()

    if not any(comando_lower.startswith(t) for t in ["pip install ", "mkdir ", "bnd", "status", "ping", "uptime", "sys", "help", "plot"]):
        return

    if not autorizado(msg.author):
        return await msg.reply("❌ Sem permissão.")

    loading = await msg.reply("```🔄 Inicializando Terminal...```")
    await loader(loading)

    # MKDIR
    if comando_lower.startswith("mkdir "):
        nome = content[6:].strip()
        await loader(loading, f"Criando {nome}...")
        canal = await criar_mkdir(msg, nome)
        await loading.edit(content=f"```✅ Estrutura '{nome}' criada!\n📁 {canal.mention}```")
        return

    # PIP INSTALL (Estilo Termux)
    if comando_lower.startswith("pip install "):
        pkg = content[12:].strip()
        await loading.edit(content=f"```📦 Baixando {pkg}...```")
        install_msg = await msg.channel.send(f"```🔽 Instalando {pkg}...```")
        
        proc = subprocess.run(f"pip install {pkg}", shell=True, capture_output=True, text=True, timeout=150)
        
        if proc.returncode == 0:
            lista = fb_get()
            if pkg not in lista:
                lista.append(pkg)
                fb_save(lista)
            await install_msg.edit(content=f"```✅ {pkg} instalado com sucesso!```")
            await loading.edit(content=f"```$ pip install {pkg}\n\n✅ Sucesso! Pacote salvo no banco.```")
        else:
            await install_msg.edit(content=f"```❌ Falha na instalação:\n{proc.stderr[:900]}```")
        return

    # BND
    if comando_lower.startswith("bnd"):
        cat = discord.utils.get(msg.guild.categories, name=CATEGORIA) or await msg.guild.create_category(CATEGORIA)
        channel = discord.utils.get(msg.guild.text_channels, name="banco-de-pacotes") or await msg.guild.create_text_channel("banco-de-pacotes", category=cat)

        lista = fb_get()
        embed = discord.Embed(title="📦 Banco de Pacotes Instalados", color=0x00ff88)
        embed.description = "\n".join([f"• {p}" for p in lista]) or "Nenhum pacote."
        embed.add_field(name="Total", value=len(lista), inline=True)
        embed.add_field(name="💾 Render", value=f"{psutil.disk_usage('/').free//(1024**3)}GB livre", inline=True)
        embed.add_field(name="🔥 Firebase", value=f"{get_firebase_size()} KB", inline=True)
        embed.add_field(name="📡 UptimeRobot", value=await get_uptime_info(), inline=False)
        embed.add_field(name="🏓 Ping", value=f"{round(bot.latency*1000, 2)}ms", inline=True)

        await channel.send(embed=embed)
        await loading.edit(content=f"```✅ Banco de pacotes aberto em {channel.mention}```")
        return

    # Outros comandos
    try:
        proc = subprocess.run(content, shell=True, capture_output=True, text=True, timeout=30)
        await loading.edit(content=f"```\n$ {content}\n\n{proc.stdout + proc.stderr[:1800] or '✔ OK'}\n```")
    except Exception as e:
        await loading.edit(content=f"```❌ {e}```")

# ====================== KEEP ALIVE ======================
from flask import Flask
from threading import Thread
app = Flask("")
@app.route("/") 
def home(): return "Bot Terminal - Ligue no Render se estiver off"
def keep_alive(): Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
