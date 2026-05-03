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
UPTIMEROBOT_API = os.getenv("UPTIMEROBOT_API_KEY")  # Adicione no Render

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
        return "\n".join([f"• {m['friendly_name']}: {'✅ Online' if m.get('status') == 2 else '❌ Offline'}" for m in monitors[:5]])
    except:
        return "Erro ao consultar UptimeRobot"

# ====================== MKDIR ======================
async def criar_mkdir(msg, nome):
    cat = discord.utils.get(msg.guild.categories, name=CATEGORIA) or await msg.guild.create_category(CATEGORIA)
    canal = await msg.guild.create_text_channel(nome, category=cat)
    try:
        os.makedirs(f"./{nome}", exist_ok=True)
        with open(f"./{nome}/info.txt", "w") as f:
            f.write(f"Pasta criada via terminal\nData: {datetime.now()}")
    except:
        pass
    return canal

# ====================== ON_READY ======================
@bot.event
async def on_ready():
    print(f"🦊 Terminal Bot Online: {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Terminal"))

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

    # Filtro para não responder conversa normal
    if not any(comando_lower.startswith(t) for t in ["pip install ", "mkdir ", "bnd", "status", "ping", "uptime", "sys", "help", "plot"]):
        return

    if not autorizado(msg.author):
        return await msg.reply("❌ Sem permissão.")

    loading = await msg.reply("```🔄 Conectando ao Terminal...```")
    await loader(loading)

    # ==================== MKDIR ====================
    if comando_lower.startswith("mkdir "):
        nome = content[6:].strip()
        await loader(loading, f"Criando estrutura {nome}...")
        canal = await criar_mkdir(msg, nome)
        await loading.edit(content=f"```✅ Pasta e canal '{nome}' criados com sucesso!\n{canal.mention}```")
        return

    # ==================== PIP INSTALL (Termux Style) ====================
    if comando_lower.startswith("pip install "):
        pkg = content[12:].strip()
        await loading.edit(content=f"```📦 Baixando {pkg}...```")
        install_msg = await msg.channel.send(f"```🔽 Instalando dependências de {pkg}...```")
        
        proc = subprocess.run(f"pip install {pkg}", shell=True, capture_output=True, text=True, timeout=150)
        
        if proc.returncode == 0:
            lista = fb_get()
            if pkg not in lista:
                lista.append(pkg)
                fb_save(lista)
            await install_msg.edit(content=f"```✅ {pkg} instalado com sucesso!```")
            await loading.edit(content=f"```$ pip install {pkg}\n\n✅ Pacote instalado e salvo no banco.```")
        else:
            await install_msg.edit(content=f"```❌ Falha na instalação de {pkg}\n{proc.stderr[:800]}```")
        return

    # ==================== BND ====================
    if comando_lower.startswith("bnd"):
        cat = discord.utils.get(msg.guild.categories, name=CATEGORIA) or await msg.guild.create_category(CATEGORIA)
        channel = discord.utils.get(msg.guild.text_channels, name="banco-de-pacotes")
        if not channel:
            channel = await msg.guild.create_text_channel("banco-de-pacotes", category=cat)

        lista = fb_get()
        embed = discord.Embed(title="📦 Banco de Pacotes Instalados", color=0x00ff88, timestamp=datetime.utcnow())
        embed.description = "\n".join([f"• {p}" for p in lista]) or "Nenhum pacote instalado."
        embed.add_field(name="Total", value=f"{len(lista)} pacotes", inline=True)
        
        try:
            disco = psutil.disk_usage('/')
            embed.add_field(name="💾 Render", value=f"{disco.free//(1024**3)}GB livre", inline=True)
        except:
            pass
        embed.add_field(name="🔥 Firebase", value=f"{get_firebase_size()} KB", inline=True)
        embed.add_field(name="📡 UptimeRobot", value=await get_uptime_info(), inline=False)
        embed.add_field(name="🏓 Ping do Bot", value=f"{round(bot.latency*1000, 2)}ms", inline=True)

        await channel.send(embed=embed)
        await loading.edit(content=f"```✅ Banco aberto em {channel.mention}```")
        return

    # ==================== OUTROS COMANDOS ====================
    if comando_lower in ["status", "sys"]:
        embed = discord.Embed(title="🖥️ Status Completo do Servidor", color=0x0099ff)
        embed.add_field(name="CPU", value=f"{psutil.cpu_percent()}%", inline=True)
        embed.add_field(name="RAM", value=f"{psutil.virtual_memory().percent}%", inline=True)
        embed.add_field(name="Ping", value=f"{round(bot.latency*1000, 2)}ms", inline=True)
        embed.add_field(name="Uptime", value=str(timedelta(seconds=int((datetime.utcnow() - start_time).total_seconds()))), inline=True)
        await loading.edit(content=None, embed=embed)
        return

    if comando_lower.startswith("ping") or comando_lower.startswith("uptime"):
        await loading.edit(content=f"```🏓 Ping: {round(bot.latency*1000, 2)}ms\n⏱️ Online há: {str(timedelta(seconds=int((datetime.utcnow() - start_time).total_seconds())))}```")
        return

    if comando_lower == "help":
        await loading.edit(content="```Comandos: mkdir, pip install, bnd, status, ping, uptime, help```")
        return

    # Comando genérico
    try:
        proc = subprocess.run(content, shell=True, capture_output=True, text=True, timeout=30)
        await loading.edit(content=f"```\n$ {content}\n\n{proc.stdout + proc.stderr[:1850] or '✔ OK'}\n```")
    except Exception as e:
        await loading.edit(content=f"```❌ {e}```")

# ====================== KEEP ALIVE ======================
from flask import Flask
from threading import Thread
app = Flask("")
@app.route("/") 
def home(): 
    return "Terminal Bot Online - Ligue no Render se estiver off"
def keep_alive(): 
    Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
