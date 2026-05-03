import discord
from discord.ext import commands
import subprocess
import asyncio
import os
import requests
import time
import psutil  # ← novo

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
        data = r.json()
        return list(data.values()) if isinstance(data, dict) else data if isinstance(data, list) else []
    except:
        return []

def fb_save(data):
    try:
        requests.put(f"{FIREBASE_URL}/packages.json", json=list(set(data)))
    except:
        pass

# ================= PERMISSÃO =================
def autorizado(member):
    return any(role.id == CARGO_ID for role in member.roles)

# ================= LOADER =================
async def loader(msg):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(18):
        frame = frames[i % len(frames)]
        barra = "█" * (i // 3) + "░" * (8 - i // 3)
        await msg.edit(content=f"```{frame} Executando...\n[{barra}] {min(i*6, 100)}%```")
        await asyncio.sleep(0.22)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"🦊 Bot ON: {bot.user}")

# ================= ON_MESSAGE =================
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:
        return

    content = msg.content.strip()
    if not content or content.startswith("!"):
        await bot.process_commands(msg)
        return

    # ================= SÓ ATIVA COM COMANDOS ESPECÍFICOS =================
    comando_lower = content.lower()

    if not any(comando_lower.startswith(x) for x in ["pip install ", "mkdir ", "bnd", "status", "help"]):
        return  # ← Ignora conversa normal

    if not autorizado(msg.author):
        return await msg.reply("❌ Sem permissão.")

    loading = await msg.reply("```Iniciando terminal...```")
    await loader(loading)

    # ================= PIP INSTALL =================
    if comando_lower.startswith("pip install "):
        pkg = content[12:].strip()
        install_msg = await msg.channel.send(f"```📦 Installing {pkg}...```")
        
        try:
            proc = subprocess.run(f"pip install {pkg}", shell=True, capture_output=True, text=True, timeout=90)
            if proc.returncode == 0:
                lista = fb_get()
                if pkg not in lista:
                    lista.append(pkg)
                    fb_save(lista)
                await install_msg.edit(content=f"```✅ {pkg} instalado com sucesso!```")
            else:
                await install_msg.edit(content=f"```❌ Erro ao instalar:\n{proc.stderr[:900]}```")
        except Exception as e:
            await install_msg.edit(content=f"```❌ Erro: {str(e)}```")
        return

    # ================= BANCO DE PACOTES (bnd) =================
    if comando_lower.startswith("bnd"):
        lista = fb_get()
        pacotes = "\n".join([f"• {p}" for p in lista]) if lista else "Nenhum pacote instalado ainda."

        embed = discord.Embed(
            title="📦 Banco de Pacotes Instalados",
            description=pacotes,
            color=0x00ff00
        )
        embed.add_field(name="Total", value=f"{len(lista)} pacotes", inline=True)
        
        # Status do Render
        try:
            disco = psutil.disk_usage('/')
            embed.add_field(name="💾 Espaço no Render", 
                          value=f"{disco.free // (1024**3)}GB livre de {disco.total // (1024**3)}GB", 
                          inline=True)
        except:
            pass

        await loading.edit(content=None, embed=embed)
        return

    # Outros comandos...
    await loading.edit(content="```Comando em desenvolvimento...```")

    await bot.process_commands(msg)

# ================= KEEP ALIVE =================
from flask import Flask
from threading import Thread
app = Flask("")
@app.route("/") 
def home(): return "Online"
def keep_alive(): Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
