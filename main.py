# ================================
# 🦊 FOX TERMINAL PRO - VPS EDITION
# ================================

import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
import os
import time
import shlex
from datetime import datetime
from flask import Flask
from threading import Thread

# ─── CONFIG ─────────────────────────────────────────────

TOKEN = os.getenv("DISCORD_TOKEN")

CARGO_ID = 1465895263582294271
CATEGORIA = "TERMINAL"

CMD_TIMEOUT = 60

# ─── BOT ───────────────────────────────────────────────

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

boot_time = time.time()

# ─── SEGURANÇA ─────────────────────────────────────────

COMANDOS_BLOQUEADOS = [
    "rm -rf /", "mkfs", "shutdown", "reboot",
    "dd if=", ">:","kill -9 1"
]

def seguro(cmd):
    for perigo in COMANDOS_BLOQUEADOS:
        if perigo in cmd:
            return False
    return True

# ─── HELPERS ───────────────────────────────────────────

def tem_cargo(member):
    return any(r.id == CARGO_ID for r in member.roles)

def uptime():
    s = int(time.time() - boot_time)
    return f"{s//3600}h {(s%3600)//60}m {s%60}s"

def cortar(txt, n=1800):
    return txt[:n] if txt else ""

def rodar(cmd):
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=CMD_TIMEOUT
        )
        return proc.stdout or proc.stderr
    except Exception as e:
        return str(e)

# ─── LOADER ANIMADO ────────────────────────────────────

SPIN = ["⠁","⠂","⠄","⠂","⠁"]

async def animar(msg, texto):
    for i in range(10):
        await msg.edit(content=f"{SPIN[i%len(SPIN)]} {texto}")
        await asyncio.sleep(0.4)

# ─── CATEGORIA ─────────────────────────────────────────

async def get_categoria(guild):
    cat = discord.utils.get(guild.categories, name=CATEGORIA)
    if not cat:
        cat = await guild.create_category(CATEGORIA)
    return cat

# ─── COMANDOS SUPORTADOS (70+) ─────────────────────────

CMDS = [
"pip","pip3","python","python3",
"npm","npx","node","yarn","pnpm","bun",
"apt","apt-get","apt-cache","dpkg",
"pkg",
"git",
"docker","docker-compose",
"ls","ll","la","pwd","cd",
"rm","cat","echo","touch","mv","cp",
"chmod","chown","ln",
"head","tail","grep","wc","find",
"which","sort","awk","sed",
"clear","history","env","export",
"ps","kill","df","du","free","uptime","date",
"curl","wget","ping","netstat","ss","ifconfig","ip",
"nmap","traceroute","dig",
"whoami","uname","id","groups",
"lscpu","lsblk",
"nano","vim","vi",
"top","htop"
]

def eh_cmd(msg):
    if not msg:
        return False
    return msg.split()[0] in CMDS

# ─── EVENTO PRINCIPAL ──────────────────────────────────

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    if not tem_cargo(msg.author):
        return

    content = msg.content.strip()

    # ─── MKDIR → CANAL ────────────────────────────────
    if content.startswith("mkdir"):
        nome = content.replace("mkdir", "").strip().lower()

        if not nome:
            await msg.reply("❌ Nome inválido")
            return

        cat = await get_categoria(msg.guild)

        if discord.utils.get(cat.channels, name=nome):
            await msg.reply("❌ Canal já existe")
            return

        canal = await msg.guild.create_text_channel(nome, category=cat)

        await msg.reply(f"✅ Canal criado: {canal.mention}")
        return

    # ─── CLEAR CHAT ───────────────────────────────────
    if content in ["clear","cls"]:
        await msg.channel.purge(limit=50)
        return

    # ─── EXECUÇÃO TERMINAL ────────────────────────────
    if eh_cmd(content):

        if not seguro(content):
            await msg.reply("🚫 Comando bloqueado por segurança")
            return

        m = await msg.reply("⏳ Executando...")
        await animar(m, content)

        output = rodar(content)

        await m.edit(content=f"```bash\n{cortar(output)}\n```")
        return

    await bot.process_commands(msg)

# ─── STATUS ───────────────────────────────────────────

@tasks.loop(seconds=30)
async def status():
    await bot.change_presence(activity=discord.Game("Fox Terminal VPS 🦊"))

# ─── READY ────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"🦊 Online como {bot.user}")
    status.start()

# ─── KEEP ALIVE ───────────────────────────────────────

app = Flask("")

@app.route("/")
def home():
    return f"Fox Terminal Online | uptime {uptime()}"

def run_web():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run_web).start()

# ─── START ────────────────────────────────────────────

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Defina DISCORD_TOKEN")
        exit()

    keep_alive()
    bot.run(TOKEN)
