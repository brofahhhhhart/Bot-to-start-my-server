# ==============================
# 🦊 FOX TERMINAL v30 (SEM IA)
# ==============================

import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
import sys
import os
import time
import re
from datetime import datetime, timezone

# ─── CONFIG ─────────────────────────────────────

TOKEN = os.environ.get("DISCORD_TOKEN", "")
CARGO_ID = 1465895263582294271
CATEGORIA = "TERMINAL"

# ─── CORES ─────────────────────────────────────

C_OK = 0x2ECC71
C_ERRO = 0xE74C3C
C_INFO = 0x3498DB
C_LOADING = 0xF39C12
C_TERM = 0x1ABC9C
C_LOCK = 0xC0392B

# ─── BOT ─────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

boot_time = time.time()

# ─── HELPERS ─────────────────────────────────────

def agora():
    return datetime.now().strftime("%H:%M:%S")

def uptime():
    s = int(time.time() - boot_time)
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def tem_cargo(member):
    return any(r.id == CARGO_ID for r in member.roles)

def cortar(texto, n=2000):
    return texto[:n] if texto else "OK"

# ─── EXECUÇÃO ─────────────────────────────────────

def rodar(cmd, timeout=60):
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return r.stdout, r.stderr, r.returncode
    except Exception as e:
        return "", str(e), 1

async def rodar_async(cmd):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: rodar(cmd))

# ─── LOADER ─────────────────────────────────────

class Loader:
    def __init__(self, canal, titulo, cmd):
        self.canal = canal
        self.titulo = titulo
        self.cmd = cmd
        self.msg = None

    async def start(self):
        self.msg = await self.canal.send(f"⏳ {self.titulo}\n```{self.cmd}```")
        return self

    async def ok(self, texto):
        await self.msg.edit(content=f"✅ {self.titulo}\n```{cortar(texto)}```")

    async def erro(self, texto):
        await self.msg.edit(content=f"❌ {self.titulo}\n```{cortar(texto)}```")

# ─── DETECÇÃO DE COMANDO ─────────────────────────

CMDS = {
    "pip","pip3","npm","npx","node",
    "apt","apt-get","pkg",
    "git","mkdir","ls","rm",
    "python","python3","wget","curl"
}

def eh_terminal(msg):
    if not msg.strip():
        return False
    return msg.split()[0].lower() in CMDS

# ─── CATEGORIA ─────────────────────────────────────

async def get_categoria(guild):
    cat = discord.utils.get(guild.categories, name=CATEGORIA)
    if not cat:
        cat = await guild.create_category(CATEGORIA)
    return cat

# ─── MKDIR ─────────────────────────────────────

async def cmd_mkdir(msg, nome):
    nome = nome.lower().replace(" ", "-")

    cat = await get_categoria(msg.guild)

    canal = await msg.guild.create_text_channel(nome, category=cat)

    await msg.channel.send(f"📁 Canal criado: {canal.mention}")

# ─── LS ─────────────────────────────────────

async def cmd_ls(msg):
    cat = discord.utils.get(msg.guild.categories, name=CATEGORIA)
    if not cat:
        await msg.channel.send("Vazio")
        return

    canais = "\n".join(c.name for c in cat.channels)
    await msg.channel.send(f"```\n{canais}\n```")

# ─── RM ─────────────────────────────────────

async def cmd_rm(msg, nome):
    cat = discord.utils.get(msg.guild.categories, name=CATEGORIA)
    canal = discord.utils.get(cat.channels, name=nome)

    if canal:
        await canal.delete()
        await msg.channel.send("🗑️ Canal removido")

# ─── UPDATE AUTOMÁTICO ─────────────────────────

async def atualizar_sistema():
    comandos = [
        "python -m pip install --upgrade pip",
        "npm install -g npm",
    ]

    for c in comandos:
        subprocess.run(c, shell=True)

# ─── ON MESSAGE ─────────────────────────────────

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    content = msg.content.strip()

    # NÃO É COMANDO → IGNORA
    if not eh_terminal(content):
        return

    # PERMISSÃO
    if not tem_cargo(msg.author):
        await msg.channel.send("🔒 Sem permissão")
        return

    parts = content.split()
    cmd = parts[0]
    args = parts[1:]

    # ─── COMANDOS ESPECIAIS ───

    if cmd == "mkdir" and args:
        await cmd_mkdir(msg, " ".join(args))
        return

    if cmd == "ls":
        await cmd_ls(msg)
        return

    if cmd == "rm" and args:
        await cmd_rm(msg, args[0])
        return

    # ─── EXECUÇÃO NORMAL ───

    loader = await Loader(msg.channel, f"Executando {cmd}", content).start()

    out, err, code = await rodar_async(content)

    if code == 0:
        await loader.ok(out or "OK")
    else:
        await loader.erro(err or out)

# ─── STATUS ─────────────────────────────────────

@tasks.loop(seconds=30)
async def status():
    await bot.change_presence(activity=discord.Game("Fox Terminal 🦊"))

@bot.event
async def on_ready():
    print("🦊 Fox Terminal ONLINE")
    status.start()

# ─── KEEP ALIVE ─────────────────────────────────

from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "Fox Terminal Online"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ─── START ─────────────────────────────────────

if __name__ == "__main__":
    if not TOKEN:
        print("Token não definido")
        exit()

    keep_alive()
    asyncio.run(atualizar_sistema())
    bot.run(TOKEN)
