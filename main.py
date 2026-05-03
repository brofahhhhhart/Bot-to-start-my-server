# ================================
# 🦊 FOX TERMINAL ULTRA v2
# ================================

import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
import os
import time
import random
from datetime import datetime
from flask import Flask
from threading import Thread

TOKEN = os.getenv("DISCORD_TOKEN")

CARGO_ID = 1465895263582294271
CATEGORIA = "TERMINAL"

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ─────────────────────────────────────────────
# 🧠 100+ COMANDOS SUPORTADOS
# ─────────────────────────────────────────────

CMDS = set("""
pip pip3 python python3
npm npx node yarn pnpm bun
apt apt-get apt-cache dpkg snap flatpak
pkg
git
docker docker-compose
ls ll la pwd cd
rm cat echo touch mv cp
chmod chown ln
head tail grep wc find
which whereis sort awk sed cut tr
clear history env export unset
ps kill killall top htop
df du free uptime date cal
curl wget ping netstat ss ifconfig ip
nmap traceroute dig nslookup host
whoami uname id groups hostname
lscpu lsblk lsusb
nano vim vi micro
zip unzip tar gzip gunzip
make gcc g++ cmake
java javac mvn gradle
composer php
go cargo rustc
perl ruby
sqlite mysql psql
screen tmux
alias unalias
watch time yes
uptime reboot shutdown
""".split())

# ─────────────────────────────────────────────
# 🔐 SEGURANÇA
# ─────────────────────────────────────────────

BLOCK = ["rm -rf /", "shutdown", "reboot", "mkfs", "dd if="]

def seguro(cmd):
    return not any(x in cmd for x in BLOCK)

def tem_cargo(member):
    return any(r.id == CARGO_ID for r in member.roles)

def eh_cmd(msg):
    if not msg:
        return False
    return msg.split()[0].lower() in CMDS

# ─────────────────────────────────────────────
# 🎬 LOADER ANIMADO (BARRA + %)
# ─────────────────────────────────────────────

async def loader_terminal(msg, texto):
    barras = ["░░░░░░░░░░","█░░░░░░░░░","██░░░░░░░░","███░░░░░░░","████░░░░░░",
              "█████░░░░░","██████░░░░","███████░░░","████████░░","█████████░","██████████"]

    for i in range(11):
        pct = i * 10
        frame = f"""
```bash
$ {texto}
[{barras[i]}] {pct}%
Processando...

"""
await msg.edit(content=frame)
await asyncio.sleep(0.4)

─────────────────────────────────────────────

🤖 RESPOSTA TERMINAL FAKE (EX: OI)

─────────────────────────────────────────────

async def resposta_fake(msg, texto):
m = await msg.reply("⏳ Inicializando terminal...")
await loader_terminal(m, texto)

respostas = [
    "comando não encontrado",
    "executando rotina...",
    "entrada recebida",
    "processo concluído"
]

await m.edit(content=f"""

$ {texto}
{random.choice(respostas)}
✔ concluído

""")

─────────────────────────────────────────────

⚙ EXECUÇÃO REAL

─────────────────────────────────────────────

def rodar(cmd):
try:
r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
return r.stdout or r.stderr or "OK"
except Exception as e:
return str(e)

─────────────────────────────────────────────

📁 CATEGORIA

─────────────────────────────────────────────

async def get_categoria(guild):
cat = discord.utils.get(guild.categories, name=CATEGORIA)
if not cat:
cat = await guild.create_category(CATEGORIA)
return cat

─────────────────────────────────────────────

🎯 EVENTO PRINCIPAL

─────────────────────────────────────────────

@bot.event
async def on_message(msg):
if msg.author.bot:
return

if not tem_cargo(msg.author):
    return

content = msg.content.strip()

# ─── MKDIR ─────────────────
if content.startswith("mkdir"):
    nome = content.replace("mkdir", "").strip().lower()
    cat = await get_categoria(msg.guild)
    canal = await msg.guild.create_text_channel(nome, category=cat)
    await msg.reply(f"📁 Canal criado: {canal.mention}")
    return

# ─── NÃO É COMANDO → TERMINAL FAKE ───
if not eh_cmd(content):
    await resposta_fake(msg, content)
    return

# ─── SEGURANÇA ───
if not seguro(content):
    await msg.reply("🚫 Comando bloqueado")
    return

# ─── EXECUÇÃO REAL ───
m = await msg.reply("⏳ Executando...")
await loader_terminal(m, content)

out = rodar(content)

await m.edit(content=f"""

$ {content}
{out[:1800]}

""")

─────────────────────────────────────────────

🔄 STATUS

─────────────────────────────────────────────

@tasks.loop(seconds=30)
async def status():
await bot.change_presence(activity=discord.Game("Terminal Ultra 🦊"))

@bot.event
async def on_ready():
print(f"🦊 Online: {bot.user}")
status.start()

─────────────────────────────────────────────

🌐 KEEP ALIVE

─────────────────────────────────────────────

app = Flask("")

@app.route("/")
def home():
return "Fox Terminal Online"

def run():
app.run(host="0.0.0.0", port=8080)

def keep_alive():
Thread(target=run).start()

─────────────────────────────────────────────

🚀 START

─────────────────────────────────────────────

if name == "main":
keep_alive()
bot.run(TOKEN)
