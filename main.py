# ==========================================
# 🦊 FOX TERMINAL v30 - FULL (SEM IA)
# ==========================================

import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
import sys
import os
import time
import re
from datetime import datetime, timezone

# ───────────────── CONFIG ─────────────────

TOKEN = os.environ.get("DISCORD_TOKEN", "")
CARGO_ID = 1465895263582294271
CATEGORIA = "TERMINAL"

CMD_TIMEOUT = 60
INSTALL_TIMEOUT = 180

# ───────────────── CORES ─────────────────

C_OK = 0x2ECC71
C_ERRO = 0xE74C3C
C_INFO = 0x3498DB
C_LOADING = 0xF39C12
C_TERM = 0x1ABC9C
C_LOCK = 0xC0392B

boot_time = time.time()

# ───────────────── BOT ─────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ───────────────── HELPERS ─────────────────

def agora():
    return datetime.now().strftime("%H:%M:%S")

def uptime():
    s = int(time.time() - boot_time)
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def tem_cargo(member):
    return any(r.id == CARGO_ID for r in member.roles)

def cortar(txt, n=2000):
    return txt[:n] if txt else "OK"

# ───────────────── SEGURANÇA ─────────────────

COMANDOS_BLOQUEADOS = [
    "rm -rf /",
    "shutdown",
    "reboot",
    "mkfs",
    ":(){:|:&};:",
]

def comando_perigoso(cmd):
    return any(b in cmd.lower() for b in COMANDOS_BLOQUEADOS)

# ───────────────── EXECUÇÃO ─────────────────

def rodar(cmd, timeout=CMD_TIMEOUT):
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "Tempo excedido", 1
    except Exception as e:
        return "", str(e), 1

async def rodar_async(cmd, timeout=CMD_TIMEOUT):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: rodar(cmd, timeout))

# ───────────────── LOADER ─────────────────

class Loader:
    def __init__(self, canal, titulo, cmd):
        self.canal = canal
        self.titulo = titulo
        self.cmd = cmd
        self.msg = None
        self.start_time = time.time()

    async def start(self):
        embed = discord.Embed(
            title=f"⏳ {self.titulo}",
            description=f"```bash\n{self.cmd}\n```",
            color=C_LOADING
        )
        self.msg = await self.canal.send(embed=embed)
        return self

    async def ok(self, output):
        tempo = f"{time.time() - self.start_time:.2f}s"
        embed = discord.Embed(
            title=f"✅ {self.titulo}",
            description=f"```bash\n{cortar(output)}\n```",
            color=C_OK
        )
        embed.add_field(name="Tempo", value=tempo)
        await self.msg.edit(embed=embed)

    async def erro(self, output):
        tempo = f"{time.time() - self.start_time:.2f}s"
        embed = discord.Embed(
            title=f"❌ {self.titulo}",
            description=f"```bash\n{cortar(output)}\n```",
            color=C_ERRO
        )
        embed.add_field(name="Tempo", value=tempo)
        await self.msg.edit(embed=embed)

# ───────────────── CATEGORIA ─────────────────

async def get_categoria(guild):
    cat = discord.utils.get(guild.categories, name=CATEGORIA)
    if not cat:
        cat = await guild.create_category(CATEGORIA)
    return cat

# ───────────────── COMANDOS DISCORD ─────────────────

async def cmd_mkdir(msg, nome):
    nome = re.sub(r"[^a-z0-9\-]", "-", nome.lower())

    cat = await get_categoria(msg.guild)

    if discord.utils.get(cat.channels, name=nome):
        await msg.channel.send("❌ Canal já existe")
        return

    canal = await msg.guild.create_text_channel(nome, category=cat)

    await msg.channel.send(f"📁 Criado: {canal.mention}")

async def cmd_ls(msg):
    cat = discord.utils.get(msg.guild.categories, name=CATEGORIA)

    if not cat:
        await msg.channel.send("Sem canais")
        return

    lista = "\n".join([c.name for c in cat.channels]) or "Vazio"
    await msg.channel.send(f"```\n{lista}\n```")

async def cmd_rm(msg, nome):
    cat = discord.utils.get(msg.guild.categories, name=CATEGORIA)
    canal = discord.utils.get(cat.channels, name=nome) if cat else None

    if not canal:
        await msg.channel.send("❌ Não encontrado")
        return

    await canal.delete()
    await msg.channel.send("🗑️ Canal removido")

# ───────────────── ATUALIZAÇÃO ─────────────────

async def atualizar_instaladores():
    comandos = [
        "python -m pip install --upgrade pip",
        "pip install --upgrade setuptools",
        "npm install -g npm",
    ]

    for cmd in comandos:
        try:
            subprocess.run(cmd, shell=True)
        except:
            pass

# ───────────────── DETECÇÃO ─────────────────

def eh_comando(msg):
    if not msg.strip():
        return False
    return True  # aceita tudo (terminal livre)

# ───────────────── ON MESSAGE ─────────────────

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:
        return

    content = msg.content.strip()

    if not eh_comando(content):
        return

    if not tem_cargo(msg.author):
        await msg.channel.send("🔒 Sem permissão")
        return

    if comando_perigoso(content):
        await msg.channel.send("🚫 Comando bloqueado")
        return

    partes = content.split()
    cmd = partes[0]
    args = partes[1:]

    # ─── mkdir ───
    if cmd == "mkdir" and args:
        await cmd_mkdir(msg, " ".join(args))
        return

    # ─── ls ───
    if cmd == "ls":
        await cmd_ls(msg)
        return

    # ─── rm ───
    if cmd == "rm" and args:
        await cmd_rm(msg, args[0])
        return

    # ─── EXECUÇÃO REAL ───
    loader = await Loader(msg.channel, f"Executando {cmd}", content).start()

    out, err, code = await rodar_async(content)

    if code == 0:
        await loader.ok(out or "OK")
    else:
        await loader.erro(err or out)

# ───────────────── STATUS ─────────────────

@tasks.loop(seconds=30)
async def status_loop():
    await bot.change_presence(activity=discord.Game("Fox Terminal 🦊"))

@bot.event
async def on_ready():
    print("🦊 Fox Terminal ONLINE")
    status_loop.start()

# ───────────────── KEEP ALIVE ─────────────────

from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return f"Fox Terminal OK | uptime {uptime()}"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ───────────────── START ─────────────────

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Token não definido")
        exit()

    keep_alive()
    asyncio.run(atualizar_instaladores())

    print("🚀 Iniciando Fox Terminal...")
    bot.run(TOKEN)
