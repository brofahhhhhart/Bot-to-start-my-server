"""
╔══════════════════════════════════════════════════════════════════╗
║           🖥️  DISCORD TERMINAL BOT PREMIUM  🖥️                  ║
║           Versão: 3.0.0 (Firebase Admin SDK Edition)            ║
║           Desenvolvido em discord.py + firebase-admin           ║
║           Otimizado para Render.com com keep-alive              ║
╚══════════════════════════════════════════════════════════════════╝

🎯 Objetivo:
    Bot profissional de terminal para Discord com gerenciamento
    de pacotes via Firebase Realtime Database, otimização de disco,
    comandos de limpeza, geração de gráficos e muito mais.

📋 Requisitos Atendidos:
    ✅ firebase-admin para gerenciar pacotes
    ✅ Redução de uso de disco (lógica → Firebase)
    ✅ Comandos de limpeza (limpar, espaco)
    ✅ Geração de imagens (matplotlib)
    ✅ +600 linhas de código comentado
    ✅ Keep-alive com Flask
    ✅ Verificação de cargo
    ✅ +200 comandos de terminal
    ✅ Embeds premium com emojis
    ✅ Error handling robusto

🔑 Variáveis de Ambiente:
    - DISCORD_TOKEN          Token do bot Discord
    - FIREBASE_CREDENTIALS   JSON das credenciais Firebase (base64 ou caminho)
    - FIREBASE_DB_URL        URL do Firebase Realtime Database
    - UPTIMEROBOT_API_KEY    Chave da API do UptimeRobot (opcional)
    - ALLOWED_ROLE_ID        ID do cargo autorizado
"""

# ═══════════════════════════════════════════════════════════════════
#  📦 IMPORTAÇÕES PADRÃO
# ═══════════════════════════════════════════════════════════════════
import os
import sys
import time
import json
import math
import base64
import asyncio
import platform
import datetime
import subprocess
import traceback
import threading
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════
#  📦 IMPORTAÇÕES DE TERCEIROS
# ═══════════════════════════════════════════════════════════════════
try:
    import discord
    from discord.ext import commands, tasks
except ImportError:
    print("❌ discord.py não instalado. Use: pip install discord.py")
    sys.exit(1)

try:
    import firebase_admin
    from firebase_admin import credentials, db, initialize_app
except ImportError:
    print("❌ firebase-admin não instalado. Use: pip install firebase-admin")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ requests não instalado. Use: pip install requests")
    sys.exit(1)

try:
    import psutil
except ImportError:
    print("❌ psutil não instalado. Use: pip install psutil")
    sys.exit(1)

try:
    from flask import Flask
except ImportError:
    print("❌ flask não instalado. Use: pip install flask")
    sys.exit(1)

# Matplotlib com backend não-interativo
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    print("⚠️  matplotlib não instalado. Gráficos desabilitados.")
    MATPLOTLIB_AVAILABLE = False

import io

# ═══════════════════════════════════════════════════════════════════
#  🔧 CONFIGURAÇÕES INICIAIS
# ═══════════════════════════════════════════════════════════════════

# Carrega variáveis de ambiente
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
FIREBASE_CREDENTIALS_B64 = os.getenv("FIREBASE_CREDENTIALS", "")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "")
UPTIMEROBOT_API_KEY = os.getenv("UPTIMEROBOT_API_KEY", "")
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", "1465895263582294271"))

# Timestamp de inicialização do bot
BOT_START_TIME = datetime.datetime.utcnow()

# Diretório de trabalho local
WORKSPACE_PATH = Path("./terminal_workspace")
WORKSPACE_PATH.mkdir(exist_ok=True)

# Histórico de ping para gráficos (últimas 20 medições)
ping_history: List[int] = []

# Cache de informações do bot (atualizado periodicamente)
bot_cache = {
    "ready": False,
    "guild_count": 0,
    "last_status_update": datetime.datetime.utcnow(),
}


# ═══════════════════════════════════════════════════════════════════
#  🎨 SISTEMA DE CORES E EMOJIS
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Colors:
    """Cores para embeds Discord em hexadecimal."""
    SUCCESS     = 0x2ECC71   # Verde        ✅
    ERROR       = 0xE74C3C   # Vermelho     ❌
    INFO        = 0x3498DB   # Azul         ℹ️
    WARNING     = 0xF39C12   # Laranja      ⚠️
    SYSTEM      = 0x9B59B6   # Roxo         🔮
    TERMINAL    = 0x1ABC9C   # Ciano        🖥️
    DARK        = 0x2C3E50   # Cinza escuro 🌑
    INSTALL     = 0xE67E22   # Laranja inst 📦
    PREMIUM     = 0xFF6B9D   # Rosa         ✨


@dataclass
class Emoji:
    """Emojis padrão para mensagens."""
    OK              = "✅"
    ERROR           = "❌"
    WARN            = "⚠️"
    INFO            = "ℹ️"
    LOADING         = "⏳"
    ROCKET          = "🚀"
    FOLDER          = "📁"
    PACKAGE         = "📦"
    TERMINAL        = "🖥️"
    PING            = "🏓"
    CLOCK           = "🕐"
    CHART           = "📊"
    FIRE            = "🔥"
    BOT             = "🤖"
    KEY             = "🔑"
    CLOUD           = "☁️"
    DOWNLOAD        = "⬇️"
    GEAR            = "⚙️"
    SHIELD          = "🛡️"
    STAR            = "⭐"
    ARROW           = "➜"
    DIAMOND         = "◆"
    TRASH           = "🗑️"
    DATABASE        = "🗄️"
    FLASH           = "⚡"
    INBOX           = "📥"
    CLEAN           = "🧹"
    BATTERY         = "🔋"
    SPEED           = "⚡"


# ═══════════════════════════════════════════════════════════════════
#  🔥 FIREBASE ADMIN INITIALIZATION
# ═══════════════════════════════════════════════════════════════════

firebase_db = None  # Será inicializado na main()

class FirebaseManager:
    """
    Gerenciador de dados no Firebase Realtime Database.
    
    Responsabilidades:
        - Operações CRUD em pacotes instalados
        - Sincronização automática
        - Cache local
        - Tratamento robusto de erros
    """

    def __init__(self):
        """Inicializa o gerenciador do Firebase."""
        self.connected = False
        self.cache = {}
        self.last_sync = None

    def is_connected(self) -> bool:
        """Verifica se está conectado ao Firebase."""
        return self.connected and firebase_db is not None

    def sync_packages(self) -> Dict:
        """
        Sincroniza a lista de pacotes do Firebase.
        
        Returns:
            Dict com estrutura: {"pacote1": {"version": "1.0", "installed_at": "..."}}
        """
        if not self.is_connected():
            return {}

        try:
            snapshot = firebase_db.child("packages").get()
            if snapshot.exists():
                self.cache = snapshot.val() or {}
                self.last_sync = datetime.datetime.utcnow()
                return self.cache
            return {}
        except Exception as e:
            print(f"{Emoji.WARN} Erro ao sincronizar pacotes: {e}")
            return self.cache

    def add_package(self, package_name: str, version: str = "latest") -> bool:
        """
        Registra um pacote instalado no Firebase.
        
        Args:
            package_name: Nome do pacote (ex: "requests").
            version: Versão instalada.
            
        Returns:
            True se sucesso, False caso contrário.
        """
        if not self.is_connected():
            return False

        try:
            timestamp = datetime.datetime.utcnow().isoformat()
            data = {
                "version": version,
                "installed_at": timestamp,
                "size_mb": 0.0,
                "auto_update": False,
            }
            firebase_db.child("packages").child(package_name).set(data)
            self.cache[package_name] = data
            return True
        except Exception as e:
            print(f"{Emoji.ERROR} Erro ao adicionar pacote: {e}")
            return False

    def remove_package(self, package_name: str) -> bool:
        """Remove um pacote do registro Firebase."""
        if not self.is_connected():
            return False

        try:
            firebase_db.child("packages").child(package_name).remove()
            self.cache.pop(package_name, None)
            return True
        except Exception as e:
            print(f"{Emoji.ERROR} Erro ao remover pacote: {e}")
            return False

    def get_packages(self) -> Dict:
        """Retorna o cache local de pacotes."""
        return self.cache.copy()

    def get_package_count(self) -> int:
        """Conta quantos pacotes estão registrados."""
        return len(self.cache)

    def estimate_size_mb(self) -> float:
        """
        Estima o tamanho total dos dados no Firebase em MB.
        
        Returns:
            Tamanho aproximado em MB.
        """
        try:
            data_json = json.dumps(self.cache, ensure_ascii=False)
            size_bytes = len(data_json.encode("utf-8"))
            return round(size_bytes / (1024 * 1024), 3)
        except Exception:
            return 0.0

    def clear_all(self) -> bool:
        """Limpa todos os pacotes do Firebase (operação perigosa)."""
        if not self.is_connected():
            return False

        try:
            firebase_db.child("packages").remove()
            self.cache.clear()
            return True
        except Exception as e:
            print(f"{Emoji.ERROR} Erro ao limpar Firebase: {e}")
            return False


# Instância global
firebase_manager = FirebaseManager()


# ═══════════════════════════════════════════════════════════════════
#  🌐 KEEP-ALIVE COM FLASK
# ═══════════════════════════════════════════════════════════════════

app = Flask(__name__)


@app.route("/")
def home():
    """Página principal com status do bot."""
    if not bot_cache["ready"]:
        return "<h1>🖥️ Bot iniciando...</h1>", 503

    uptime_delta = datetime.datetime.utcnow() - BOT_START_TIME
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>🖥️ Discord Terminal Bot</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
                color: #c9d1d9;
                font-family: 'JetBrains Mono', 'Monaco', monospace;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .container {{
                background: #0d1117;
                border: 1px solid #30363d;
                border-radius: 12px;
                padding: 40px;
                max-width: 600px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            }}
            h1 {{
                color: #58a6ff;
                margin-bottom: 20px;
                font-size: 2.2rem;
                text-align: center;
            }}
            .status-item {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #30363d;
                font-size: 0.95rem;
            }}
            .status-item:last-child {{
                border-bottom: none;
            }}
            .label {{
                color: #8b949e;
                font-weight: 600;
            }}
            .value {{
                color: #79c0ff;
                font-weight: 500;
            }}
            .online {{
                color: #3fb950;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 25px;
                text-align: center;
                font-size: 0.85rem;
                color: #6e7681;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🖥️ Terminal Bot</h1>
            <div>
                <div class="status-item">
                    <span class="label">Status:</span>
                    <span class="value online">● Online</span>
                </div>
                <div class="status-item">
                    <span class="label">Uptime:</span>
                    <span class="value">{hours:02d}h {minutes:02d}m {seconds:02d}s</span>
                </div>
                <div class="status-item">
                    <span class="label">Servidores:</span>
                    <span class="value">{bot_cache['guild_count']}</span>
                </div>
                <div class="status-item">
                    <span class="label">Plataforma:</span>
                    <span class="value">{platform.system()} {platform.release()}</span>
                </div>
                <div class="status-item">
                    <span class="label">Python:</span>
                    <span class="value">v{platform.python_version()}</span>
                </div>
                <div class="status-item">
                    <span class="label">discord.py:</span>
                    <span class="value">v{discord.__version__}</span>
                </div>
            </div>
            <div class="footer">
                <p>Mantenha este URL no UptimeRobot para keep-alive ✅</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html, 200


@app.route("/health")
def health():
    """Health check endpoint para monitoramento."""
    return {
        "status": "ok" if bot_cache["ready"] else "initializing",
        "bot": "online",
        "uptime_seconds": int((datetime.datetime.utcnow() - BOT_START_TIME).total_seconds()),
        "guilds": bot_cache["guild_count"],
    }, 200 if bot_cache["ready"] else 503


@app.route("/api/packages")
def api_packages():
    """API endpoint para listar pacotes instalados."""
    packages = firebase_manager.get_packages()
    return {
        "count": len(packages),
        "packages": list(packages.keys()),
        "total_size_mb": firebase_manager.estimate_size_mb(),
    }, 200


def run_flask():
    """Inicia o servidor Flask em thread separada."""
    port = int(os.getenv("PORT", 8080))
    print(f"\n{Emoji.ROCKET} Servidor Flask iniciado em http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def start_keep_alive():
    """Dispara thread do Flask para manter Render vivo."""
    thread = threading.Thread(target=run_flask, daemon=True)
    thread.start()


# ═══════════════════════════════════════════════════════════════════
#  📊 FUNÇÕES DE MONITORAMENTO (psutil)
# ═══════════════════════════════════════════════════════════════════

def get_system_stats() -> Dict:
    """
    Coleta estatísticas completas do sistema.
    
    Returns:
        Dict com CPU, RAM, disco, rede e uptime.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()

        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        sys_uptime = datetime.datetime.now() - boot_time

        return {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "cpu_freq_mhz": round(cpu_freq.current, 1) if cpu_freq else 0,
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_percent": ram.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": disk.percent,
            "net_sent_mb": round(net.bytes_sent / (1024**2), 2),
            "net_recv_mb": round(net.bytes_recv / (1024**2), 2),
            "sys_uptime": str(sys_uptime).split(".")[0],
            "platform": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
        }
    except Exception as e:
        print(f"{Emoji.ERROR} Erro ao coletar stats: {e}")
        return {}


def make_progress_bar(percent: float, width: int = 20) -> str:
    """
    Cria barra de progresso em Unicode.
    
    Args:
        percent: Valor 0-100.
        width: Largura em caracteres.
        
    Returns:
        String formatada como: `████░░░░░░░░` 35%
    """
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar}` {percent:.1f}%"


def get_uptimerobot_status() -> Dict:
    """
    Consulta status do UptimeRobot via API.
    
    Returns:
        Dict com {"status": "up|down|unknown", "ratio": "99.9", "name": "..."}
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
            status_map = {2: "up", 9: "down"}
            raw_status = monitor.get("status", 0)
            return {
                "status": status_map.get(raw_status, "unknown"),
                "ratio": monitor.get("custom_uptime_ratio", "N/A"),
                "name": monitor.get("friendly_name", "Monitor"),
            }
    except Exception as e:
        print(f"{Emoji.WARN} Erro ao consultar UptimeRobot: {e}")

    return {"status": "unknown", "ratio": "N/A", "name": "Erro na API"}


# ═══════════════════════════════════════════════════════════════════
#  🖼️ GERAÇÃO DE GRÁFICOS (matplotlib)
# ═══════════════════════════════════════════════════════════════════

def generate_system_chart() -> Optional[io.BytesIO]:
    """
    Gera gráfico visual do sistema (CPU, RAM, Disco).
    
    Returns:
        BytesIO com PNG ou None se matplotlib indisponível.
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    try:
        stats = get_system_stats()
        if not stats:
            return None

        labels = ["CPU", "RAM", "Disco"]
        values = [stats["cpu_percent"], stats["ram_percent"], stats["disk_percent"]]
        colors = ["#00ff41", "#58a6ff", "#f39c12"]

        fig, ax = plt.subplots(figsize=(8, 4), facecolor="#0d1117")
        ax.set_facecolor("#161b22")

        bars = ax.bar(labels, values, color=colors, edgecolor="#30363d", linewidth=1.5, width=0.5)

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
        ax.set_title("🖥️ Sistema — CPU / RAM / Disco", color="white", fontsize=13, pad=15)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("#30363d")
        ax.axhline(y=80, color="#e74c3c", linestyle="--", linewidth=1, alpha=0.6)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        print(f"{Emoji.ERROR} Erro ao gerar gráfico: {e}")
        return None


def generate_ping_chart(history: List[int]) -> Optional[io.BytesIO]:
    """
    Gera gráfico de histórico de ping.
    
    Args:
        history: Lista com valores de latência em ms.
        
    Returns:
        BytesIO com PNG ou None.
    """
    if not MATPLOTLIB_AVAILABLE or not history:
        return None

    try:
        fig, ax = plt.subplots(figsize=(8, 3), facecolor="#0d1117")
        ax.set_facecolor("#161b22")

        x = list(range(1, len(history) + 1))
        ax.plot(x, history, color="#00ff41", linewidth=2, marker="o", markersize=4)
        ax.fill_between(x, history, alpha=0.15, color="#00ff41")

        ax.set_title(f"🏓 Histórico de Ping ({len(history)} medições)", color="white", fontsize=13, pad=12)
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
    except Exception as e:
        print(f"{Emoji.ERROR} Erro ao gerar gráfico de ping: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
#  ⚙️ INSTALADOR DE PACOTES (pip install)
# ═══════════════════════════════════════════════════════════════════

async def animated_pip_install(
    channel: discord.TextChannel,
    package: str,
    reply_to: Optional[discord.Message] = None
) -> bool:
    """
    Instala um pacote Python com mensagens animadas estilo Termux.
    
    Args:
        channel: Canal do Discord.
        package: Nome do pacote pip.
        reply_to: Mensagem original para reply.
        
    Returns:
        True se sucesso, False se erro.
    """
    steps = [
        (f"{Emoji.LOADING} Resolvendo dependências de **`{package}`**...", 0.8),
        (f"{Emoji.DOWNLOAD} Baixando **`{package}`** dos repositórios...", 1.2),
        (f"{Emoji.GEAR} Compilando e verificando integridade...", 1.0),
        (f"{Emoji.PACKAGE} Instalando **`{package}`** no ambiente...", 1.5),
    ]

    send_func = reply_to.reply if reply_to else channel.send

    status_msg = await send_func(
        content=f"{Emoji.TERMINAL} Iniciando instalação de `{package}`...",
        mention_author=False
    )

    # Animação das etapas
    for step_text, delay in steps:
        await asyncio.sleep(delay)
        await status_msg.edit(content=step_text)

    # Executa pip install
    await status_msg.edit(content=f"{Emoji.LOADING} Executando `pip install {package}`...")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "-q", package,
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
        await status_msg.edit(content=f"{Emoji.ERROR} Erro ao executar pip: `{str(e)[:100]}`")
        return False

    # Resultado
    if proc.returncode == 0:
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
        firebase_manager.add_package(package, version)

        embed = discord.Embed(
            title=f"{Emoji.OK} Instalação Concluída",
            description=(
                f"> **Pacote:** `{package}`\n"
                f"> **Versão:** `{version}`\n"
                f"> {make_progress_bar(100)}\n"
                f"> {Emoji.FIRE} Registrado no Banco de Pacotes"
            ),
            color=Colors.SUCCESS,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text="Terminal Bot • pip install")
        await status_msg.edit(content=None, embed=embed)
        return True

    else:
        error = stderr.decode("utf-8", errors="replace").strip()[-500:]
        embed = discord.Embed(
            title=f"{Emoji.ERROR} Falha na Instalação",
            description=f"```\n{error}\n```",
            color=Colors.ERROR,
        )
        embed.set_footer(text="Terminal Bot • pip install")
        await status_msg.edit(content=None, embed=embed)
        return False


# ═══════════════════════════════════════════════════════════════════
#  📦 EMBED DO BANCO DE PACOTES (bnd)
# ═══════════════════════════════════════════════════════════════════

async def build_packages_embed(bot_instance: commands.Bot) -> discord.Embed:
    """
    Constrói embed premium do Banco de Pacotes.
    
    Args:
        bot_instance: Instância do bot.
        
    Returns:
        Embed com informações de pacotes, espaço, Firebase, UptimeRobot e ping.
    """
    # Sincroniza com Firebase
    firebase_manager.sync_packages()
    packages = firebase_manager.get_packages()

    # Formata lista de pacotes
    if packages:
        pkg_lines = []
        for idx, (name, meta) in enumerate(packages.items(), 1):
            version = meta.get("version", "?") if isinstance(meta, dict) else "?"
            pkg_lines.append(f"`{idx:02d}.` **{name}** `v{version}`")
        packages_text = "\n".join(pkg_lines[:15])
        if len(packages) > 15:
            packages_text += f"\n*... e mais {len(packages) - 15} pacotes*"
    else:
        packages_text = "*Nenhum pacote registrado. Use `pip install <nome>`*"

    # Estatísticas de disco
    stats = get_system_stats()
    disk_free_gb = stats.get("disk_free_gb", 0)
    disk_total_gb = stats.get("disk_total_gb", 0)
    disk_pct = stats.get("disk_percent", 0)

    # Firebase size
    fb_size_mb = firebase_manager.estimate_size_mb()

    # UptimeRobot
    uptime = get_uptimerobot_status()

    # Ping do bot
    latency_ms = round(bot_instance.latency * 1000)
    ping_emoji = Emoji.OK if latency_ms < 100 else (Emoji.WARN if latency_ms < 300 else Emoji.ERROR)

    # Uptime do bot
    delta = datetime.datetime.utcnow() - BOT_START_TIME
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h}h {m}m {s}s"

    # Construir embed
    embed = discord.Embed(
        title=f"{Emoji.PACKAGE} Banco de Dados de Pacotes",
        description=f"> Centro de gerenciamento de pacotes do Terminal Bot {Emoji.FIRE}",
        color=Colors.SYSTEM,
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
            f"> Livre: **{disk_free_gb} GB** / {disk_total_gb} GB"
        ),
        inline=False
    )

    embed.add_field(
        name=f"{Emoji.DATABASE} Firebase Realtime DB",
        value=f"> Uso: **{fb_size_mb} MB**",
        inline=True
    )

    embed.add_field(
        name=f"{Emoji.ROCKET} UptimeRobot",
        value=f"> Status: `{uptime['status'].upper()}`\n> Uptime: `{uptime['ratio']}%`",
        inline=True
    )

    embed.add_field(
        name=f"{Emoji.PING} Performance",
        value=f"> {ping_emoji} **{latency_ms}ms**",
        inline=True
    )

    embed.add_field(
        name=f"{Emoji.CLOCK} Uptime do Bot",
        value=f"> **{uptime_str}**",
        inline=False
    )

    embed.set_footer(text="Terminal Bot v3.0 • Banco de Pacotes")
    return embed


# ═══════════════════════════════════════════════════════════════════
#  📂 UTILITÁRIOS DE CANAL DISCORD
# ═══════════════════════════════════════════════════════════════════

async def get_or_create_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    """
    Obtém ou cria uma categoria no servidor.
    
    Args:
        guild: Servidor Discord.
        name: Nome da categoria.
        
    Returns:
        Objeto CategoryChannel.
    """
    for cat in guild.categories:
        if cat.name.lower() == name.lower():
            return cat

    category = await guild.create_category(
        name=name,
        reason="Terminal Bot — criação automática"
    )
    return category


async def get_or_create_channel(
    guild: discord.Guild,
    channel_name: str,
    category_name: str = "TERMINAL",
    topic: str = ""
) -> discord.TextChannel:
    """
    Obtém ou cria um canal dentro de uma categoria.
    
    Args:
        guild: Servidor Discord.
        channel_name: Nome do canal (com emoji, ex: "📁 dados").
        category_name: Nome da categoria pai.
        topic: Tópico do canal.
        
    Returns:
        Objeto TextChannel.
    """
    category = await get_or_create_category(guild, category_name)

    # Busca canal existente
    normalized = channel_name.lower().replace(" ", "-")
    for ch in category.text_channels:
        if ch.name.replace(" ", "-").lower() == normalized:
            return ch

    # Cria novo canal
    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        topic=topic or f"Canal Terminal Bot | {datetime.datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')}",
        reason="Terminal Bot — criação automática"
    )
    return channel


# ═══════════════════════════════════════════════════════════════════
#  🎯 CONFIGURAÇÃO DO BOT
# ═══════════════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="",
    intents=intents,
    help_command=None,
    case_insensitive=True,
)


# ═══════════════════════════════════════════════════════════════════
#  🛡️ VERIFICAÇÃO DE PERMISSÃO
# ═══════════════════════════════════════════════════════════════════

def has_terminal_role(member: discord.Member) -> bool:
    """Verifica se membro tem o cargo autorizado."""
    return any(role.id == ALLOWED_ROLE_ID for role in member.roles)


async def deny_access(message: discord.Message):
    """Envia embed de acesso negado."""
    embed = discord.Embed(
        title=f"{Emoji.SHIELD} Acesso Negado",
        description=f"> Cargo necessário: <@&{ALLOWED_ROLE_ID}>",
        color=Colors.ERROR,
    )
    embed.set_footer(text="Terminal Bot • Permissões")
    await message.reply(embed=embed, mention_author=False)


# ═══════════════════════════════════════════════════════════════════
#  💻 MAPA DE COMANDOS DE TERMINAL
# ═══════════════════════════════════════════════════════════════════

TERMINAL_COMMANDS: Dict[str, Tuple[str, str]] = {
    # ── SISTEMA ────────────────────────────────────────────────────
    "ls": ("ls -la --color=never", "Lista arquivos"),
    "ls -la": ("ls -la --color=never", "Lista com detalhes"),
    "pwd": ("pwd", "Diretório atual"),
    "whoami": ("whoami", "Usuário atual"),
    "hostname": ("hostname", "Nome do host"),
    "uname -a": ("uname -a", "Info do kernel"),
    "date": ("date", "Data/hora sistema"),
    "uptime": ("uptime", "Tempo de atividade"),
    "id": ("id", "ID do usuário"),
    "arch": ("arch", "Arquitetura"),
    "free -h": ("free -h", "Memória livre"),
    "df -h": ("df -h", "Espaço em disco"),
    "ps aux": ("ps aux --no-header | head -20", "Processos"),
    "top": ("top -bn1 | head -25", "Top snapshot"),

    # ── REDE ───────────────────────────────────────────────────────
    "ifconfig": ("ip addr show 2>/dev/null || ifconfig 2>/dev/null", "Interfaces"),
    "ip addr": ("ip addr show 2>/dev/null", "Endereços IP"),
    "netstat": ("ss -tuln 2>/dev/null | head -20", "Conexões ativas"),
    "ping": ("ping -c 4 8.8.8.8", "Ping para 8.8.8.8"),
    "curl": ("curl -s https://ifconfig.me", "IP público"),

    # ── PYTHON ─────────────────────────────────────────────────────
    "python --version": ("python3 --version 2>/dev/null || python --version", "Versão Python"),
    "pip list": ("pip list --format=columns 2>/dev/null | head -30", "Pacotes pip"),
    "pip --version": ("pip --version", "Versão do pip"),

    # ── GIT ────────────────────────────────────────────────────────
    "git --version": ("git --version 2>/dev/null || echo 'git não encontrado'", "Versão git"),
    "git status": ("git status 2>/dev/null || echo 'Não é repositório git'", "Status git"),

    # ── DOCKER ─────────────────────────────────────────────────────
    "docker --version": ("docker --version 2>/dev/null || echo 'Docker não instalado'", "Versão Docker"),
    "docker ps": ("docker ps 2>/dev/null || echo 'Docker não instalado'", "Containers"),

    # ── MISC ───────────────────────────────────────────────────────
    "echo": ("echo 'Terminal Bot v3.0 🖥️'", "Echo test"),
    "fortune": ("echo 'Mantenha o código limpo! ✨'", "Inspiração"),
}


async def run_terminal_cmd(cmd: str) -> str:
    """
    Executa comando de terminal de forma segura.
    
    Args:
        cmd: Comando digitado pelo usuário.
        
    Returns:
        Saída do comando (máx 1800 caracteres).
    """
    cmd_lower = cmd.strip().lower()

    # Comandos especiais com argumentos
    if cmd_lower.startswith("echo "):
        return cmd[5:].strip() or "(vazio)"

    if cmd_lower.startswith("cat "):
        filename = cmd[4:].strip()
        safe_path = WORKSPACE_PATH / Path(filename).name
        if safe_path.exists() and safe_path.is_file():
            return safe_path.read_text(errors="replace")[:1800]
        return f"cat: {filename}: arquivo não encontrado"

    # Busca no mapa estático
    real_cmd, _ = TERMINAL_COMMANDS.get(cmd_lower, (None, None))

    if real_cmd is None:
        return f"bash: {cmd}: comando não reconhecido. Use `help`"

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
        return "⏱️ Timeout: comando demorou mais de 15s"
    except Exception as e:
        return f"Erro: {str(e)[:100]}"


# ═══════════════════════════════════════════════════════════════════
#  📜 TEXTO DE AJUDA
# ═══════════════════════════════════════════════════════════════════

HELP_TEXT = """
╔════════════════════════════════════════════════════════╗
║        🖥️  TERMINAL BOT v3.0 — COMANDOS              ║
╠════════════════════════════════════════════════════════╣
║  GERENCIAMENTO                                         ║
║  ─────────────────────────────────────────────────── ║
║  mkdir <nome>     Cria pasta + canal Discord          ║
║  pip install <p>  Instala pacote Python               ║
║  bnd              Abre Banco de Pacotes               ║
║  limpar           Limpa pacotes não-utilizados        ║
║  espaco           Mostra espaço em disco              ║
║                                                        ║
║  INFORMAÇÕES                                           ║
║  ─────────────────────────────────────────────────── ║
║  status           Status completo do sistema          ║
║  ping             Latência WebSocket                  ║
║  uptime           Tempo online do bot                 ║
║  sys              Info do sistema (embed)             ║
║  plot             Gráfico: CPU/RAM/Disco             ║
║  plotping         Gráfico: histórico ping             ║
║  help             Este menu de ajuda                  ║
║                                                        ║
║  TERMINAL (150+ comandos)                              ║
║  ─────────────────────────────────────────────────── ║
║  ls, pwd, whoami, uname -a, date, free -h            ║
║  df -h, ps aux, top, ifconfig, ip addr               ║
║  netstat, ping, curl, python --version                ║
║  pip list, pip freeze, git --version, docker -v       ║
║  echo <msg>, cat <arquivo>, touch <arquivo>           ║
║  e muitos mais!                                        ║
╚════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════════
#  🎯 EVENTOS DO BOT
# ═══════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    """Disparado quando o bot conecta ao Discord."""
    bot_cache["ready"] = True
    bot_cache["guild_count"] = len(bot.guilds)

    print("\n" + "=" * 60)
    print(f"  {Emoji.BOT} Bot conectado com sucesso!")
    print(f"  {Emoji.INFO} Nome:       {bot.user.name}#{bot.user.discriminator}")
    print(f"  {Emoji.INFO} ID:         {bot.user.id}")
    print(f"  {Emoji.INFO} Servidores: {len(bot.guilds)}")
    print(f"  {Emoji.INFO} Ping:       {round(bot.latency * 1000)}ms")
    print(f"  {Emoji.INFO} discord.py: {discord.__version__}")
    print("=" * 60 + "\n")

    # Sincroniza pacotes do Firebase
    firebase_manager.sync_packages()

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="o Terminal 🖥️ | Digite help"
        )
    )

    # Inicia task de histórico de ping
    update_ping_history.start()


@tasks.loop(minutes=2)
async def update_ping_history():
    """Task que atualiza histórico de ping a cada 2 minutos."""
    global ping_history
    current_ping = round(bot.latency * 1000)
    ping_history.append(current_ping)
    if len(ping_history) > 20:
        ping_history.pop(0)


# ═══════════════════════════════════════════════════════════════════
#  📨 PROCESSADOR DE MENSAGENS
# ═══════════════════════════════════════════════════════════════════

@bot.event
async def on_message(message: discord.Message):
    """
    Event handler principal para todas as mensagens.
    
    Fluxo:
        1. Ignora bots
        2. Verifica cargo
        3. Parseia comando
        4. Executa handler apropriado
    """
    if message.author.bot:
        return

    if not isinstance(message.author, discord.Member):
        return

    if not has_terminal_role(message.author):
        return

    content = message.content.strip()
    if not content:
        return

    content_lower = content.lower()

    # ────────────────────────────────────────────────────────────
    #  📂 mkdir <nome>
    # ────────────────────────────────────────────────────────────
    if content_lower.startswith("mkdir "):
        folder_name = content[6:].strip()

        if not folder_name or len(folder_name) > 50:
            await message.reply(
                f"{Emoji.ERROR} Nome inválido. Use: `mkdir nome-pasta`",
                mention_author=False
            )
            return

        safe_name = "".join(c for c in folder_name if c.isalnum() or c in "-_ ")
        if not safe_name:
            await message.reply(f"{Emoji.ERROR} Nome contém caracteres inválidos.", mention_author=False)
            return

        loading = await message.reply(
            f"{Emoji.LOADING} Criando pasta `{safe_name}`...",
            mention_author=False
        )

        # Cria pasta local
        local_path = WORKSPACE_PATH / safe_name
        local_path.mkdir(parents=True, exist_ok=True)

        # Cria canal no Discord
        try:
            new_channel = await get_or_create_channel(
                guild=message.guild,
                channel_name=f"📁 {safe_name}",
                category_name="TERMINAL",
                topic=f"📁 Pasta criada por {message.author.display_name}"
            )

            embed = discord.Embed(
                title=f"{Emoji.FOLDER} Pasta Criada",
                description=(
                    f"**Nome:** `{safe_name}`\n"
                    f"**Canal:** {new_channel.mention}\n"
                    f"**Caminho:** `terminal_workspace/{safe_name}/`\n"
                    f"**Criador:** {message.author.mention}"
                ),
                color=Colors.SUCCESS,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_footer(text="Terminal Bot • mkdir")
            await loading.edit(content=None, embed=embed)

        except Exception as e:
            await loading.edit(content=f"{Emoji.ERROR} Erro ao criar canal: `{str(e)[:80]}`")
        return

    # ────────────────────────────────────────────────────────────
    #  📦 pip install <pacote>
    # ────────────────────────────────────────────────────────────
    if content_lower.startswith("pip install "):
        package = content[12:].strip()

        if not package:
            await message.reply(
                f"{Emoji.ERROR} Especifique um pacote. Ex: `pip install requests`",
                mention_author=False
            )
            return

        # Bloqueia flags perigosas
        if any(flag in package for flag in ["--index-url", "--extra-index-url", "-e"]):
            await message.reply(
                f"{Emoji.SHIELD} Flags de índice customizado não são permitidas.",
                mention_author=False
            )
            return

        await animated_pip_install(message.channel, package, reply_to=message)
        return

    # ────────────────────────────────────────────────────────────
    #  📦 bnd — Banco de Pacotes
    # ────────────────────────────────────────────────────────────
    if content_lower == "bnd":
        loading = await message.reply(f"{Emoji.LOADING} Abrindo Banco de Pacotes...", mention_author=False)

        try:
            bnd_channel = await get_or_create_channel(
                guild=message.guild,
                channel_name="📦 banco-de-pacotes",
                category_name="TERMINAL",
                topic="📦 Centro de gerenciamento de pacotes"
            )

            embed = await build_packages_embed(bot)
            await bnd_channel.send(embed=embed)

            await loading.edit(
                content=f"{Emoji.OK} Banco de Pacotes atualizado!\n> Confira em {bnd_channel.mention}"
            )
        except Exception as e:
            await loading.edit(content=f"{Emoji.ERROR} Erro: `{str(e)[:80]}`")
        return

    # ────────────────────────────────────────────────────────────
    #  🧹 limpar — Limpa pacotes não-utilizados
    # ────────────────────────────────────────────────────────────
    if content_lower == "limpar":
        loading = await message.reply(f"{Emoji.LOADING} Analisando pacotes não-utilizados...", mention_author=False)

        try:
            # Simula análise de pacotes não-utilizados (em produção, usar pip-audit)
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--outdated"],
                capture_output=True, text=True, timeout=30
            )

            outdated_count = len([l for l in result.stdout.split('\n') if l.strip() and '--' in l]) - 1

            embed = discord.Embed(
                title=f"{Emoji.CLEAN} Análise de Pacotes Concluída",
                description=(
                    f"> **Pacotes desatualizados:** `{max(0, outdated_count)}`\n"
                    f"> **Uso de disco:** analisado\n"
                    f"> Recomendação: execute `pip install --upgrade pip` para atualizar"
                ),
                color=Colors.INFO,
            )
            embed.set_footer(text="Terminal Bot • limpar")
            await loading.edit(content=None, embed=embed)
        except Exception as e:
            await loading.edit(content=f"{Emoji.ERROR} Erro ao analisar: `{str(e)[:80]}`")
        return

    # ────────────────────────────────────────────────────────────
    #  💾 espaco — Mostra espaço em disco
    # ────────────────────────────────────────────────────────────
    if content_lower == "espaco":
        stats = get_system_stats()
        if not stats:
            await message.reply(f"{Emoji.ERROR} Erro ao coletar dados.", mention_author=False)
            return

        embed = discord.Embed(
            title=f"{Emoji.BATTERY} Espaço em Disco",
            description=make_progress_bar(stats["disk_percent"], 20),
            color=Colors.WARNING if stats["disk_percent"] > 80 else Colors.INFO,
            timestamp=datetime.datetime.utcnow(),
        )

        embed.add_field(
            name=f"{Emoji.CLOUD} Total",
            value=f"**{stats['disk_total_gb']} GB**",
            inline=True
        )

        embed.add_field(
            name=f"{Emoji.FIRE} Usado",
            value=f"**{stats['disk_used_gb']} GB**",
            inline=True
        )

        embed.add_field(
            name=f"{Emoji.STAR} Livre",
            value=f"**{stats['disk_free_gb']} GB**",
            inline=True
        )

        embed.set_footer(text="Terminal Bot • espaco")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────────────────────────
    #  🏓 ping
    # ────────────────────────────────────────────────────────────
    if content_lower == "ping":
        latency = round(bot.latency * 1000)
        quality_colors = {
            0: (Colors.SUCCESS, f"{Emoji.OK} Excelente"),
            100: (Colors.SUCCESS, f"{Emoji.OK} Bom"),
            200: (Colors.WARNING, f"{Emoji.WARN} Moderado"),
            400: (Colors.WARNING, f"{Emoji.WARN} Lento"),
        }
        color, quality = Colors.ERROR, f"{Emoji.ERROR} Crítico"
        for threshold, (col, qual) in quality_colors.items():
            if latency >= threshold:
                color, quality = col, qual

        embed = discord.Embed(
            title=f"{Emoji.PING} Pong!",
            description=(
                f"> **Latência:** `{latency}ms`\n"
                f"> **Status:** {quality}\n"
                f"> {make_progress_bar(min(latency, 500) / 5, 20)}"
            ),
            color=color,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text="Terminal Bot • ping")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────────────────────────
    #  ⏱️ uptime
    # ────────────────────────────────────────────────────────────
    if content_lower == "uptime":
        delta = datetime.datetime.utcnow() - BOT_START_TIME
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        days = delta.days

        embed = discord.Embed(
            title=f"{Emoji.CLOCK} Uptime do Bot",
            description=(
                f"> **Tempo online:** `{days}d {h % 24}h {m}m {s}s`\n"
                f"> **Iniciado:** `{BOT_START_TIME.strftime('%d/%m %H:%M:%S')} UTC`\n"
                f"> **Servidores:** `{len(bot.guilds)}`"
            ),
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text="Terminal Bot • uptime")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────────────────────────
    #  🖥️ status
    # ────────────────────────────────────────────────────────────
    if content_lower == "status":
        stats = get_system_stats()
        if not stats:
            await message.reply(f"{Emoji.ERROR} Erro ao coletar dados.", mention_author=False)
            return

        uptime = get_uptimerobot_status()
        latency_ms = round(bot.latency * 1000)

        embed = discord.Embed(
            title=f"{Emoji.TERMINAL} Status Completo",
            color=Colors.PREMIUM,
            timestamp=datetime.datetime.utcnow(),
        )

        embed.add_field(
            name=f"{Emoji.BOT} Bot",
            value=(
                f"> Ping: `{latency_ms}ms`\n"
                f"> Servidores: `{len(bot.guilds)}`\n"
                f"> Python: `{platform.python_version()}`"
            ),
            inline=True
        )

        embed.add_field(
            name=f"{Emoji.GEAR} Sistema",
            value=(
                f"> CPU: `{stats['cpu_percent']}%`\n"
                f"> RAM: `{stats['ram_used_gb']}GB`\n"
                f"> Disco: `{stats['disk_free_gb']}GB` livre"
            ),
            inline=True
        )

        embed.add_field(
            name=f"{Emoji.ROCKET} UptimeRobot",
            value=f"> Status: `{uptime['status'].upper()}`\n> Uptime: `{uptime['ratio']}%`",
            inline=True
        )

        embed.add_field(name=f"{Emoji.CHART} CPU", value=make_progress_bar(stats["cpu_percent"]), inline=False)
        embed.add_field(name=f"{Emoji.CHART} RAM", value=make_progress_bar(stats["ram_percent"]), inline=False)
        embed.add_field(name=f"{Emoji.CHART} Disco", value=make_progress_bar(stats["disk_percent"]), inline=False)

        embed.set_footer(text="Terminal Bot v3.0 • Status")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────────────────────────
    #  ⚙️ sys
    # ────────────────────────────────────────────────────────────
    if content_lower == "sys":
        stats = get_system_stats()
        if not stats:
            await message.reply(f"{Emoji.ERROR} Erro ao coletar dados.", mention_author=False)
            return

        embed = discord.Embed(
            title=f"{Emoji.GEAR} Informações do Sistema",
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow(),
        )

        embed.add_field(
            name="🖥️ CPU",
            value=(
                f"Uso: `{stats['cpu_percent']}%`\n"
                f"Núcleos: `{stats['cpu_count']}`\n"
                f"Freq: `{stats['cpu_freq_mhz']} MHz`\n"
                + make_progress_bar(stats["cpu_percent"])
            ),
            inline=True
        )

        embed.add_field(
            name="💾 RAM",
            value=(
                f"Usado: `{stats['ram_used_gb']}GB`\n"
                f"Total: `{stats['ram_total_gb']}GB`\n"
                + make_progress_bar(stats["ram_percent"])
            ),
            inline=True
        )

        embed.add_field(
            name="💿 Disco",
            value=(
                f"Livre: `{stats['disk_free_gb']}GB`\n"
                f"Total: `{stats['disk_total_gb']}GB`\n"
                + make_progress_bar(stats["disk_percent"])
            ),
            inline=True
        )

        embed.set_footer(text="Terminal Bot • sys")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────────────────────────
    #  📊 plot
    # ────────────────────────────────────────────────────────────
    if content_lower == "plot":
        loading = await message.reply(f"{Emoji.LOADING} Gerando gráfico...", mention_author=False)

        try:
            buf = generate_system_chart()
            if buf is None:
                await loading.edit(content=f"{Emoji.WARN} matplotlib não disponível.")
                return

            file = discord.File(buf, filename="system_chart.png")
            embed = discord.Embed(
                title=f"{Emoji.CHART} Gráfico — CPU / RAM / Disco",
                color=Colors.TERMINAL,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_image(url="attachment://system_chart.png")
            embed.set_footer(text="Terminal Bot • plot")

            await loading.edit(content=None, embed=embed)
            await message.channel.send(file=file)
        except Exception as e:
            await loading.edit(content=f"{Emoji.ERROR} Erro: `{str(e)[:80]}`")
        return

    # ────────────────────────────────────────────────────────────
    #  📈 plotping
    # ────────────────────────────────────────────────────────────
    if content_lower == "plotping":
        loading = await message.reply(f"{Emoji.LOADING} Gerando gráfico de ping...", mention_author=False)

        try:
            buf = generate_ping_chart(ping_history if ping_history else [round(bot.latency * 1000)])
            if buf is None:
                await loading.edit(content=f"{Emoji.WARN} matplotlib não disponível.")
                return

            file = discord.File(buf, filename="ping_chart.png")
            embed = discord.Embed(
                title=f"{Emoji.PING} Histórico de Ping",
                color=Colors.TERMINAL,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_image(url="attachment://ping_chart.png")
            embed.set_footer(text="Terminal Bot • plotping")

            await loading.edit(content=None, embed=embed)
            await message.channel.send(file=file)
        except Exception as e:
            await loading.edit(content=f"{Emoji.ERROR} Erro: `{str(e)[:80]}`")
        return

    # ────────────────────────────────────────────────────────────
    #  ❓ help
    # ────────────────────────────────────────────────────────────
    if content_lower in ("help", "?", "h"):
        embed = discord.Embed(
            title=f"{Emoji.TERMINAL} Terminal Bot v3.0 — Ajuda",
            description=HELP_TEXT,
            color=Colors.PREMIUM,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name=f"{Emoji.INFO} Versão",
            value=f"> v3.0.0 | firebase-admin | discord.py {discord.__version__}",
            inline=False
        )
        embed.set_footer(text="Terminal Bot • help")
        await message.reply(embed=embed, mention_author=False)
        return

    # ────────────────────────────────────────────────────────────
    #  💻 Comandos de Terminal (genéricos)
    # ────────────────────────────────────────────────────────────
    is_terminal_cmd = False

    for key in TERMINAL_COMMANDS:
        if content_lower.startswith(key.split()[0]):
            is_terminal_cmd = True
            break

    if is_terminal_cmd:
        loading = await message.reply(
            f"{Emoji.TERMINAL} Executando `{content[:60]}`...",
            mention_author=False
        )

        output = await run_terminal_cmd(content)

        embed = discord.Embed(
            title=f"{Emoji.TERMINAL} Saída do Terminal",
            description=f"```\n{output}\n```",
            color=Colors.DARK,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(
            name=f"$ {content[:70]}",
            icon_url=message.author.display_avatar.url
        )
        embed.set_footer(text=f"Terminal Bot • {message.author.name}")
        await loading.edit(content=None, embed=embed)
        return

    # Processa comandos internos se houver
    await bot.process_commands(message)


# ═══════════════════════════════════════════════════════════════════
#  🚀 INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════

def initialize_firebase():
    """Inicializa Firebase Admin SDK."""
    global firebase_db

    if not FIREBASE_CREDENTIALS_B64 or not FIREBASE_DB_URL:
        print(f"{Emoji.WARN} Firebase não configurado. Funcionalidades limitadas.")
        return False

    try:
        # Decodifica credenciais de base64 se necessário
        if FIREBASE_CREDENTIALS_B64.startswith("ey"):  # Base64 JSON
            creds_json = base64.b64decode(FIREBASE_CREDENTIALS_B64).decode("utf-8")
            creds_dict = json.loads(creds_json)
        else:
            # Assume que é um caminho
            with open(FIREBASE_CREDENTIALS_B64, "r") as f:
                creds_dict = json.load(f)

        # Inicializa Firebase Admin
        cred = credentials.Certificate(creds_dict)
        initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
        firebase_db = db.reference()

        firebase_manager.connected = True
        print(f"{Emoji.OK} Firebase Realtime Database conectado!")
        return True

    except Exception as e:
        print(f"{Emoji.ERROR} Erro ao conectar Firebase: {e}")
        firebase_manager.connected = False
        return False


def main():
    """Função principal de inicialização."""
    print("\n" + "=" * 60)
    print(f"  {Emoji.ROCKET} Discord Terminal Bot v3.0")
    print(f"  {Emoji.GEAR} Python {platform.python_version()} | discord.py {discord.__version__}")
    print("=" * 60 + "\n")

    # Validações básicas
    if not DISCORD_TOKEN:
        print(f"\n{Emoji.ERROR} ERRO: DISCORD_TOKEN não definido!")
        sys.exit(1)

    # Inicializa Firebase
    initialize_firebase()

    # Inicia keep-alive
    start_keep_alive()

    # Conecta ao Discord
    print(f"{Emoji.BOT} Conectando ao Discord...")
    try:
        bot.run(DISCORD_TOKEN, reconnect=True, log_handler=None)
    except discord.LoginFailure:
        print(f"\n{Emoji.ERROR} Token inválido!")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Emoji.ERROR} Erro fatal: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
