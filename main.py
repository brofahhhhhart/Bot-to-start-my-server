import discord
import asyncio
import subprocess
import os
import json
import sys
import time

# ================= CONFIG =================
TOKEN = os.environ.get("TOKEN")
CARGO_ID = 1465895263582294271

PKG_DIR = "./packages"
DB_FILE = "packages.json"

os.makedirs(PKG_DIR, exist_ok=True)
sys.path.append(PKG_DIR)

# ================= DATABASE =================
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_pkg(pkg):
    data = load_db()
    if pkg not in data:
        data.append(pkg)
        save_db(data)

# ================= DISCORD =================
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

def has_perm(member):
    return any(r.id == CARGO_ID for r in member.roles)

# ================= TERMINAL =================
SAFE_COMMANDS = [
    "pip install",
    "pip uninstall",
    "pip list",
    "ls", "pwd", "whoami",
    "echo", "cat",
    "curl", "wget"
]

def is_safe(cmd):
    return any(cmd.startswith(s) for s in SAFE_COMMANDS)

async def run(cmd):
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            cwd=PKG_DIR,
            capture_output=True,
            text=True
        )
        out = r.stdout or r.stderr
        return out[:1800] if out else "✔ OK"
    except Exception as e:
        return str(e)

# ================= LOADER BONITO =================
async def loader(msg, title="Carregando"):
    blocks = ["░", "▒", "▓", "█"]
    for i in range(0, 101, 10):
        bar = "█" * (i//10) + "░" * (10 - i//10)
        txt = f"""
╔══════════════════════════╗
║  {title}
║
║  [{bar}] {i}%
║
║  Sistema ativo...
╚══════════════════════════╝
"""
        await msg.edit(content=f"```bash\n{txt}\n```")
        await asyncio.sleep(0.3)

# ================= REINSTALAR =================
async def reinstall_all():
    pkgs = load_db()
    for p in pkgs:
        await run(f"pip install {p} --target={PKG_DIR}")

# ================= EVENTOS =================
@bot.event
async def on_ready():
    print(f"🦊 Bot online: {bot.user}")
    await reinstall_all()

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    if not has_perm(msg.author):
        return

    content = msg.content.strip()

    # ================= OI (modo terminal bonito) =================
    if content.lower() in ["oi", "ola", "hello"]:
        m = await msg.channel.send("```bash\nInicializando...\n```")
        await loader(m, "Boot Fox Terminal")

        await m.edit(content="""```bash
✔ Sistema Linux carregado
✔ Pacotes persistentes ativos
✔ Memória virtual pronta

$ _
```""")
        return

    # ================= INSTALAR =================
    if content.startswith("pip install"):
        pkg = content.split(" ", 2)[-1]

        m = await msg.channel.send(f"```bash\n$ {content}\n```")
        await loader(m, f"Instalando {pkg}")

        out = await run(f"pip install {pkg} --target={PKG_DIR}")

        add_pkg(pkg)

        await m.edit(content=f"""```bash
$ {content}

{out}

✔ Instalado localmente
✔ Salvo no sistema
```""")
        return

    # ================= LISTAR =================
    if content == "pacotes":
        data = load_db()
        txt = "\n".join(data) if data else "Nenhum pacote"

        await msg.channel.send(f"""```bash
Pacotes salvos:

{txt}
```""")
        return

    # ================= COMANDOS =================
    if not is_safe(content):
        await msg.channel.send("❌ Comando não permitido")
        return

    m = await msg.channel.send(f"```bash\n$ {content}\n```")
    await loader(m, "Executando comando")

    out = await run(content)

    await m.edit(content=f"""```bash
$ {content}

{out}
```""")

# ================= START =================
bot.run(TOKEN)
