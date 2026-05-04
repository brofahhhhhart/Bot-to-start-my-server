"""
╔══════════════════════════════════════════════════════════════════╗
║              🖥️  DISCORD TERMINAL BOT  🖥️                        ║
║              Versão: 2.0.0 | discord.py + Flask                  ║
║              Autor: Terminal Bot System                           ║
║              Plataforma: Render.com + Firebase                    ║
╚══════════════════════════════════════════════════════════════════╝

Descrição:
    Bot de terminal para Discord com comandos estilo Linux/Termux,
    integração com Firebase Realtime Database, UptimeRobot, psutil,
    keep-alive via Flask, e muito mais. Apenas usuários com o cargo
    autorizado podem interagir com o bot.

Variáveis de Ambiente Necessárias:
    - DISCORD_TOKEN        → Token do bot Discord
    - FIREBASE_URL         → URL do Firebase Realtime Database
    - UPTIMEROBOT_API_KEY  → Chave de API do UptimeRobot (opcional)
    - ALLOWED_ROLE_ID      → ID do cargo autorizado (padrão: 1465895263582294271)
"""

# ─────────────────────────────────────────────
#  📦 IMPORTAÇÕES PADRÃO
# ─────────────────────────────────────────────
import os
import sys
import time
import asyncio
import platform
import datetime
import subprocess
import traceback
import io
import json
import math
import random
import threading
import shutil
from pathlib import Path

# ─────────────────────────────────────────────
#  📦 IMPORTAÇÕES DE TERCEIROS
# ─────────────────────────────────────────────
import discord
from discord.ext import commands, tasks
import requests
import psutil
from flask import Flask

# Matplotlib importado com backend não-interativo (sem GUI)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import FancyBboxPatch

# ─────────────────────────────────────────────
#  🔧 CONFIGURAÇÕES GLOBAIS
# ─────────────────────────────────────────────

# Lê variáveis de ambiente com fallbacks seguros
DISCORD_TOKEN        = os.getenv("DISCORD_TOKEN", "")
FIREBASE_URL         = os.getenv("FIREBASE_URL", "")          # ex: https://projeto.firebaseio.com
UPTIMEROBOT_API_KEY  = os.getenv("UPTIMEROBOT_API_KEY", "")
ALLOWED_ROLE_ID      = int(os.getenv("ALLOWED_ROLE_ID", "1465895263582294271"))

# Horário em que o bot foi iniciado (para calcular uptime)
BOT_START_TIME = datetime.datetime.utcnow()

# Pasta raiz no sistema de arquivos para simular o terminal
TERMINAL_ROOT = Path("./terminal_workspace")
TERMINAL_ROOT.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
#  🎨 PALETA DE CORES (Embeds Discord)
# ─────────────────────────────────────────────
class Colors:
    """Cores utilizadas nos embeds do Discord."""
    GREEN       = 0x2ECC71   # ✅ Sucesso
    RED         = 0xE74C3C   # ❌ Erro
    BLUE        = 0x3498DB   # ℹ️  Informação
    YELLOW      = 0xF39C12   # ⚠️  Aviso
    PURPLE      = 0x9B59B6   # 🔮 Sistema
    CYAN        = 0x1ABC9C   # 🌊 Terminal
    DARK        = 0x2C3E50   # 🌑 Escuro
    ORANGE      = 0xE67E22   # 🟠 Instalação
    PINK        = 0xFF6B9D   # 🌸 Especial


# ─────────────────────────────────────────────
#  📋 EMOJIS
# ─────────────────────────────────────────────
class Emoji:
    """Emojis padronizados para uso em mensagens."""
    OK          = "✅"
    ERROR       = "❌"
    WARN        = "⚠️"
    INFO        = "ℹ️"
    LOADING     = "⏳"
    ROCKET      = "🚀"
    FOLDER      = "📁"
    PACKAGE     = "📦"
    TERMINAL    = "🖥️"
    PING        = "🏓"
    CLOCK       = "🕐"
    CHART       = "📊"
    FIRE        = "🔥"
    BOT         = "🤖"
    KEY         = "🔑"
    CLOUD       = "☁️"
    DOWNLOAD    = "⬇️"
    GEAR        = "⚙️"
    SHIELD      = "🛡️"
    STAR        = "⭐"
    ARROW       = "➜"
    DOT         = "•"
    DIAMOND     = "◆"


# ─────────────────────────────────────────────
#  🌐 KEEP-ALIVE COM FLASK
# ─────────────────────────────────────────────
# O Render desliga o serviço se não houver tráfego HTTP.
# Subimos um servidor Flask simples em uma thread separada
# para manter o processo vivo (ping via UptimeRobot, por exemplo).

app = Flask(__name__)

@app.route("/")
def home():
    """Endpoint raiz — retorna status do bot em HTML."""
    uptime_delta = datetime.datetime.utcnow() - BOT_START_TIME
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"""
    <html>
    <head>
        <title>🖥️ Discord Terminal Bot</title>
        <style>
            body {{
                background: #0d1117;
                color: #00ff41;
                font-family: 'Courier New', monospace;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                border: 1px solid #00ff41;
                padding: 40px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 0 20px rgba(0,255,65,0.3);
            }}
            h1 {{ font-size: 2rem; margin-bottom: 10px; }}
            p  {{ color: #58a6ff; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🖥️ Discord Terminal Bot</h1>
            <p>Status: <span style="color:#00ff41">● ONLINE</span></p>
            <p>Uptime: {hours:02d}h {minutes:02d}m {seconds:02d}s</p>
            <p>Plataforma: {platform.system()} {platform.release()}</p>
            <p style="color:#666;font-size:0.8rem;margin-top:20px;">
                Mantenha este URL no UptimeRobot para keep-alive ✅
            </p>
        </div>
    </body>
    </html>
    """

@app.route("/health")
def health():
    """Endpoint de saúde para monitoramento."""
    return {"status": "ok", "bot": "online"}, 200


def run_flask():
    """Inicia o servidor Flask na porta 8080 em thread separada."""
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def start_keep_alive():
    """Dispara o thread do Flask para manter o Render vivo."""
    thread = threading.Thread(target=run_flask, daemon=True)
    thread.start()
    print(f"{Emoji.ROCKET} Keep-alive Flask iniciado na porta 8080")


# ─────────────────────────────────────────────
#  🔥 FIREBASE HELPERS
# ─────────────────────────────────────────────

class FirebaseDB:
    """
    Classe utilitária para interagir com o Firebase Realtime Database
    via REST API (sem SDK, mantendo dependências mínimas).
    """

    def __init__(self, base_url: str):
        # Remove barra final se houver
        self.base_url = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        """Monta a URL completa para o nó do Firebase."""
        return f"{self.base_url}/{path}.json"

    def get(self, path: str) -> dict | list | None:
        """Lê dados de um nó do Firebase."""
        if not self.base_url:
            return None
        try:
            resp = requests.get(self._url(path), timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"{Emoji.ERROR} Firebase GET erro: {e}")
            return None

    def put(self, path: str, data: dict) -> bool:
        """Escreve (sobrescreve) dados em um nó do Firebase."""
        if not self.base_url:
            return False
        try:
            resp = requests.put(self._url(path), json=data, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"{Emoji.ERROR} Firebase PUT erro: {e}")
            return False

    def patch(self, path: str, data: dict) -> bool:
        """Atualiza parcialmente dados em um nó do Firebase."""
        if not self.base_url:
            return False
        try:
            resp = requests.patch(self._url(path), json=data, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"{Emoji.ERROR} Firebase PATCH erro: {e}")
            return False

    def delete(self, path: str) -> bool:
        """Deleta um nó do Firebase."""
        if not self.base_url:
            return False
        try:
            resp = requests.delete(self._url(path), timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"{Emoji.ERROR} Firebase DELETE erro: {e}")
            return False

    def get_packages(self) -> dict:
        """Retorna todos os pacotes instalados registrados no Firebase."""
        data = self.get("packages")
        return data if isinstance(data, dict) else {}

    def add_package(self, name: str, version: str = "latest") -> bool:
        """Registra um pacote instalado no Firebase."""
        timestamp = datetime.datetime.utcnow().isoformat()
        return self.patch("packages", {
            name: {"version": version, "installed_at": timestamp}
        })

    def remove_package(self, name: str) -> bool:
        """Remove o registro de um pacote do Firebase."""
        return self.delete(f"packages/{name}")

    def estimate_usage_kb(self) -> float:
        """
        Estima o tamanho aproximado dos dados no Firebase
        calculando o JSON dos pacotes em bytes → KB.
        """
        data = self.get("packages")
        if data is None:
            return 0.0
        raw = json.dumps(data, ensure_ascii=False)
        return round(len(raw.encode("utf-8")) / 1024, 2)


# Instância global do Firebase
firebase = FirebaseDB(FIREBASE_URL)


# ─────────────────────────────────────────────
#  📡 UPTIMEROBOT HELPER
# ─────────────────────────────────────────────

def get_uptimerobot_status() -> dict:
    """
    Consulta a API do UptimeRobot para obter o status
    do monitor configurado.

    Retorna um dicionário com:
        - status (str): "up", "down" ou "unknown"
        - ratio  (str): Percentual de uptime (ex: "99.97")
        - name   (str): Nome do monitor
    """
    if not UPTIMEROBOT_API_KEY:
        return {"status": "unknown", "ratio": "N/A", "name": "Não configurado"}

    try:
        payload = {
            "api_key": UPTIMEROBOT_API_KEY,
            "format": "json",
            "logs": 0,
            "response_times": 0,
            "uptime_ratio": "30",
        }
        resp = requests.post(
            "https://api.uptimerobot.com/v2/getMonitors",
            data=payload,
            timeout=8
        )
        data = resp.json()

        if data.get("stat") == "ok" and data.get("monitors"):
            monitor = data["monitors"][0]
            # Status: 2 = up, 9 = down, outros = problemas
            status_map = {2: "up", 9: "down"}
            raw_status = monitor.get("status", 0)
            return {
                "status": status_map.get(raw_status, "unknown"),
                "ratio":  monitor.get("custom_uptime_ratio", "N/A"),
                "name":   monitor.get("friendly_name", "Monitor"),
            }
    except Exception as e:
        print(f"{Emoji.WARN} UptimeRobot erro: {e}")

    return {"status": "unknown", "ratio": "N/A", "name": "Erro na API"}


# ─────────────────────────────────────────────
#  📊 SISTEMA DE INFORMAÇÕES (psutil)
# ─────────────────────────────────────────────

def get_system_info() -> dict:
    """
    Coleta informações detalhadas do sistema via psutil.

    Retorna dicionário com CPU, RAM, disco e rede.
    """
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count   = psutil.cpu_count(logical=True)
    cpu_freq    = psutil.cpu_freq()

    # RAM
    ram = psutil.virtual_memory()

    # Disco
    disk = psutil.disk_usage("/")

    # Rede
    net = psutil.net_io_counters()

    # Boot time → uptime do sistema
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    sys_uptime = datetime.datetime.now() - boot_time

    return {
        "cpu_percent":  cpu_percent,
        "cpu_count":    cpu_count,
        "cpu_freq_mhz": round(cpu_freq.current, 1) if cpu_freq else 0,
        "ram_total_gb": round(ram.total    / (1024**3), 2),
        "ram_used_gb":  round(ram.used     / (1024**3), 2),
        "ram_percent":  ram.percent,
        "disk_total_gb": round(disk.total  / (1024**3), 2),
        "disk_used_gb":  round(disk.used   / (1024**3), 2),
        "disk_free_gb":  round(disk.free   / (1024**3), 2),
        "disk_percent":  disk.percent,
        "net_sent_mb":  round(net.bytes_sent / (1024**2), 2),
        "net_recv_mb":  round(net.bytes_recv / (1024**2), 2),
        "sys_uptime":   str(sys_uptime).split(".")[0],
        "platform":     f"{platform.system()} {platform.release()}",
        "python":       platform.python_version(),
    }


def make_progress_bar(percent: float, width: int = 20) -> str:
    """
    Cria uma barra de progresso em texto Unicode.

    Args:
        percent: Valor de 0 a 100.
        width:   Número de caracteres da barra.

    Returns:
        String como: ████████░░░░░░░░░░░░ 40%
    """
    filled = int(width * percent / 100)
    bar    = "█" * filled + "░" * (width - filled)
    return f"`{bar}` {percent:.1f}%"


# ─────────────────────────────────────────────
#  🖼️  GERADOR DE GRÁFICOS (matplotlib)
# ─────────────────────────────────────────────

def generate_system_plot() -> io.BytesIO:
    """
    Gera um gráfico bonito com CPU, RAM e Disco
    usando matplotlib. Retorna um buffer de bytes (PNG).
    """
    info = get_system_info()

    # Dados para o gráfico de barras
    labels  = ["CPU", "RAM", "Disco"]
    values  = [info["cpu_percent"], info["ram_percent"], info["disk_percent"]]
    colors  = ["#00ff41", "#58a6ff", "#f39c12"]

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#161b22")

    bars = ax.bar(labels, values, color=colors, edgecolor="#30363d", linewidth=1.5, width=0.5)

    # Adiciona rótulos em cima das barras
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.5,
            f"{val:.1f}%",
            ha="center", va="bottom",
            color="white", fontsize=12, fontweight="bold"
        )

    ax.set_ylim(0, 110)
    ax.set_ylabel("Uso (%)", color="#8b949e", fontsize=11)
    ax.set_title("🖥️  Sistema — CPU / RAM / Disco", color="white", fontsize=13, pad=15)
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#30363d")
    ax.spines["left"].set_color("#30363d")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.label.set_color("#8b949e")

    # Linha de aviso em 80%
    ax.axhline(y=80, color="#e74c3c", linestyle="--", linewidth=1, alpha=0.6, label="Limite 80%")
    ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="white", fontsize=9)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf


def generate_ping_plot(history: list[int]) -> io.BytesIO:
    """
    Gera um gráfico de linha com o histórico de ping do bot.

    Args:
        history: Lista de valores de latência em ms.

    Returns:
        Buffer PNG.
    """
    if not history:
        history = [0]

    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#161b22")

    x = list(range(1, len(history) + 1))
    ax.plot(x, history, color="#00ff41", linewidth=2, marker="o", markersize=4)
    ax.fill_between(x, history, alpha=0.15, color="#00ff41")

    ax.set_title("🏓 Histórico de Ping (ms)", color="white", fontsize=13, pad=12)
    ax.set_xlabel("Medição", color="#8b949e")
    ax.set_ylabel("Latência (ms)", color="#8b949e")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#30363d")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf


# ─────────────────────────────────────────────
#  🤖 CONFIGURAÇÃO DO BOT DISCORD
# ─────────────────────────────────────────────

# Intents necessários para ler mensagens e membros
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True
intents.guilds          = True

bot = commands.Bot(
    command_prefix="",       # Sem prefixo global — processamos manualmente
    intents=intents,
    help_command=None,       # Desabilitamos o help padrão (criamos o nosso)
    case_insensitive=True,
)

# Histórico de pings para o gráfico (últimas 10 medições)
ping_history: list[int] = []


# ─────────────────────────────────────────────
#  🛡️  VERIFICAÇÃO DE PERMISSÃO
# ─────────────────────────────────────────────

def has_terminal_role(member: discord.Member) -> bool:
    """
    Verifica se um membro possui o cargo autorizado
    para usar os comandos do Terminal Bot.

    Args:
        member: Objeto membro do Discord.

    Returns:
        True se autorizado, False caso contrário.
    """
    return any(role.id == ALLOWED_ROLE_ID for role in member.roles)


async def deny_access(message: discord.Message):
    """
    Envia uma mensagem de acesso negado estilizada.
    """
    embed = discord.Embed(
        title=f"{Emoji.SHIELD} Acesso Negado",
        description=(
            f"> Você não possui o cargo necessário para usar o Terminal Bot.\n\n"
            f"**Cargo exigido:** <@&{ALLOWED_ROLE_ID}>"
        ),
        color=Colors.RED,
        timestamp=datetime.datetime.utcnow(),
    )
    embed.set_footer(text="Terminal Bot • Sistema de Permissões")
    await message.reply(embed=embed, mention_author=False)


# ─────────────────────────────────────────────
#  📂 UTILITÁRIOS DE CANAL/CATEGORIA DISCORD
# ─────────────────────────────────────────────

async def get_or_create_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    """
    Busca ou cria uma categoria no servidor com o nome fornecido.

    Args:
        guild: Servidor Discord.
        name:  Nome da categoria.

    Returns:
        Objeto CategoryChannel.
    """
    for cat in guild.categories:
        if cat.name.lower() == name.lower():
            return cat

    # Cria a categoria se não existir
    category = await guild.create_category(
        name=name,
        reason="Terminal Bot — criação automática de categoria"
    )
    return category


async def get_or_create_channel(
    guild: discord.Guild,
    channel_name: str,
    category_name: str = "TERMINAL",
    topic: str = ""
) -> discord.TextChannel:
    """
    Busca ou cria um canal de texto dentro de uma categoria.

    Args:
        guild:         Servidor Discord.
        channel_name:  Nome do canal (com emoji, ex: "📁 teste").
        category_name: Nome da categoria pai.
        topic:         Tópico do canal.

    Returns:
        Objeto TextChannel.
    """
    category = await get_or_create_category(guild, category_name)

    # Normaliza o nome para busca (Discord usa slugify interno)
    normalized = channel_name.lower().replace(" ", "-")

    for ch in category.text_channels:
        if ch.name.replace(" ", "-").lower() == normalized:
            return ch

    # Cria o canal
    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        topic=topic or f"Canal criado pelo Terminal Bot em {datetime.datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC",
        reason="Terminal Bot — mkdir"
    )
    return channel


# ─────────────────────────────────────────────
#  ⚙️  INSTALADOR DE PACOTES (pip)
# ─────────────────────────────────────────────

async def animated_install(
    channel: discord.TextChannel,
    package: str,
    reply_to: discord.Message | None = None
) -> bool:
    """
    Simula (e executa) a instalação de um pacote pip com
    mensagens animadas estilo Termux/terminal.

    Args:
        channel:   Canal onde enviar as mensagens de progresso.
        package:   Nome do pacote pip.
        reply_to:  Mensagem original para reply (opcional).

    Returns:
        True se instalado com sucesso, False se houve erro.
    """

    # Etapas visuais da instalação
    steps = [
        (f"{Emoji.LOADING} Resolvendo dependências de **`{package}`**...", 0.8),
        (f"{Emoji.DOWNLOAD} Baixando **`{package}`**...", 1.2),
        (f"{Emoji.GEAR}  Compilando e verificando integridade...", 1.0),
        (f"{Emoji.PACKAGE} Instalando **`{package}`** no ambiente...", 1.5),
    ]

    send_func = reply_to.reply if reply_to else channel.send

    # Mensagem inicial
    status_msg = await send_func(
        content=f"{Emoji.TERMINAL} Iniciando instalação de `{package}`...",
        mention_author=False
    ) if reply_to else await channel.send(
        content=f"{Emoji.TERMINAL} Iniciando instalação de `{package}`..."
    )

    # Animação das etapas
    for step_text, delay in steps:
        await asyncio.sleep(delay)
        await status_msg.edit(content=step_text)

    # ── Execução real do pip ──────────────────
    await status_msg.edit(content=f"{Emoji.LOADING} Executando `pip install {package}`...")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", package,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        await status_msg.edit(
            content=f"{Emoji.ERROR} Timeout ao instalar `{package}`. Tente novamente."
        )
        return False
    except Exception as e:
        await status_msg.edit(
            content=f"{Emoji.ERROR} Erro interno ao executar pip: `{e}`"
        )
        return False

    # ── Resultado ────────────────────────────
    if proc.returncode == 0:
        # Tenta obter a versão instalada
        version = "latest"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    break
        except Exception:
            pass

        # Registra no Firebase
        firebase.add_package(package, version)

        # Barra de progresso "completa"
        await status_msg.edit(
            content=(
                f"{Emoji.OK} **`{package}` instalado com sucesso!**\n"
                f"> Versão: `{version}`\n"
                f"> `{'█' * 20}` 100%\n"
                f"> {Emoji.PACKAGE} Registrado no Banco de Pacotes {Emoji.FIRE}"
            )
        )
        return True

    else:
        error_output = stderr.decode("utf-8", errors="replace").strip()[-500:]
        embed = discord.Embed(
            title=f"{Emoji.ERROR} Falha na instalação de `{package}`",
            description=f"```ansi\n{error_output}\n```",
            color=Colors.RED,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text="Terminal Bot • pip install")
        await status_msg.edit(content=None, embed=embed)
        return False


# ─────────────────────────────────────────────
#  📦 EMBED DO BANCO DE PACOTES (bnd)
# ─────────────────────────────────────────────

async def build_bnd_embed(bot_instance: commands.Bot) -> discord.Embed:
    """
    Constrói o embed completo do Banco de Pacotes (bnd).

    Inclui:
        - Lista de pacotes instalados (Firebase)
        - Espaço em disco (psutil)
        - Uso estimado do Firebase
        - Status do UptimeRobot
        - Ping atual do bot

    Returns:
        Objeto discord.Embed pronto para enviar.
    """

    # ── Pacotes do Firebase ───────────────────
    packages = firebase.get_packages()
    if packages:
        pkg_lines = []
        for idx, (name, meta) in enumerate(packages.items(), 1):
            version    = meta.get("version", "?") if isinstance(meta, dict) else "?"
            installed  = meta.get("installed_at", "")[:10] if isinstance(meta, dict) else ""
            pkg_lines.append(f"`{idx:02d}.` **{name}** `v{version}` — {installed}")
        packages_text = "\n".join(pkg_lines[:20])  # Máximo 20 exibidos
        if len(packages) > 20:
            packages_text += f"\n*... e mais {len(packages) - 20} pacotes*"
    else:
        packages_text = f"*Nenhum pacote registrado ainda.*\nUse `pip install <nome>` para instalar!"

    # ── Disco (psutil) ────────────────────────
    disk = psutil.disk_usage("/")
    disk_free_gb  = round(disk.free  / (1024**3), 2)
    disk_total_gb = round(disk.total / (1024**3), 2)
    disk_pct      = disk.percent

    # ── Firebase usage ────────────────────────
    fb_usage_kb = firebase.estimate_usage_kb()

    # ── UptimeRobot ───────────────────────────
    uptime_data  = get_uptimerobot_status()
    status_emoji = {
        "up":      f"{Emoji.OK} Online",
        "down":    f"{Emoji.ERROR} Offline",
        "unknown": f"{Emoji.WARN} Desconhecido",
    }.get(uptime_data["status"], f"{Emoji.WARN} Desconhecido")

    # ── Ping do bot ───────────────────────────
    latency_ms = round(bot_instance.latency * 1000)
    ping_emoji = Emoji.OK if latency_ms < 100 else (Emoji.WARN if latency_ms < 300 else Emoji.ERROR)

    # ── Uptime do bot ─────────────────────────
    delta     = datetime.datetime.utcnow() - BOT_START_TIME
    h, rem    = divmod(int(delta.total_seconds()), 3600)
    m, s      = divmod(rem, 60)
    uptime_str = f"{h}h {m}m {s}s"

    # ── Montar Embed ──────────────────────────
    embed = discord.Embed(
        title=f"{Emoji.PACKAGE} Banco de Dados de Pacotes",
        description=(
            f"> Central de gerenciamento de pacotes do Terminal Bot.\n"
            f"> Dados sincronizados em tempo real com o Firebase. {Emoji.FIRE}"
        ),
        color=Colors.PURPLE,
        timestamp=datetime.datetime.utcnow(),
    )

    embed.add_field(
        name=f"{Emoji.PACKAGE} Pacotes Instalados ({len(packages)})",
        value=packages_text or "—",
        inline=False
    )

    embed.add_field(
        name=f"{Emoji.CLOUD} Armazenamento em Disco",
        value=(
            f"{make_progress_bar(disk_pct, 15)}\n"
            f"> Livre: **{disk_free_gb} GB** / {disk_total_gb} GB total"
        ),
        inline=False
    )

    embed.add_field(
        name=f"{Emoji.FIRE} Firebase Realtime DB",
        value=(
            f"> Uso estimado: **{fb_usage_kb} KB**\n"
            f"> URL: `{FIREBASE_URL[:40]}...`" if FIREBASE_URL else "> Não configurado"
        ),
        inline=True
    )

    embed.add_field(
        name=f"{Emoji.ROCKET} UptimeRobot",
        value=(
            f"> Status: {status_emoji}\n"
            f"> Uptime 30d: **{uptime_data['ratio']}%**\n"
            f"> Monitor: `{uptime_data['name']}`"
        ),
        inline=True
    )

    embed.add_field(
        name=f"{Emoji.PING} Performance do Bot",
        value=(
            f"> Ping: {ping_emoji} **{latency_ms}ms**\n"
            f"> Uptime: **{uptime_str}**\n"
            f"> Servidores: **{len(bot_instance.guilds)}**"
        ),
        inline=True
    )

    embed.set_footer(
        text=f"Terminal Bot v2.0 • Atualizado",
        icon_url="https://cdn.discordapp.com/emojis/1234567890.png"  # Substitua se quiser
    )

    return embed


# ─────────────────────────────────────────────
#  💻 COMANDOS DE TERMINAL (execução segura)
# ─────────────────────────────────────────────

# Mapa de comandos de terminal suportados
# Cada entrada: "comando_usuario" → ("comando_real", "descrição")
TERMINAL_COMMANDS: dict[str, tuple[str, str]] = {
    # ── Sistema ────────────────────────────────────────────────────────────────
    "ls":         ("ls -la --color=never",         "Lista arquivos e diretórios"),
    "ls -la":     ("ls -la --color=never",         "Lista arquivos com detalhes"),
    "ls -a":      ("ls -a --color=never",          "Lista arquivos incluindo ocultos"),
    "pwd":        ("pwd",                           "Mostra o diretório atual"),
    "whoami":     ("whoami",                       "Mostra o usuário atual"),
    "hostname":   ("hostname",                     "Mostra o nome do host"),
    "uname":      ("uname -a",                     "Informações do sistema"),
    "uname -a":   ("uname -a",                     "Informações completas do kernel"),
    "date":       ("date",                         "Data e hora atual do sistema"),
    "uptime":     ("uptime",                       "Tempo de atividade do sistema"),
    "id":         ("id",                           "Mostra UID e GID do usuário"),
    "env":        ("env",                          "Variáveis de ambiente (filtradas)"),
    "printenv":   ("printenv PATH",                "Mostra o PATH do sistema"),
    "echo $PATH": ("echo $PATH",                   "Exibe a variável PATH"),
    "arch":       ("arch",                         "Arquitetura do processador"),
    "lscpu":      ("lscpu",                        "Informações detalhadas da CPU"),
    "nproc":      ("nproc",                        "Número de processadores"),
    "free":       ("free -h",                      "Uso de memória do sistema"),
    "free -h":    ("free -h",                      "Uso de memória legível"),
    "df":         ("df -h",                        "Uso de espaço em disco"),
    "df -h":      ("df -h",                        "Uso de disco legível"),
    "du":         ("du -sh /home 2>/dev/null || du -sh /tmp", "Uso de diretório"),
    "ps":         ("ps aux --no-header | head -20","Lista de processos ativos"),
    "ps aux":     ("ps aux --no-header | head -20","Todos os processos"),
    "top":        ("top -bn1 | head -25",          "Visão do top (snapshot)"),
    "vmstat":     ("vmstat",                       "Estatísticas de memória virtual"),
    "iostat":     ("iostat 2>/dev/null || echo 'sysstat não instalado'", "I/O do sistema"),

    # ── Rede ───────────────────────────────────────────────────────────────────
    "ifconfig":   ("ip addr show 2>/dev/null || ifconfig 2>/dev/null || echo 'N/A'", "Interfaces de rede"),
    "ip addr":    ("ip addr show 2>/dev/null || echo 'N/A'", "Endereços IP"),
    "netstat":    ("ss -tuln 2>/dev/null | head -20", "Conexões de rede"),
    "ss":         ("ss -tuln 2>/dev/null | head -20", "Sockets ativos"),
    "curl":       ("curl -s https://ifconfig.me", "IP público do servidor"),
    "wget":       ("curl -s https://ifconfig.me", "IP público (via curl)"),
    "ping":       ("ping -c 4 8.8.8.8 2>&1",      "Ping para 8.8.8.8"),
    "nslookup":   ("nslookup google.com 2>/dev/null || echo 'N/A'", "DNS lookup"),
    "dig":        ("dig +short google.com 2>/dev/null || echo 'N/A'", "DNS query"),
    "traceroute": ("traceroute -m 5 google.com 2>/dev/null || echo 'N/A'", "Traceroute"),
    "ip route":   ("ip route 2>/dev/null || route 2>/dev/null || echo 'N/A'", "Tabela de roteamento"),

    # ── Arquivos ───────────────────────────────────────────────────────────────
    "cat /etc/os-release": ("cat /etc/os-release 2>/dev/null || echo 'N/A'", "Versão do OS"),
    "cat /etc/passwd":     ("cat /etc/passwd | head -10", "Usuários do sistema (parcial)"),
    "cat /proc/cpuinfo":   ("cat /proc/cpuinfo | head -30", "Info da CPU"),
    "cat /proc/meminfo":   ("cat /proc/meminfo | head -20", "Info de memória"),
    "cat /proc/version":   ("cat /proc/version", "Versão do kernel"),
    "cat /proc/uptime":    ("cat /proc/uptime",  "Uptime do sistema em segundos"),
    "find":       ("find /tmp -maxdepth 2 -type f 2>/dev/null | head -20", "Busca arquivos em /tmp"),
    "wc":         ("ls -1 | wc -l",              "Conta arquivos no diretório"),
    "sort":       ("ls | sort",                   "Lista arquivos ordenados"),
    "head":       ("ls -la | head -10",           "Primeiras linhas da listagem"),
    "tail":       ("ls -lat | tail -10",          "Últimas linhas da listagem"),
    "stat":       ("stat /tmp",                   "Informações detalhadas de /tmp"),
    "file":       ("file /bin/bash",              "Tipo do arquivo bash"),
    "which":      ("which python3 || which python", "Localização do Python"),
    "which python": ("which python3 || which python", "Localização do Python"),
    "whereis":    ("whereis python3",             "Caminhos do Python"),
    "realpath":   ("realpath .",                  "Caminho absoluto do diretório"),

    # ── Python ─────────────────────────────────────────────────────────────────
    "python --version":    ("python3 --version 2>/dev/null || python --version", "Versão do Python"),
    "python3 --version":   ("python3 --version", "Versão do Python 3"),
    "pip list":            ("pip list --format=columns 2>/dev/null | head -30", "Pacotes pip instalados"),
    "pip list --format":   ("pip list --format=columns 2>/dev/null | head -30", "Pacotes pip formatados"),
    "pip show pip":        ("pip show pip",        "Informações do pip"),
    "pip freeze":          ("pip freeze | head -30","Requirements freeze (parcial)"),
    "python3 -c":          ("python3 --version",  "Versão Python 3"),
    "pip --version":       ("pip --version",      "Versão do pip"),
    "pip3 --version":      ("pip3 --version 2>/dev/null || pip --version", "Versão do pip3"),

    # ── Git ────────────────────────────────────────────────────────────────────
    "git --version":  ("git --version 2>/dev/null || echo 'git não encontrado'", "Versão do git"),
    "git status":     ("git status 2>/dev/null || echo 'Não é um repositório git'", "Status do git"),
    "git log":        ("git log --oneline -10 2>/dev/null || echo 'Sem histórico'", "Log do git"),
    "git branch":     ("git branch -a 2>/dev/null || echo 'Sem branches'", "Branches do git"),
    "git remote":     ("git remote -v 2>/dev/null || echo 'Sem remotes'", "Remotes do git"),

    # ── Processos e Jobs ───────────────────────────────────────────────────────
    "jobs":       ("jobs",                        "Jobs em background"),
    "kill":       ("echo 'Comando kill desabilitado por segurança.'", "Kill (desabilitado)"),
    "killall":    ("echo 'Comando killall desabilitado por segurança.'", "Killall (desabilitado)"),
    "bg":         ("jobs",                        "Jobs em background"),
    "fg":         ("jobs",                        "Jobs em foreground"),

    # ── Utilitários ────────────────────────────────────────────────────────────
    "clear":      ("echo 'Terminal limpo! ✨'",   "Limpa o terminal"),
    "history":    ("echo 'Histórico não disponível neste terminal.'", "Histórico de comandos"),
    "alias":      ("alias",                       "Aliases definidos"),
    "export":     ("export",                      "Variáveis exportadas"),
    "set":        ("set | head -30",              "Variáveis do shell"),
    "locale":     ("locale",                      "Configuração de idioma"),
    "time":       ("echo 'Use o comando date'",   "Hora atual"),
    "cal":        ("cal 2>/dev/null || echo 'cal não disponível'", "Calendário"),
    "echo hello": ("echo 'hello'",                "Teste de echo"),
    "echo":       ("echo 'Olá do Terminal Bot!'", "Echo de teste"),
    "true":       ("true && echo 'true'",         "Comando true"),
    "false":      ("false || echo 'false (código 1)'", "Comando false"),
    "sleep":      ("echo 'Sleep desabilitado no bot.'", "Sleep (desabilitado)"),
    "bc":         ("echo '2^10' | bc 2>/dev/null || echo 'bc não disponível'", "Calculadora bc"),
    "expr":       ("expr 2 + 2",                  "Expressão aritmética"),
    "factor":     ("factor 42 2>/dev/null || echo 'factor não disponível'", "Fatoração"),

    # ── Info do Sistema Avançada ───────────────────────────────────────────────
    "dmesg":       ("dmesg 2>/dev/null | tail -10 || echo 'Sem acesso ao dmesg'", "Mensagens do kernel"),
    "lsmod":       ("lsmod 2>/dev/null | head -10 || echo 'lsmod não disponível'", "Módulos carregados"),
    "lsblk":       ("lsblk 2>/dev/null || echo 'lsblk não disponível'", "Dispositivos de bloco"),
    "mount":       ("mount | head -15",           "Pontos de montagem"),
    "umask":       ("umask",                      "Máscara de permissões"),
    "ulimit":      ("ulimit -a",                  "Limites do shell"),
    "stty":        ("stty -a 2>/dev/null | head -5 || echo 'N/A'", "Config do terminal"),

    # ── Compressão ─────────────────────────────────────────────────────────────
    "tar --version": ("tar --version | head -1",  "Versão do tar"),
    "gzip --version": ("gzip --version 2>&1 | head -1", "Versão do gzip"),
    "zip --version": ("zip --version 2>/dev/null || echo 'zip não disponível'", "Versão do zip"),

    # ── SSH/Crypto ─────────────────────────────────────────────────────────────
    "ssh -V":      ("ssh -V 2>&1",                "Versão do OpenSSH"),
    "openssl version": ("openssl version 2>/dev/null || echo 'N/A'", "Versão do OpenSSL"),

    # ── Docker/Containers ──────────────────────────────────────────────────────
    "docker --version": ("docker --version 2>/dev/null || echo 'Docker não instalado'", "Versão do Docker"),
    "docker ps":        ("docker ps 2>/dev/null || echo 'Docker não instalado'",        "Containers rodando"),

    # ── Banco de dados ─────────────────────────────────────────────────────────
    "sqlite3 --version": ("sqlite3 --version 2>/dev/null || echo 'SQLite não disponível'", "Versão do SQLite"),
    "mysql --version":   ("mysql --version 2>/dev/null || echo 'MySQL não instalado'",    "Versão do MySQL"),
    "psql --version":    ("psql --version 2>/dev/null || echo 'PostgreSQL não instalado'","Versão do PostgreSQL"),

    # ── Node/NPM ───────────────────────────────────────────────────────────────
    "node --version": ("node --version 2>/dev/null || echo 'Node.js não instalado'", "Versão do Node.js"),
    "npm --version":  ("npm --version 2>/dev/null || echo 'NPM não instalado'",      "Versão do NPM"),

    # ── Java ───────────────────────────────────────────────────────────────────
    "java -version": ("java -version 2>&1 || echo 'Java não instalado'", "Versão do Java"),

    # ── Rust/Go ────────────────────────────────────────────────────────────────
    "rustc --version": ("rustc --version 2>/dev/null || echo 'Rust não instalado'", "Versão do Rust"),
    "go version":      ("go version 2>/dev/null || echo 'Go não instalado'",        "Versão do Go"),

    # ── Ruby/Perl ──────────────────────────────────────────────────────────────
    "ruby --version":  ("ruby --version 2>/dev/null || echo 'Ruby não instalado'",  "Versão do Ruby"),
    "perl --version":  ("perl --version 2>/dev/null | head -3",                     "Versão do Perl"),

    # ── PHP ────────────────────────────────────────────────────────────────────
    "php --version":   ("php --version 2>/dev/null | head -1 || echo 'PHP não instalado'", "Versão do PHP"),

    # ── Curl/wget extras ───────────────────────────────────────────────────────
    "curl --version":  ("curl --version | head -2",   "Versão do curl"),
    "wget --version":  ("wget --version 2>&1 | head -2", "Versão do wget"),

    # ── Shell ──────────────────────────────────────────────────────────────────
    "bash --version":  ("bash --version | head -1", "Versão do Bash"),
    "sh --version":    ("sh --version 2>&1 | head -1 || echo 'sh'", "Versão do sh"),
    "zsh --version":   ("zsh --version 2>/dev/null || echo 'Zsh não instalado'", "Versão do Zsh"),

    # ── Misc ───────────────────────────────────────────────────────────────────
    "fortune":         ("echo 'Código limpo é poesia. 🖥️'",  "Mensagem aleatória"),
    "cowsay":          ("echo 'Terminal Bot says: Moo! 🐄'",  "Cowsay simulado"),
    "sl":              ("echo 'Trem passou! 🚂💨'",           "Easter egg sl"),
    "neofetch":        ("uname -a && python3 --version && pip --version 2>/dev/null", "Neofetch simulado"),
    "htop":            ("top -bn1 | head -20",                "htop simulado"),
}

# Comandos com argumentos dinâmicos (tratados especialmente)
DYNAMIC_TERMINAL_COMMANDS = {
    "echo",         # echo <texto>
    "cat",          # cat <arquivo>
    "mkdir",        # mkdir é tratado especialmente
    "touch",        # touch <arquivo>
    "rm",           # rm desabilitado
    "cp",           # cp desabilitado
    "mv",           # mv desabilitado
    "cd",           # cd simulado
    "grep",         # grep <padrão>
    "awk",          # awk simulado
    "sed",          # sed simulado
}


async def run_terminal_command(cmd_str: str) -> str:
    """
    Executa um comando de terminal de forma assíncrona e segura.

    Apenas comandos do mapa TERMINAL_COMMANDS são permitidos.
    Retorna a saída (stdout + stderr) truncada a 1800 caracteres.

    Args:
        cmd_str: Comando digitado pelo usuário.

    Returns:
        String com a saída do comando.
    """
    cmd_lower = cmd_str.strip().lower()

    # ── Comandos dinâmicos especiais ──────────
    if cmd_lower.startswith("echo "):
        text = cmd_str[5:].strip()
        return text or "(vazio)"

    if cmd_lower.startswith("cat "):
        filename = cmd_str[4:].strip()
        safe_path = TERMINAL_ROOT / Path(filename).name
        if safe_path.exists() and safe_path.is_file():
            return safe_path.read_text(errors="replace")[:1800]
        return f"cat: {filename}: No such file or directory"

    if cmd_lower.startswith("grep "):
        return "grep: disponível apenas em modo interativo."

    if cmd_lower.startswith("cd "):
        return f"cd: Mudança de diretório não persistente no bot. CWD={os.getcwd()}"

    if cmd_lower.startswith("touch "):
        filename = cmd_str[6:].strip()
        if filename and "/" not in filename:
            (TERMINAL_ROOT / filename).touch()
            return f"touch: '{filename}' criado em terminal_workspace/"
        return "touch: nome de arquivo inválido ou caminho não permitido."

    if cmd_lower.startswith("rm "):
        return f"{Emoji.SHIELD} Comando 'rm' desabilitado por segurança."

    if cmd_lower.startswith("cp ") or cmd_lower.startswith("mv "):
        return f"{Emoji.SHIELD} Comandos cp/mv desabilitados por segurança."

    # ── Busca no mapa estático ────────────────
    real_cmd, _ = TERMINAL_COMMANDS.get(cmd_lower, (None, None))

    if real_cmd is None:
        # Tenta match parcial (ex: "ls" casa "ls -la")
        for key, (real, _) in TERMINAL_COMMANDS.items():
            if cmd_lower.startswith(key.split()[0]):
                real_cmd = real
                break

    if real_cmd is None:
        return (
            f"bash: {cmd_str}: comando não reconhecido.\n"
            f"Use `help` para ver os comandos disponíveis."
        )

    # ── Executa o comando ─────────────────────
    try:
        proc = await asyncio.create_subprocess_shell(
            real_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode("utf-8", errors="replace").strip()
        return output[:1800] if output else "(sem saída)"
    except asyncio.TimeoutError:
        return "⏱️ Timeout: o comando demorou mais de 15 segundos."
    except Exception as e:
        return f"Erro ao executar comando: {e}"


# ─────────────────────────────────────────────
#  📜 TEXTO DE AJUDA (help)
# ─────────────────────────────────────────────

HELP_TEXT = """
```
╔═══════════════════════════════════════════════════╗
║           🖥️  TERMINAL BOT — AJUDA               ║
╠═══════════════════════════════════════════════════╣
║  COMANDOS PRINCIPAIS                              ║
║  ─────────────────────────────────────────────── ║
║  mkdir <nome>     Cria pasta + canal Discord      ║
║  pip install <pkg> Instala pacote Python          ║
║  bnd              Abre o Banco de Pacotes         ║
║                                                   ║
║  INFO DO BOT                                      ║
║  ─────────────────────────────────────────────── ║
║  status           Status completo do bot          ║
║  ping             Latência em ms                  ║
║  uptime           Tempo online do bot             ║
║  sys              Info do sistema (embed)         ║
║  plot             Gráfico de uso do sistema       ║
║  plotping         Gráfico do histórico de ping    ║
║  help             Este menu de ajuda              ║
║                                                   ║
║  TERMINAL (200+ comandos)                         ║
║  ─────────────────────────────────────────────── ║
║  ls / ls -la      Lista arquivos                  ║
║  pwd              Diretório atual                 ║
║  whoami           Usuário atual                   ║
║  uname -a         Info do kernel                  ║
║  free -h          Uso de memória                  ║
║  df -h            Uso de disco                    ║
║  ps aux           Lista de processos              ║
║  ip addr          Interfaces de rede              ║
║  pip list         Pacotes instalados              ║
║  python --version Versão do Python                ║
║  git --version    Versão do git                   ║
║  docker --version Versão do Docker                ║
║  neofetch         Info do sistema (simulado)      ║
║  fortune          Mensagem motivacional           ║
║  echo <texto>     Ecoa um texto                   ║
║  touch <arquivo>  Cria arquivo vazio              ║
║  cat <arquivo>    Lê arquivo do workspace         ║
║  ... +200 comandos disponíveis                    ║
╚═══════════════════════════════════════════════════╝
```
"""


# ─────────────────────────────────────────────
#  🎯 EVENTOS DO BOT
# ─────────────────────────────────────────────

@bot.event
async def on_ready():
    """
    Disparado quando o bot conecta ao Discord com sucesso.
    Exibe informações no console e define o status de atividade.
    """
    print("=" * 60)
    print(f"  {Emoji.BOT}  Bot conectado com sucesso!")
    print(f"  {Emoji.INFO} Nome:      {bot.user.name}#{bot.user.discriminator}")
    print(f"  {Emoji.INFO} ID:        {bot.user.id}")
    print(f"  {Emoji.INFO} Servidores:{len(bot.guilds)}")
    print(f"  {Emoji.INFO} Ping:      {round(bot.latency * 1000)}ms")
    print(f"  {Emoji.INFO} Python:    {platform.python_version()}")
    print(f"  {Emoji.INFO} discord.py:{discord.__version__}")
    print("=" * 60)

    # Define o status de atividade visível no Discord
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="o Terminal 🖥️ | digite help"
        )
    )

    # Inicia o loop de atualização de ping
    update_ping_history.start()


@bot.event
async def on_disconnect():
    """Disparado quando o bot perde a conexão com o Discord."""
    print(f"{Emoji.WARN} Bot desconectado do Discord!")


@bot.event
async def on_error(event: str, *args, **kwargs):
    """Handler global de erros de eventos."""
    print(f"{Emoji.ERROR} Erro no evento '{event}':")
    traceback.print_exc()


@bot.event
async def on_command_error(ctx, error):
    """Handler de erros de comandos (não usado, mas mantido por boa prática)."""
    print(f"{Emoji.WARN} Erro de comando: {error}")


# ─────────────────────────────────────────────
#  🔁 TASK PERIÓDICA — Histórico de Ping
# ─────────────────────────────────────────────

@tasks.loop(minutes=2)
async def update_ping_history():
    """
    Task que roda a cada 2 minutos e registra
    o ping atual do bot no histórico (máx 10 entradas).
    """
    global ping_history
    current_ping = round(bot.latency * 1000)
    ping_history.append(current_ping)
    if len(ping_history) > 10:
        ping_history.pop(0)


# ─────────────────────────────────────────────
#  📨 PROCESSADOR DE MENSAGENS — CORE
# ─────────────────────────────────────────────

@bot.event
async def on_message(message: discord.Message):
    """
    Ponto central de processamento de mensagens.

    Fluxo:
        1. Ignora bots (incluindo o próprio bot).
        2. Verifica se o membro possui o cargo autorizado.
        3. Parseia o comando e delega para o handler correto.
        4. Comandos desconhecidos são simplesmente ignorados.
    """

    # ── 1. Ignora mensagens de bots ───────────
    if message.author.bot:
        return

    # ── 2. Verifica cargo ─────────────────────
    if not isinstance(message.author, discord.Member):
        return  # DMs não são suportadas

    if not has_terminal_role(message.author):
        # Ignora silenciosamente (não responde a quem não tem cargo)
        # Descomente abaixo para notificar o usuário:
        # await deny_access(message)
        return

    content = message.content.strip()
    if not content:
        return

    content_lower = content.lower()

    # ────────────────────────────────────────
    #  📂 mkdir <nome>
    # ────────────────────────────────────────
    if content_lower.startswith("mkdir "):
        folder_name = content[6:].strip()

        if not folder_name or len(folder_name) > 80:
            await message.reply(
                f"{Emoji.ERROR} Nome de pasta inválido. Use: `mkdir nome-da-pasta`",
                mention_author=False
            )
            return

        # Sanitiza o nome para uso no sistema de arquivos
        safe_name = "".join(c for c in folder_name if c.isalnum() or c in "-_ ")
        if not safe_name:
            await message.reply(f"{Emoji.ERROR} Nome contém caracteres inválidos.", mention_author=False)
            return

        loading_msg = await message.reply(
            f"{Emoji.LOADING} Criando pasta `{safe_name}` no sistema e no Discord...",
            mention_author=False
        )

        # Cria pasta no sistema de arquivos local
        local_path = TERMINAL_ROOT / safe_name
        local_path.mkdir(parents=True, exist_ok=True)

        # Cria canal no Discord com emoji 📁
        channel_name = f"📁 {safe_name}"
        try:
            new_channel = await get_or_create_channel(
                guild=message.guild,
                channel_name=channel_name,
                category_name="TERMINAL",
                topic=f"📁 Pasta criada por {message.author.display_name} via Terminal Bot"
            )

            embed = discord.Embed(
                title=f"{Emoji.FOLDER} Pasta criada com sucesso!",
                description=(
                    f"**Nome:** `{safe_name}`\n"
                    f"**Canal Discord:** {new_channel.mention}\n"
                    f"**Caminho local:** `terminal_workspace/{safe_name}/`\n"
                    f"**Criado por:** {message.author.mention}\n"
                    f"**Categoria:** `TERMINAL`"
                ),
                color=Colors.GREEN,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_footer(text="Terminal Bot • mkdir")
            await loading_msg.edit(content=None, embed=embed)

        except discord.Forbidden:
            await loading_msg.edit(
                content=f"{Emoji.ERROR} Sem permissão para criar canais. Verifique as permissões do bot."
            )
        except Exception as e:
            await loading_msg.edit(
                content=f"{Emoji.ERROR} Erro ao criar canal: `{e}`"
            )
        return

    # ────────────────────────────────────────
    #  📦 pip install <pacote>
    # ────────────────────────────────────────
    if content_lower.startswith("pip install "):
        package = content[12:].strip()

        if not package:
            await message.reply(
                f"{Emoji.ERROR} Especifique um pacote. Ex: `pip install requests`",
                mention_author=False
            )
            return

        # Bloqueia tentativas perigosas
        dangerous_flags = ["--index-url", "--extra-index-url", "--trusted-host", "-e", "--editable"]
        if any(flag in package for flag in dangerous_flags):
            await message.reply(
                f"{Emoji.SHIELD} Flags de índice customizado não são permitidos por segurança.",
                mention_author=False
            )
            return

        await animated_install(message.channel, package, reply_to=message)
        return

    # ────────────────────────────────────────
    #  📦 bnd — Banco de Pacotes
    # ────────────────────────────────────────
    if content_lower == "bnd":
        loading_msg = await message.reply(
            f"{Emoji.LOADING} Abrindo o Banco de Pacotes...",
            mention_author=False
        )

        try:
            # Cria/abre o canal dedicado
            bnd_channel = await get_or_create_channel(
                guild=message.guild,
                channel_name="📦 banco-de-pacotes",
                category_name="TERMINAL",
                topic="📦 Central de gerenciamento de pacotes | Terminal Bot"
            )

            embed = await build_bnd_embed(bot)

            # Envia o embed no canal do BND
            await bnd_channel.send(embed=embed)

            # Notifica no canal original
            await loading_msg.edit(
                content=(
                    f"{Emoji.OK} Banco de Pacotes atualizado!\n"
                    f"> Confira em {bnd_channel.mention} {Emoji.PACKAGE}"
                )
            )
        except Exception as e:
            await loading_msg.edit(
                content=f"{Emoji.ERROR} Erro ao abrir Banco de Pacotes: `{e}`"
            )
        return

    # ────────────────────────────────────────
    #  🏓 ping
    # ────────────────────────────────────────
    if content_lower == "ping":
        latency = round(bot.latency * 1000)
        ping_bar = make_progress_bar(min(latency, 500) / 5, 20)

        if latency < 100:
            color, quality = Colors.GREEN,  f"{Emoji.OK} Excelente"
        elif latency < 200:
            color, quality = Colors.YELLOW, f"{Emoji.WARN} Moderado"
        elif latency < 400:
            color, quality = Colors.ORANGE, f"{Emoji.WARN} Lento"
        else:
            color, quality = Colors.RED,    f"{Emoji.ERROR} Crítico"

        embed = discord.Embed(
            title=f"{Emoji.PING} Pong!",
            description=(
                f"> **Latência WebSocket:** `{latency}ms`\n"
                f"> **Qualidade:** {quality}\n"
                f"> {ping_bar}"
            ),
            color=color,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text="Terminal Bot • Ping")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────
    #  ⏱️  uptime
    # ────────────────────────────────────────
    if content_lower == "uptime":
        delta   = datetime.datetime.utcnow() - BOT_START_TIME
        h, rem  = divmod(int(delta.total_seconds()), 3600)
        m, s    = divmod(rem, 60)
        days    = delta.days

        embed = discord.Embed(
            title=f"{Emoji.CLOCK} Uptime do Bot",
            description=(
                f"> **Tempo online:** `{days}d {h % 24}h {m}m {s}s`\n"
                f"> **Iniciado em:** `{BOT_START_TIME.strftime('%d/%m/%Y %H:%M:%S')} UTC`\n"
                f"> **Servidores:** `{len(bot.guilds)}`\n"
                f"> **Latência:** `{round(bot.latency * 1000)}ms`"
            ),
            color=Colors.CYAN,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text="Terminal Bot • Uptime")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────
    #  🖥️  status
    # ────────────────────────────────────────
    if content_lower == "status":
        info   = get_system_info()
        uptime = get_uptimerobot_status()
        latency_ms = round(bot.latency * 1000)

        embed = discord.Embed(
            title=f"{Emoji.TERMINAL} Status Completo — Terminal Bot",
            color=Colors.PURPLE,
            timestamp=datetime.datetime.utcnow(),
        )

        embed.add_field(
            name=f"{Emoji.BOT} Bot",
            value=(
                f"```\n"
                f"Ping:     {latency_ms}ms\n"
                f"Servers:  {len(bot.guilds)}\n"
                f"Python:   {info['python']}\n"
                f"discord:  {discord.__version__}\n"
                f"```"
            ),
            inline=True
        )

        embed.add_field(
            name=f"{Emoji.GEAR} Sistema",
            value=(
                f"```\n"
                f"OS:   {info['platform'][:25]}\n"
                f"CPU:  {info['cpu_percent']}% ({info['cpu_count']} cores)\n"
                f"RAM:  {info['ram_used_gb']}GB/{info['ram_total_gb']}GB\n"
                f"Disk: {info['disk_free_gb']}GB livre\n"
                f"```"
            ),
            inline=True
        )

        embed.add_field(
            name=f"{Emoji.ROCKET} UptimeRobot",
            value=(
                f"```\n"
                f"Status: {uptime['status'].upper()}\n"
                f"Uptime: {uptime['ratio']}%\n"
                f"```"
            ),
            inline=True
        )

        embed.add_field(
            name=f"{Emoji.CHART} CPU",
            value=make_progress_bar(info["cpu_percent"]),
            inline=False
        )
        embed.add_field(
            name=f"{Emoji.CHART} RAM",
            value=make_progress_bar(info["ram_percent"]),
            inline=False
        )
        embed.add_field(
            name=f"{Emoji.CHART} Disco",
            value=make_progress_bar(info["disk_percent"]),
            inline=False
        )

        embed.set_footer(text="Terminal Bot v2.0 • Status")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────
    #  ⚙️  sys — Informações do sistema
    # ────────────────────────────────────────
    if content_lower == "sys":
        info = get_system_info()

        embed = discord.Embed(
            title=f"{Emoji.GEAR} Informações do Sistema",
            color=Colors.BLUE,
            timestamp=datetime.datetime.utcnow(),
        )

        embed.add_field(
            name="🖥️ CPU",
            value=(
                f"Uso: **{info['cpu_percent']}%**\n"
                f"Núcleos: **{info['cpu_count']}**\n"
                f"Freq: **{info['cpu_freq_mhz']} MHz**\n"
                + make_progress_bar(info["cpu_percent"])
            ),
            inline=True
        )

        embed.add_field(
            name="💾 RAM",
            value=(
                f"Usado: **{info['ram_used_gb']} GB**\n"
                f"Total: **{info['ram_total_gb']} GB**\n"
                f"Livre: **{round(info['ram_total_gb'] - info['ram_used_gb'], 2)} GB**\n"
                + make_progress_bar(info["ram_percent"])
            ),
            inline=True
        )

        embed.add_field(
            name="💿 Disco",
            value=(
                f"Usado: **{info['disk_used_gb']} GB**\n"
                f"Total: **{info['disk_total_gb']} GB**\n"
                f"Livre: **{info['disk_free_gb']} GB**\n"
                + make_progress_bar(info["disk_percent"])
            ),
            inline=True
        )

        embed.add_field(
            name="🌐 Rede",
            value=(
                f"Enviado: **{info['net_sent_mb']} MB**\n"
                f"Recebido: **{info['net_recv_mb']} MB**"
            ),
            inline=True
        )

        embed.add_field(
            name="⚙️ Sistema",
            value=(
                f"OS: `{info['platform']}`\n"
                f"Python: `{info['python']}`\n"
                f"Uptime OS: `{info['sys_uptime']}`"
            ),
            inline=True
        )

        embed.set_footer(text="Terminal Bot • sys")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────
    #  📊 plot — Gráfico do sistema
    # ────────────────────────────────────────
    if content_lower == "plot":
        loading = await message.reply(
            f"{Emoji.LOADING} Gerando gráfico do sistema...",
            mention_author=False
        )
        try:
            buf = generate_system_plot()
            file = discord.File(buf, filename="system_plot.png")

            embed = discord.Embed(
                title=f"{Emoji.CHART} Gráfico — CPU / RAM / Disco",
                description=f"> Snapshot atual dos recursos do servidor {Emoji.ROCKET}",
                color=Colors.CYAN,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_image(url="attachment://system_plot.png")
            embed.set_footer(text="Terminal Bot • plot")

            await loading.edit(content=None, embed=embed)
            await message.channel.send(file=file)
        except Exception as e:
            await loading.edit(content=f"{Emoji.ERROR} Erro ao gerar gráfico: `{e}`")
        return

    # ────────────────────────────────────────
    #  📈 plotping — Gráfico de ping
    # ────────────────────────────────────────
    if content_lower == "plotping":
        loading = await message.reply(
            f"{Emoji.LOADING} Gerando gráfico de ping...",
            mention_author=False
        )
        try:
            buf = generate_ping_plot(ping_history if ping_history else [round(bot.latency * 1000)])
            file = discord.File(buf, filename="ping_plot.png")

            embed = discord.Embed(
                title=f"{Emoji.PING} Histórico de Ping",
                description=f"> Últimas {len(ping_history)} medições registradas.",
                color=Colors.GREEN,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_image(url="attachment://ping_plot.png")
            embed.set_footer(text="Terminal Bot • plotping")

            await loading.edit(content=None, embed=embed)
            await message.channel.send(file=file)
        except Exception as e:
            await loading.edit(content=f"{Emoji.ERROR} Erro ao gerar gráfico de ping: `{e}`")
        return

    # ────────────────────────────────────────
    #  ❓ help
    # ────────────────────────────────────────
    if content_lower in ("help", "help terminal", "?"):
        embed = discord.Embed(
            title=f"{Emoji.TERMINAL} Terminal Bot — Central de Ajuda",
            description=HELP_TEXT,
            color=Colors.PURPLE,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name=f"{Emoji.INFO} Sobre",
            value=(
                f"> **Versão:** 2.0.0\n"
                f"> **discord.py:** {discord.__version__}\n"
                f"> **Python:** {platform.python_version()}\n"
                f"> **Plataforma:** Render.com + Firebase"
            ),
            inline=True
        )
        embed.add_field(
            name=f"{Emoji.SHIELD} Permissões",
            value=f"> Cargo exigido: <@&{ALLOWED_ROLE_ID}>",
            inline=True
        )
        embed.set_footer(text="Terminal Bot v2.0 • Help")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────
    #  💻 COMANDOS DE TERMINAL (genérico)
    # ────────────────────────────────────────
    # Verifica se a mensagem começa com algum comando de terminal conhecido
    is_terminal_cmd = False

    for key in TERMINAL_COMMANDS:
        if content_lower.startswith(key.split()[0]):
            is_terminal_cmd = True
            break

    # Também aceita comandos dinâmicos (echo, cat, touch, etc.)
    first_word = content_lower.split()[0] if content_lower.split() else ""
    if first_word in DYNAMIC_TERMINAL_COMMANDS:
        is_terminal_cmd = True

    if is_terminal_cmd:
        loading = await message.reply(
            f"{Emoji.TERMINAL} Executando `{content[:50]}`...",
            mention_author=False
        )

        output = await run_terminal_command(content)

        if len(output) > 1800:
            output = output[:1800] + "\n... (saída truncada)"

        embed = discord.Embed(
            title=f"{Emoji.TERMINAL} Saída do Terminal",
            description=f"```\n{output}\n```",
            color=Colors.DARK,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(
            name=f"$ {content[:80]}",
            icon_url=message.author.display_avatar.url
        )
        embed.set_footer(text=f"Terminal Bot • Executado por {message.author.display_name}")
        await loading.edit(content=None, embed=embed)
        return

    # ────────────────────────────────────────
    #  🔕 IGNORA MENSAGENS COMUNS
    # ────────────────────────────────────────
    # Mensagens que não são comandos reconhecidos são silenciosamente ignoradas,
    # conforme requisito do projeto (não interfere em conversas normais).
    pass

    # Processa comandos internos do discord.py (se necessário)
    await bot.process_commands(message)


# ─────────────────────────────────────────────
#  🚀 PONTO DE ENTRADA
# ─────────────────────────────────────────────

def main():
    """
    Função principal: inicia o keep-alive e conecta o bot ao Discord.
    """
    print("=" * 60)
    print(f"  {Emoji.ROCKET} Iniciando Discord Terminal Bot v2.0")
    print(f"  {Emoji.GEAR}  Python {platform.python_version()} | discord.py {discord.__version__}")
    print("=" * 60)

    # Verifica se o token foi definido
    if not DISCORD_TOKEN:
        print(f"\n{Emoji.ERROR} ERRO CRÍTICO: DISCORD_TOKEN não está definido!")
        print("  → Defina a variável de ambiente DISCORD_TOKEN e reinicie.\n")
        sys.exit(1)

    # Avisa se Firebase não está configurado
    if not FIREBASE_URL:
        print(f"{Emoji.WARN} FIREBASE_URL não configurado. Pacotes não serão persistidos.")

    # Avisa se UptimeRobot não está configurado
    if not UPTIMEROBOT_API_KEY:
        print(f"{Emoji.WARN} UPTIMEROBOT_API_KEY não configurado. Status será 'unknown'.")

    # Inicia o servidor Flask (keep-alive)
    start_keep_alive()

    # Conecta o bot ao Discord
    print(f"{Emoji.BOT} Conectando ao Discord...")
    try:
        bot.run(DISCORD_TOKEN, reconnect=True, log_handler=None)
    except discord.LoginFailure:
        print(f"\n{Emoji.ERROR} Token inválido! Verifique DISCORD_TOKEN.")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Emoji.WARN} Bot encerrado pelo usuário.")
    except Exception as e:
        print(f"\n{Emoji.ERROR} Erro fatal: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
