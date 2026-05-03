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

TOKEN = os.getenv("DISCORD_TOKEN")
FIREBASE_URL = os.getenv("FIREBASE_URL")
UPTIMEROBOT_API = os.getenv("UPTIMEROBOT_API_KEY")  # ← Adicione no Render

CARGO_ID = 1465895263582294271
CATEGORIA = "TERMINAL"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
start_time = datetime.utcnow()

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

def get_firebase_size():
    try:
        r = requests.get(FIREBASE_URL + ".json?shallow=true")
        return len(str(r.content)) // 1024  # KB aproximado
    except:
        return "N/A"

# ================= PERMISSÃO =================
def autorizado(member):
    return any(role.id == CARGO_ID for role in member.roles)

# ================= LOADER =================
async def loader(msg, texto="Processando..."):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(20):
        frame = frames[i % len(frames)]
        barra = "█" * (i // 2) + "░" * (12 - i // 2)
        await msg.edit(content=f"```{frame} {texto}\n[{barra}] {min(i*5, 100)}%```")
        await asyncio.sleep(0.2)

# ================= UPTIMEROBOT =================
async def get_uptime_status():
    if not UPTIMEROBOT_API:
        return "API não configurada"
    try:
        data = requests.post("https://api.uptimerobot.com/v2/getMonitors", 
                           data={"api_key": UPTIMEROBOT_API, "format": "json"}).json()
        monitors = data.get("monitors", [])
        return "\n".join([f"• {m['friendly_name']}: {'✅ Online' if m['status'] == 2 else '❌ Offline'}" for m in monitors])
    except:
        return "Erro ao consultar UptimeRobot"

# ================= ON_READY =================
@bot.event
async def on_ready():
    print(f"🦊 Bot iniciado: {bot.user}")
    await bot.change_presence(activity=discord.Game("Terminal em execução"))

# ================= ON_MESSAGE =================
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:
        return

    content = msg.content.strip()
    if not content or content.startswith("!"):
        await bot.process_commands(msg)
        return

    comando_lower = content.lower()

    if not any(comando_lower.startswith(t) for t in ["pip install ", "bnd", "status", "ping", "uptime", "sys", "help"]):
        return

    if not autorizado(msg.author):
        return await msg.reply("❌ Sem permissão.")

    loading = await msg.reply("```🔄 Conectando ao terminal...```")
    await loader(loading)

    # ================= BND - BANCO DE PACOTES =================
    if comando_lower.startswith("bnd"):
        cat = discord.utils.get(msg.guild.categories, name=CATEGORIA)
        if not cat:
            cat = await msg.guild.create_category(CATEGORIA)

        channel = discord.utils.get(msg.guild.text_channels, name="banco-de-pacotes")
        if not channel:
            channel = await msg.guild.create_text_channel("banco-de-pacotes", category=cat)

        lista = fb_get()
        pacotes = "\n".join([f"• {p}" for p in lista]) or "Nenhum pacote instalado."

        embed = discord.Embed(title="📦 Banco de Pacotes Instalados", description=pacotes, color=0x00ff88, timestamp=datetime.utcnow())
        embed.add_field(name="Total de Pacotes", value=len(lista), inline=True)
        
        # Render
        try:
            disco = psutil.disk_usage('/')
            embed.add_field(name="💾 Render", value=f"{disco.free//(1024**3)}GB livre", inline=True)
        except:
            pass

        # Firebase
        embed.add_field(name="🔥 Firebase", value=f"{get_firebase_size()} KB usados", inline=True)

        # UptimeRobot
        uptime_info = await get_uptime_status()
        embed.add_field(name="📡 UptimeRobot", value=uptime_info, inline=False)

        await channel.send(embed=embed)
        await loading.edit(content=f"```✅ Banco de pacotes aberto em {channel.mention}```")
        return

    # ================= OUTROS COMANDOS =================
    if comando_lower.startswith("pip install "):
        # (mesmo código anterior de pip install)
        pkg = content[12:].strip()
        install_msg = await msg.channel.send(f"```📦 Installing {pkg}...```")
        proc = subprocess.run(f"pip install {pkg}", shell=True, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            lista = fb_get()
            if pkg not in lista:
                lista.append(pkg)
                fb_save(lista)
            await install_msg.edit(content=f"```✅ {pkg} instalado com sucesso!```")
        else:
            await install_msg.edit(content=f"```❌ Erro:\n{proc.stderr[:800]}```")
        return

    if comando_lower in ["status", "sys"]:
        embed = discord.Embed(title="🖥️ Status do Servidor", color=0x0099ff)
        embed.add_field(name="CPU", value=f"{psutil.cpu_percent()}%", inline=True)
        embed.add_field(name="RAM", value=f"{psutil.virtual_memory().percent}%", inline=True)
        embed.add_field(name="Ping", value=f"{round(bot.latency*1000, 2)}ms", inline=True)
        await loading.edit(content=None, embed=embed)
        return

    if comando_lower.startswith("ping") or comando_lower.startswith("uptime"):
        uptime = str(timedelta(seconds=int((datetime.utcnow() - start_time).total_seconds())))
        await loading.edit(content=f"```🏓 Ping: {round(bot.latency*1000, 2)}ms\n⏱️ Uptime: {uptime}```")
        return

    # Comando genérico
    try:
        proc = subprocess.run(content, shell=True, capture_output=True, text=True, timeout=25)
        await loading.edit(content=f"```\n$ {content}\n\n{proc.stdout + proc.stderr[:1800] or '✔ OK'}\n```")
    except Exception as e:
        await loading.edit(content=f"```❌ {e}```")

# ================= KEEP ALIVE =================
from flask import Flask
from threading import Thread
app = Flask("")
@app.route("/") 
def home(): return "Terminal Online"
def keep_alive(): Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

if __name__ == "__main__":
    if not TOKEN or not FIREBASE_URL:
        print("Configure as variáveis de ambiente!")
        exit()
    keep_alive()
    bot.run(TOKEN)
