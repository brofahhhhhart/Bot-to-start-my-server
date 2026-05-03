import discord
from discord.ext import commands
import subprocess
import asyncio
import os
import requests
import time
import shlex

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

# ================= LOADER ANIMADO =================
async def loader(msg, texto_inicial="Iniciando terminal..."):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(25):  # \~5 segundos de animação
        frame = frames[i % len(frames)]
        barra = "█" * (i // 3) + "░" * (8 - i // 3)
        await msg.edit(content=f"```{frame} {texto_inicial}\n[{barra}] {i*4}%```")
        await asyncio.sleep(0.2)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"🦊 Bot ON: {bot.user}")
    # Reinstala pacotes salvos
    pkgs = fb_get()
    if pkgs:
        print("📦 Reinstalando pacotes salvos...")
        for p in pkgs:
            os.system(f"pip install {p}")

# ================= TERMINAL =================
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:
        return

    content = msg.content.strip()
    if not content:
        return

    # Ignora comandos do bot (!)
    if content.startswith("!"):
        await bot.process_commands(msg)
        return

    if not autorizado(msg.author):
        return await msg.reply("❌ Você não tem permissão para usar o terminal.")

    # ================= FILTRO: Só executa comandos conhecidos =================
    comando = content.split()[0].lower()

    comandos_permitidos = {
        "pip", "mkdir", "ls", "cd", "echo", "cat", "python", "node", "npm",
        "clear", "whoami", "uptime", "date", "ping", "help"
    }

    if comando not in comandos_permitidos and not content.startswith(("sudo ", "apt ", "pkg ")):
        return await msg.reply("❌ Comando não reconhecido. Digite `help` para ver os comandos disponíveis.")

    # Loader
    loading = await msg.reply("```Iniciando terminal...```")
    await loader(loading, "Executando...")

    # ================= COMANDOS ESPECIAIS =================
    if content.startswith("pip install "):
        pkg = content.replace("pip install ", "").strip()
        lista = fb_get()

        await loading.edit(content="```📦 Instalando pacote...```")
        try:
            proc = subprocess.run(f"pip install {pkg}", shell=True, capture_output=True, text=True, timeout=60)
            
            if proc.returncode == 0:
                if pkg not in lista:
                    lista.append(pkg)
                    fb_save(lista)
                await loading.edit(content=f"```✅ {pkg} instalado com sucesso!```")
            else:
                await loading.edit(content=f"```❌ Erro na instalação:\n{proc.stderr[:1500]}```")
        except Exception as e:
            await loading.edit(content=f"```❌ Erro: {str(e)}```")
        return

    elif content.startswith("mkdir "):
        nome = content.replace("mkdir ", "").strip()
        cat = discord.utils.get(msg.guild.categories, name=CATEGORIA)
        if not cat:
            cat = await msg.guild.create_category(CATEGORIA)
        canal = await msg.guild.create_text_channel(nome, category=cat)
        return await loading.edit(content=f"```📁 Canal '{nome}' criado com sucesso!\n{canal.mention}```")

    # ================= EXECUÇÃO GERAL =================
    try:
        start = time.time()
        proc = subprocess.run(content, shell=True, capture_output=True, text=True, timeout=30)
        output = proc.stdout + proc.stderr
        tempo = round(time.time() - start, 2)
    except subprocess.TimeoutExpired:
        output = "⏰ Comando demorou muito (timeout)"
        tempo = 30
    except Exception as e:
        output = str(e)
        tempo = 0

    if not output.strip():
        output = "✔ Comando executado com sucesso (sem saída)"

    await loading.edit(content=f"""```
$ {content}

{output[:1800]}

⏱ {tempo}s
```""")

    await bot.process_commands(msg)

# ================= KEEP ALIVE (Render) =================
from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "🦊 Terminal Bot Online"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ================= START =================
if __name__ == "__main__":
    if not TOKEN or not FIREBASE_URL:
        print("❌ Configure as variáveis DISCORD_TOKEN e FIREBASE_URL")
        exit()
    keep_alive()
    bot.run(TOKEN)
