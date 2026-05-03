import discord
from discord.ext import commands
import subprocess
import asyncio
import os
import requests
import time

# ================= CONFIG =================
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
        return r.json() if r.json() else []
    except:
        return []

def fb_save(data):
    try:
        requests.put(f"{FIREBASE_URL}/packages.json", json=data)
    except:
        pass

# ================= PERMISSÃO =================
def autorizado(member):
    return any(role.id == CARGO_ID for role in member.roles)

# ================= REINSTALL =================
async def reinstall():
    pkgs = fb_get()
    if not pkgs:
        return

    print("📦 Reinstalando pacotes...")
    for p in pkgs:
        os.system(f"pip install {p}")

# ================= LOADER =================
async def loader(msg):
    for i in range(0, 101, 10):
        barra = "█" * (i // 10) + "░" * (10 - i // 10)
        await msg.edit(content=f"```[{barra}] {i}%```")
        await asyncio.sleep(0.3)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"🦊 Bot ON: {bot.user}")
    await reinstall()

# ================= TERMINAL =================
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:
        return

    content = msg.content.strip()

    # Ignorar comandos normais
    if content.startswith("!"):
        await bot.process_commands(msg)
        return

    # 🔒 Permissão
    if not autorizado(msg.author):
        return await msg.reply("❌ Sem permissão")

    # 🎬 Loader estilo terminal
    loading = await msg.reply("```Iniciando terminal...```")
    await loader(loading)

    # ================= MKDIR =================
    if content.startswith("mkdir "):
        nome = content.replace("mkdir ", "").strip()

        cat = discord.utils.get(msg.guild.categories, name=CATEGORIA)
        if not cat:
            cat = await msg.guild.create_category(CATEGORIA)

        canal = await msg.guild.create_text_channel(nome, category=cat)
        return await loading.edit(content=f"📁 Canal criado: {canal.mention}")

    # ================= PIP =================
    if content.startswith("pip install "):
        pkg = content.replace("pip install ", "").strip()

        lista = fb_get()
        if pkg not in lista:
            lista.append(pkg)
            fb_save(lista)

    # ================= EXEC =================
    try:
        start = time.time()
        proc = subprocess.run(content, shell=True, capture_output=True, text=True, timeout=20)
        output = proc.stdout + proc.stderr
        tempo = round(time.time() - start, 2)

    except Exception as e:
        output = str(e)
        tempo = 0

    if not output.strip():
        output = "✔ Executado"

    await loading.edit(content=f"""```
$ {content}

{output[:1800]}

⏱ {tempo}s
```""")

    await bot.process_commands(msg)

# ================= KEEP ALIVE =================
from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "🦊 Bot Online"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ================= START =================
if __name__ == "__main__":
    if not TOKEN or not FIREBASE_URL:
        print("❌ Configure DISCORD_TOKEN e FIREBASE_URL")
        exit()

    keep_alive()
    bot.run(TOKEN)
