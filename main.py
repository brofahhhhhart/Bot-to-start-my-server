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

# ================= FIREBASE (Corrigido) =================
def fb_get():
    try:
        r = requests.get(f"{FIREBASE_URL}/packages.json")
        data = r.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return list(data.values())
        return []
    except:
        return []

def fb_save(data):
    try:
        requests.put(f"{FIREBASE_URL}/packages.json", json=list(set(data)))  # remove duplicatas
    except:
        pass

# ================= PERMISSÃO =================
def autorizado(member):
    return any(role.id == CARGO_ID for role in member.roles)

# ================= LOADER ANIMADO =================
async def loader(msg):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(20):
        frame = frames[i % len(frames)]
        barra = "█" * (i // 3) + "░" * (8 - i // 3)
        await msg.edit(content=f"```{frame} Executando...\n[{barra}] {min(i*5, 100)}%```")
        await asyncio.sleep(0.25)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"🦊 Bot ON: {bot.user}")
    for p in fb_get():
        os.system(f"pip install {p}")

# ================= TERMINAL =================
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild or not msg.content.strip():
        return

    content = msg.content.strip()
    if content.startswith("!"):
        await bot.process_commands(msg)
        return

    if not autorizado(msg.author):
        return await msg.reply("❌ Sem permissão.")

    comando_lower = content.lower()

    # Filtro de comandos
    if not any(comando_lower.startswith(c) for c in ["pip install ", "mkdir ", "ls", "echo", "python", "node", "npm", "help"]):
        return await msg.reply("❌ Comando não reconhecido.")

    # ================= LOADING INICIAL =================
    loading = await msg.reply("```Iniciando terminal...```")
    await loader(loading)

    # ================= PIP INSTALL - ESTILO TERMUX =================
    if comando_lower.startswith("pip install "):
        pkg = content[12:].strip()
        
        # Mensagem de instalação abaixo do loader
        install_msg = await msg.channel.send(f"```📦 Installing {pkg}...```")
        
        try:
            proc = subprocess.run(f"pip install {pkg}", shell=True, capture_output=True, text=True, timeout=90)
            
            if proc.returncode == 0:
                lista = fb_get()
                if pkg not in lista:
                    lista.append(pkg)
                    fb_save(lista)
                
                await install_msg.edit(content=f"```✅ {pkg} instalado com sucesso!```")
                await loading.edit(content=f"```$ {content}\n✅ Sucesso!```")
            else:
                await install_msg.edit(content=f"```❌ Erro ao instalar {pkg}:\n{proc.stderr[:1000]}```")
        except Exception as e:
            await install_msg.edit(content=f"```❌ Erro: {str(e)}```")
        
        return

    # ================= OUTROS COMANDOS =================
    if comando_lower.startswith("mkdir "):
        nome = content[6:].strip()
        cat = discord.utils.get(msg.guild.categories, name=CATEGORIA) or await msg.guild.create_category(CATEGORIA)
        canal = await msg.guild.create_text_channel(nome, category=cat)
        await loading.edit(content=f"```📁 Canal '{nome}' criado!\n{canal.mention}```")
        return

    # Execução normal
    try:
        proc = subprocess.run(content, shell=True, capture_output=True, text=True, timeout=30)
        output = proc.stdout + proc.stderr or "✔ Executado com sucesso."
        await loading.edit(content=f"```\n$ {content}\n\n{output[:1800]}\n```")
    except Exception as e:
        await loading.edit(content=f"```❌ Erro: {str(e)}```")

    await bot.process_commands(msg)

# ================= KEEP ALIVE =================
from flask import Flask
from threading import Thread
app = Flask("")
@app.route("/") 
def home(): return "Online"
def run(): app.run(host="0.0.0.0", port=8080)
def keep_alive(): Thread(target=run).start()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
