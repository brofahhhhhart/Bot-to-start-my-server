"""
╔══════════════════════════════════════════════════════════════════════════╗
║   Minecraft Bedrock — Render.com Free Tier                              ║
║   PocketMine-MP + Playit.gg + Backup automático via GitHub              ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Variáveis de ambiente necessárias (Render > Environment):              ║
║                                                                          ║
║  Obrigatórias:                                                           ║
║    GH_TOKEN        Personal Access Token do GitHub (repo scope)          ║
║    GH_REPO         Ex: "seu-usuario/mc-world-backup"                    ║
║                                                                          ║
║  Opcionais (têm valor padrão):                                           ║
║    SECRET_KEY      Chave do agente Playit (obtida após 1º claim)        ║
║    BACKUP_INTERVAL Minutos entre backups automáticos (padrão: 20)       ║
║    GIT_USER_NAME   Autor do commit (padrão: "MC Backup Bot")            ║
║    GIT_USER_EMAIL  Email do commit  (padrão: "bot@render.mc")           ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import stat
import signal
import shutil
import tarfile
import threading
import subprocess
import logging
import time
import textwrap
import requests
from flask import Flask

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("mc-render")

# ── Constantes e caminhos ─────────────────────────────────────────────────────
BASE_DIR         = os.getcwd()
BIN_DIR          = os.path.join(BASE_DIR, "bin")        # PHP binary
PMMP_DIR         = os.path.join(BASE_DIR, "pmmp")       # servidor PMMP
PMMP_WORLDS_DIR  = os.path.join(PMMP_DIR, "worlds")
PHAR_PATH        = os.path.join(PMMP_DIR, "PocketMine-MP.phar")
PLAYIT_BIN       = os.path.join(BASE_DIR, "playit")
BACKUP_REPO_DIR  = os.path.join(BASE_DIR, "world-backup") # clone do repo GitHub

PHAR_URL         = "https://github.com/pmmp/PocketMine-MP/releases/latest/download/PocketMine-MP.phar"
GITHUB_API       = "https://api.github.com/repos/{}/releases/latest"
PLAYIT_REPO      = "playit-cloud/playit-agent"
PHP_REPO         = "pmmp/PHP-Binaries"

# Variáveis de ambiente
GH_TOKEN         = os.environ.get("GH_TOKEN", "")
GH_REPO          = os.environ.get("GH_REPO", "")
SECRET_KEY       = os.environ.get("SECRET_KEY", "")
BACKUP_INTERVAL  = int(os.environ.get("BACKUP_INTERVAL", "20")) * 60  # → segundos
GIT_USER_NAME    = os.environ.get("GIT_USER_NAME", "MC Backup Bot")
GIT_USER_EMAIL   = os.environ.get("GIT_USER_EMAIL", "bot@render.mc")

# Estado global
pmmp_proc: subprocess.Popen | None = None
backup_lock = threading.Lock()    # evita backups simultâneos
shutdown_event = threading.Event()


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — Flask Keep-Alive
# ═══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Minecraft Bedrock (PocketMine-MP) está online!", 200

@app.route("/health")
def health():
    mc_alive = pmmp_proc is not None and pmmp_proc.poll() is None
    return {
        "status": "ok",
        "minecraft": "running" if mc_alive else "stopped",
        "server": "PocketMine-MP",
    }, 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    log.info("🌐 Flask iniciando na porta %s …", port)
    app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — Utilitários de Download
# ═══════════════════════════════════════════════════════════════════════════════

def _download(url: str, dest: str, label: str):
    """Baixa um arquivo com progresso e timeout robusto."""
    log.info("⬇  Baixando %s …", label)
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        total    = int(r.headers.get("content-length", 0))
        done     = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    mb  = done // (1024 * 1024)
                    print(f"\r   {pct:3d}% — {mb} MB", end="", flush=True)
    print()
    log.info("   ✅ Salvo em: %s", dest)


def _get_latest_asset_url(repo: str, name_filters: list[str], name_excludes: list[str] = None) -> str:
    """Busca a URL de download do asset mais recente em um repo GitHub."""
    api_url  = GITHUB_API.format(repo)
    response = requests.get(
        api_url,
        headers={"Accept": "application/vnd.github.v3+json"},
        timeout=15,
    )
    response.raise_for_status()
    assets = response.json().get("assets", [])

    for asset in assets:
        name = asset["name"]
        name_lower = name.lower()
        if all(f.lower() in name_lower for f in name_filters):
            if name_excludes and any(e.lower() in name_lower for e in name_excludes):
                continue
            return asset["browser_download_url"]

    raise RuntimeError(
        f"Nenhum asset encontrado em {repo} com filtros {name_filters}. "
        f"Verifique https://github.com/{repo}/releases"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3 — Playit.gg
# ═══════════════════════════════════════════════════════════════════════════════

def setup_playit():
    if os.path.isfile(PLAYIT_BIN):
        log.info("✅ Playit.gg já instalado.")
        return

    log.info("🔍 Buscando binário mais recente do Playit.gg …")
    try:
        url = _get_latest_asset_url(
            PLAYIT_REPO,
            name_filters=["linux", "amd64"],
            name_excludes=["tar.gz", "sha256", ".sig"],
        )
    except Exception:
        url = "https://github.com/playit-cloud/playit-agent/releases/latest/download/playit-linux-amd64"
        log.warning("   API falhou — usando URL de fallback.")

    _download(url, PLAYIT_BIN, "Playit.gg (linux-amd64)")
    st = os.stat(PLAYIT_BIN)
    os.chmod(PLAYIT_BIN, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def run_playit():
    env = os.environ.copy()

    if SECRET_KEY:
        env["SECRET_KEY"] = SECRET_KEY
        log.info("🔑 SECRET_KEY detectada — Playit autenticará sem Claim Code.")
    else:
        log.warning(
            "\n"
            "┌─────────────────────────────────────────────────────────────────┐\n"
            "│  ⚠️  SECRET_KEY não definida.                                   │\n"
            "│  Aguarde a mensagem abaixo nos logs e acesse o link para        │\n"
            "│  vincular sua conta Playit.gg:                                  │\n"
            "│                                                                 │\n"
            "│  >> Visit link to claim agent:                                  │\n"
            "│     https://playit.gg/claim?code=XXXX-XXXX-XXXX-XXXX           │\n"
            "│                                                                 │\n"
            "│  Depois: copie a SECRET_KEY do painel Playit →                 │\n"
            "│  Render > Environment > SECRET_KEY = sk-live-...               │\n"
            "└─────────────────────────────────────────────────────────────────┘"
        )

    log.info("🚀 Iniciando Playit.gg …")
    while not shutdown_event.is_set():
        proc = subprocess.Popen(
            [PLAYIT_BIN],
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=subprocess.DEVNULL,
        )
        proc.wait()
        if shutdown_event.is_set():
            break
        log.warning("Playit encerrou (código %s). Reiniciando em 10s …", proc.returncode)
        time.sleep(10)


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 4 — PHP Binary
# ═══════════════════════════════════════════════════════════════════════════════

def _find_php_exec() -> str | None:
    for root, _dirs, files in os.walk(BIN_DIR):
        if "php" in files:
            candidate = os.path.join(root, "php")
            if os.access(candidate, os.X_OK):
                return candidate
    return None


def setup_php() -> str:
    php = _find_php_exec()
    if php:
        log.info("✅ PHP já instalado em: %s", php)
        return php

    log.info("🔍 Buscando PHP binary (PM5, Linux x86-64) …")
    url = _get_latest_asset_url(
        PHP_REPO,
        name_filters=["linux_x86-64", "pm5", ".tar.gz"],
        name_excludes=["aarch64", "arm", "debug"],
    )

    tar_path = os.path.join(BASE_DIR, "php-bin.tar.gz")
    _download(url, tar_path, "PHP binary para PM5")

    os.makedirs(BIN_DIR, exist_ok=True)
    log.info("📦 Extraindo PHP binary …")
    with tarfile.open(tar_path, "r:gz") as tf:
        tf.extractall(BIN_DIR)
    os.remove(tar_path)

    php = _find_php_exec()
    if not php:
        raise RuntimeError("PHP extraído, mas executável não localizado.")
    log.info("✅ PHP pronto: %s", php)
    return php


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 5 — Backup do Mundo (GitHub)
# ═══════════════════════════════════════════════════════════════════════════════

def _git_remote_url() -> str:
    """Monta a URL autenticada do repositório GitHub."""
    return f"https://{GH_TOKEN}@github.com/{GH_REPO}.git"


def _run_git(*args, cwd: str = BACKUP_REPO_DIR, check: bool = True) -> subprocess.CompletedProcess:
    """Executa um comando git e retorna o resultado."""
    cmd = ["git"] + list(args)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _configure_git_identity():
    """Configura nome e email do git no repositório de backup."""
    _run_git("config", "user.name",  GIT_USER_NAME)
    _run_git("config", "user.email", GIT_USER_EMAIL)


def restore_world():
    """
    Restaura o mundo do GitHub no início do servidor.
    Se o repositório não existir ou estiver vazio, apenas cria a estrutura local.
    """
    if not GH_TOKEN or not GH_REPO:
        log.warning(
            "⚠️  GH_TOKEN ou GH_REPO não definidos.\n"
            "   O mundo NÃO será persistido entre reinicializações!\n"
            "   Configure essas variáveis no Render > Environment."
        )
        os.makedirs(PMMP_WORLDS_DIR, exist_ok=True)
        return

    log.info("🌍 Restaurando mundo do GitHub (%s) …", GH_REPO)
    remote = _git_remote_url()

    # ── Caso 1: repositório local já existe (restart do Render sem limpeza) ──
    if os.path.isdir(os.path.join(BACKUP_REPO_DIR, ".git")):
        log.info("   Repositório local encontrado — fazendo pull …")
        _configure_git_identity()
        result = _run_git("pull", "--rebase", "origin", "main", check=False)
        if result.returncode != 0:
            log.warning("   git pull falhou: %s", result.stderr.strip())
    else:
        # ── Caso 2: clone do repositório ──────────────────────────────────
        os.makedirs(BASE_DIR, exist_ok=True)
        log.info("   Clonando repositório de backup …")
        result = subprocess.run(
            ["git", "clone", "--depth=1", remote, BACKUP_REPO_DIR],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr
            if "empty" in stderr.lower() or "remote: Repository not found" in stderr.lower():
                log.warning("   Repositório vazio ou não existe — será inicializado no primeiro backup.")
                os.makedirs(BACKUP_REPO_DIR, exist_ok=True)
                _run_git("init", cwd=BACKUP_REPO_DIR)
                _run_git("remote", "add", "origin", remote, cwd=BACKUP_REPO_DIR)
                _configure_git_identity()
            else:
                log.error("   ❌ Falha no clone: %s", stderr.strip())
                os.makedirs(PMMP_WORLDS_DIR, exist_ok=True)
                return
        else:
            _configure_git_identity()

    # ── Copia worlds do backup para o diretório do PMMP ───────────────────
    backup_worlds = os.path.join(BACKUP_REPO_DIR, "worlds")
    if os.path.isdir(backup_worlds) and os.listdir(backup_worlds):
        log.info("   Copiando mundo salvo para pmmp/worlds/ …")
        if os.path.exists(PMMP_WORLDS_DIR):
            shutil.rmtree(PMMP_WORLDS_DIR)
        shutil.copytree(backup_worlds, PMMP_WORLDS_DIR)
        log.info("   ✅ Mundo restaurado com sucesso!")
    else:
        log.info("   Sem mundo salvo no repositório — começando do zero.")
        os.makedirs(PMMP_WORLDS_DIR, exist_ok=True)


def _send_pmmp_command(cmd: str):
    """Envia um comando para o console do PocketMine-MP."""
    global pmmp_proc
    if pmmp_proc and pmmp_proc.poll() is None and pmmp_proc.stdin:
        try:
            pmmp_proc.stdin.write((cmd + "\n").encode())
            pmmp_proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass


def backup_world(reason: str = "automático"):
    """
    Copia o mundo do PMMP para o repositório local e faz push para o GitHub.
    Protegido por lock para evitar execuções simultâneas.
    """
    if not GH_TOKEN or not GH_REPO:
        return  # silencioso — aviso já dado no restore_world()

    if not backup_lock.acquire(blocking=False):
        log.info("🔒 Backup já em andamento — ignorando chamada duplicada.")
        return

    try:
        log.info("💾 Iniciando backup do mundo (%s) …", reason)

        # 1. Pede ao PMMP para salvar e aguarda alguns segundos
        _send_pmmp_command("save-all")
        time.sleep(5)

        if not os.path.isdir(PMMP_WORLDS_DIR):
            log.warning("   pmmp/worlds/ não existe — nada para fazer backup.")
            return

        # 2. Copia worlds para o repositório de backup
        backup_worlds_dest = os.path.join(BACKUP_REPO_DIR, "worlds")
        if os.path.exists(backup_worlds_dest):
            shutil.rmtree(backup_worlds_dest)
        shutil.copytree(PMMP_WORLDS_DIR, backup_worlds_dest)

        # 3. Git add + commit + push
        _run_git("add", "-A")
        timestamp = time.strftime("%Y-%m-%d %H:%M UTC")
        result = _run_git(
            "commit", "-m", f"[{timestamp}] Backup {reason}",
            check=False,
        )

        if "nothing to commit" in result.stdout + result.stderr:
            log.info("   ✅ Sem alterações desde o último backup.")
            return

        # Tenta push; cria branch 'main' se ainda não existir
        push_result = _run_git("push", "origin", "main", check=False)
        if push_result.returncode != 0:
            # Tenta criar a branch remota
            _run_git("push", "--set-upstream", "origin", "main", check=False)

        log.info("   ✅ Backup enviado para GitHub: %s", timestamp)

    except Exception as exc:
        log.error("   ❌ Falha no backup: %s", exc)
    finally:
        backup_lock.release()


def backup_loop():
    """Thread que executa backups periódicos enquanto o servidor roda."""
    log.info("⏰ Backup automático a cada %d minutos.", BACKUP_INTERVAL // 60)
    # Aguarda o servidor iniciar antes do primeiro ciclo
    time.sleep(60)
    while not shutdown_event.is_set():
        backup_world(reason="periódico")
        shutdown_event.wait(timeout=BACKUP_INTERVAL)


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 6 — PocketMine-MP
# ═══════════════════════════════════════════════════════════════════════════════

def _write_default_configs():
    os.makedirs(PMMP_DIR, exist_ok=True)

    server_props = os.path.join(PMMP_DIR, "server.properties")
    if not os.path.isfile(server_props):
        with open(server_props, "w") as f:
            f.write(textwrap.dedent("""\
                #Properties Config file
                server-name=Minecraft Bedrock — Render
                motd=Servidor via Render.com | PocketMine-MP
                server-port=19132
                server-portv6=19133
                enable-ipv6=on
                white-list=off
                max-players=10
                gamemode=0
                force-gamemode=off
                hardcore=off
                pvp=on
                difficulty=1
                level-name=world
                level-seed=
                level-type=DEFAULT
                auto-save=on
                xbox-auth=off
                language=por
            """))
        log.info("📄 server.properties criado.")

    pocketmine_yml = os.path.join(PMMP_DIR, "pocketmine.yml")
    if not os.path.isfile(pocketmine_yml):
        with open(pocketmine_yml, "w") as f:
            f.write(textwrap.dedent("""\
                settings:
                  skip-setup-wizard: true
                  language: por
                  async-workers: auto
                  enable-profiler: false
                memory:
                  global-limit: 256
                  main-limit: 220
                player:
                  save-player-data: true
                aliases: {}
                worlds: {}
            """))
        log.info("📄 pocketmine.yml criado.")


def setup_pmmp():
    if os.path.isfile(PHAR_PATH):
        log.info("✅ PocketMine-MP.phar já presente.")
        return
    _download(PHAR_URL, PHAR_PATH, "PocketMine-MP.phar")


def run_minecraft(php_exec: str):
    global pmmp_proc

    log.info("🎮 Iniciando PocketMine-MP …")
    env = {**os.environ, "TERM": "xterm"}

    while not shutdown_event.is_set():
        pmmp_proc = subprocess.Popen(
            [php_exec, "-dphar.readonly=0", PHAR_PATH, "--no-wizard", "--ansi"],
            cwd=PMMP_DIR,
            env=env,
            stdin=subprocess.PIPE,   # PIPE → permite send_pmmp_command()
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        pmmp_proc.wait()
        if shutdown_event.is_set():
            break
        code = pmmp_proc.returncode
        log.warning("PocketMine-MP encerrou (código %s). Reiniciando em 15s …", code)
        time.sleep(15)


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 7 — Shutdown Gracioso (SIGTERM do Render)
# ═══════════════════════════════════════════════════════════════════════════════

def _handle_sigterm(signum, frame):
    """
    O Render envia SIGTERM antes de parar o container.
    Aproveitamos para fazer um backup final antes de sair.
    """
    log.info("\n🛑 SIGTERM recebido — encerrando com backup final …")
    shutdown_event.set()

    # Avisa jogadores online (se o PMMP ainda estiver rodando)
    _send_pmmp_command("say [SISTEMA] Servidor reiniciando em instantes. Salvando mundo...")
    time.sleep(3)
    _send_pmmp_command("stop")
    time.sleep(8)

    backup_world(reason="shutdown")
    log.info("✅ Backup final concluído. Encerrando.")
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT,  _handle_sigterm)


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 8 — Ponto de entrada
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log.info("=" * 66)
    log.info("  🚀  Minecraft Bedrock / Render — inicializando stack …")
    log.info("=" * 66)

    # ── Fase 1: preparação sequencial ─────────────────────────────────────
    try:
        setup_playit()
        php_exec = setup_php()
        setup_pmmp()
        _write_default_configs()
        restore_world()          # ← restaura o mundo ANTES de iniciar o PMMP
    except Exception as exc:
        log.critical("❌ Falha fatal na inicialização: %s", exc)
        sys.exit(1)

    # ── Fase 2: threads em paralelo ────────────────────────────────────────
    threads = [
        threading.Thread(target=run_playit,                     name="playit",  daemon=True),
        threading.Thread(target=run_minecraft, args=(php_exec,), name="pmmp",    daemon=True),
        threading.Thread(target=backup_loop,                    name="backup",  daemon=True),
    ]

    for t in threads:
        t.start()
        time.sleep(2)

    # Flask bloqueia a thread principal (Render precisa de uma porta HTTP ativa)
    run_web_server()
