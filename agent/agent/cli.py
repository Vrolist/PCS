"""pcs-agent CLI 入口"""
import logging
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone

import click

from . import __version__
from .config import CONFIG_FILE, CONFIG_DIR, INSTALL_DIR, SERVICE_FILE, Config
from .pve_client import PVEClient
from .scanner import scan_full
from .scheduler import Scheduler
from .uploader import Uploader

SERVICE_NAME = "pcs-agent"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _run_systemctl(*args) -> str:
    """执行 systemctl 命令并返回输出"""
    try:
        result = subprocess.run(
            ["systemctl", *args],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def _get_service_status() -> str:
    """获取服务状态"""
    output = _run_systemctl("is-active", SERVICE_NAME)
    return output if output else "unknown"


def _get_uptime() -> str:
    """获取服务运行时长"""
    output = _run_systemctl("show", SERVICE_NAME, "--property=ActiveEnterTimestamp")
    if not output or "n/a" in output:
        return "未运行"
    try:
        # ActiveEnterTimestamp=Mon 2026-06-29 15:30:00 CST
        ts_str = output.split("=", 1)[1]
        start = datetime.fromisoformat(ts_str)
        now = datetime.now(start.tzinfo)
        delta = now - start
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)
    except Exception:
        return "未知"


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="pcs-agent")
@click.pass_context
def main(ctx):
    """PVE 集群扫描 Agent — 采集 Proxmox VE 集群数据并上报到管理平台"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ============================================================
# init — 初始化（注册到平台）
# ============================================================

@main.command()
@click.option("--platform-url", prompt="平台地址", help="Django 管理平台地址")
@click.option("--token", prompt="Agent Token", help="集群的 agent_token")
@click.option("--pve-endpoint", prompt="PVE API 地址", help="如 https://192.168.1.100:8006")
@click.option("--pve-username", prompt="PVE 用户名", default="root@pam")
@click.option("--pve-password", prompt=True, hide_input=True, help="PVE 密码")
@click.option("--scan-interval", default=3600, type=int, help="扫描间隔(秒)")
def init(platform_url, token, pve_endpoint, pve_username, pve_password, scan_interval):
    """初始化 Agent — 注册到平台并保存配置"""
    cfg = Config()
    cfg.platform_url = platform_url
    cfg.agent_token = token
    cfg.pve_api_endpoint = pve_endpoint
    cfg.pve_username = pve_username
    cfg.pve_password = pve_password
    cfg.scan_interval = scan_interval

    hostname = socket.gethostname()

    click.echo(f"Registering agent on {hostname}...")
    uploader = Uploader(platform_url)
    try:
        result = uploader.register(
            agent_token=token,
            pve_endpoint=pve_endpoint,
            pve_username=pve_username,
            pve_password=pve_password,
            hostname=hostname,
            scan_interval=scan_interval,
        )
    except Exception as e:
        click.echo(f"Registration failed: {e}", err=True)
        sys.exit(1)

    cfg.agent_id = result["agent_id"]
    cfg.cluster_id = ""
    cfg.save()

    click.echo(f"Agent registered successfully!")
    click.echo(f"  Agent ID:    {cfg.agent_id}")
    click.echo(f"  Scan interval: {cfg.scan_interval}s")
    click.echo(f"  Config saved to: {CONFIG_FILE}")


# ============================================================
# start — 启动守护进程
# ============================================================

@main.command()
@click.option("--foreground", is_flag=True, help="前台运行（systemd 使用）")
@click.option("--once", is_flag=True, help="执行单次扫描后退出")
def start(foreground, once):
    """启动 Agent（心跳 + 定时扫描）"""
    cfg = Config.load()
    if not cfg.is_registered():
        click.echo("Agent not initialized. Run 'pcs-agent init' first.", err=True)
        sys.exit(1)

    click.echo(f"Starting pcs-agent (id: {cfg.agent_id})...")
    scheduler = Scheduler(cfg)

    if once:
        scheduler.run_once()
    else:
        scheduler.start()


# ============================================================
# status — 查看运行状态
# ============================================================

@main.command()
def status():
    """查看 Agent 运行状态"""
    cfg = Config.load()
    if not cfg.is_registered():
        click.echo("Agent 未安装或未初始化。")
        click.echo(f"  安装目录: {INSTALL_DIR}")
        click.echo(f"  配置文件: {CONFIG_FILE}")
        return

    # 服务状态
    service_status = _get_service_status()
    uptime = _get_uptime()

    # 从平台获取最新统计
    scan_count = "未知"
    failed_count = "未知"
    last_scan = "未知"
    try:
        uploader = Uploader(cfg.platform_url)
        # 通过心跳获取平台侧信息（简化实现）
    except Exception:
        pass

    click.echo()
    click.echo("PVE Agent 状态")
    click.echo("=" * 40)
    click.echo(f"  版本:       v{__version__}")
    click.echo(f"  Agent ID:   {cfg.agent_id}")
    click.echo(f"  平台:       {cfg.platform_url}")
    click.echo(f"  PVE:        {cfg.pve_api_endpoint}")
    click.echo(f"  扫描间隔:   {cfg.scan_interval}s")
    click.echo(f"  心跳间隔:   {cfg.heartbeat_interval}s")
    click.echo()
    click.echo(f"  服务状态:   {service_status}")
    click.echo(f"  运行时长:   {uptime}")
    click.echo()
    click.echo(f"  配置文件:   {CONFIG_FILE}")
    click.echo(f"  安装目录:   {INSTALL_DIR}")
    click.echo()


# ============================================================
# stop — 停止服务
# ============================================================

@main.command()
def stop():
    """停止 Agent 服务"""
    click.echo("Stopping pcs-agent...")
    output = _run_systemctl("stop", SERVICE_NAME)
    if output:
        click.echo(output)
    click.echo("pcs-agent stopped.")


# ============================================================
# update — 更新到最新版本
# ============================================================

@main.command()
@click.option("--check", is_flag=True, help="仅检查不更新")
def update(check):
    """更新 Agent 到最新版本"""
    cfg = Config.load()
    current = __version__

    click.echo("检查更新中...")
    click.echo(f"当前版本: v{current}")

    # 从平台查询最新版本
    try:
        uploader = Uploader(cfg.platform_url)
        result = uploader.check_version()
        latest = result.get("latest_version", current)
    except Exception as e:
        click.echo(f"无法连接平台: {e}", err=True)
        click.echo("请检查网络连接或平台地址配置。")
        sys.exit(1)

    click.echo(f"最新版本: v{latest}")

    if current == latest:
        click.echo("已是最新版本，无需更新。")
        return

    if check:
        click.echo("发现新版本，使用 'pcs-agent update' 进行更新。")
        return

    click.echo("发现新版本，正在更新...")

    # 1. 停止服务
    click.echo("1. 停止服务...")
    _run_systemctl("stop", SERVICE_NAME)

    # 2. 更新 pip 包
    click.echo("2. 下载新版本...")
    pip = str(INSTALL_DIR / "venv" / "bin" / "pip")
    if not os.path.exists(pip):
        pip = sys.executable.replace("python", "pip")

    result = subprocess.run(
        [pip, "install", "--upgrade", "pcs-agent"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        click.echo(f"更新失败: {result.stderr}", err=True)
        # 尝试重启旧版本
        _run_systemctl("start", SERVICE_NAME)
        sys.exit(1)

    # 3. 重启服务
    click.echo("3. 重启服务...")
    _run_systemctl("daemon-reload")
    _run_systemctl("restart", SERVICE_NAME)

    # 4. 验证
    click.echo("4. 验证服务状态...")
    import time
    time.sleep(2)
    new_status = _get_service_status()

    click.echo()
    click.echo("=" * 40)
    click.echo("更新完成！")
    click.echo(f"  旧版本: v{current}")
    click.echo(f"  新版本: v{latest}")
    click.echo(f"  服务状态: {new_status}")
    click.echo("=" * 40)


# ============================================================
# uninstall — 卸载 Agent
# ============================================================

@main.command()
@click.option("--force", is_flag=True, help="跳过确认")
def uninstall(force):
    """卸载 Agent"""
    cfg = Config.load()

    if not cfg.is_registered() and not CONFIG_FILE.exists():
        click.echo("Agent 未安装。")
        return

    if not force:
        click.echo("即将卸载 PVE Agent:")
        click.echo(f"  Agent ID:   {cfg.agent_id or '未知'}")
        click.echo(f"  安装目录:   {INSTALL_DIR}")
        click.echo(f"  配置目录:   {CONFIG_DIR}")
        click.echo()
        if not click.confirm("确认卸载?"):
            click.echo("已取消。")
            return

    # 1. 停止服务
    click.echo("1. 停止服务...")
    _run_systemctl("stop", SERVICE_NAME)

    # 2. 禁用开机自启
    click.echo("2. 禁用开机自启...")
    _run_systemctl("disable", SERVICE_NAME)

    # 3. 删除 systemd 服务文件
    click.echo("3. 删除 systemd 服务...")
    if SERVICE_FILE.exists():
        SERVICE_FILE.unlink()
    _run_systemctl("daemon-reload")

    # 4. 通知平台
    if cfg.agent_id:
        click.echo("4. 通知平台...")
        try:
            uploader = Uploader(cfg.platform_url)
            uploader.unregister(cfg.agent_id)
        except Exception:
            pass  # 通知失败不影响卸载

    # 5. 删除文件
    click.echo("5. 清理文件...")
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
    if CONFIG_DIR.exists():
        shutil.rmtree(CONFIG_DIR)

    click.echo()
    click.echo("Agent 已卸载。")


# ============================================================
# install — 安装为 systemd 服务
# ============================================================

@main.command()
def install():
    """安装为 systemd 服务并启动"""
    cfg = Config.load()
    if not cfg.is_registered():
        click.echo("请先运行 'pcs-agent init' 初始化。", err=True)
        sys.exit(1)

    venv_pip = str(INSTALL_DIR / "venv" / "bin" / "python")
    if not os.path.exists(venv_pip):
        venv_pip = sys.executable

    # 生成 systemd service 文件
    service_content = f"""[Unit]
Description=PVE Cluster Scan Agent
After=network.target

[Service]
Type=simple
ExecStart={venv_pip} -m agent.cli start --foreground
Restart=always
RestartSec=10
WorkingDirectory={INSTALL_DIR}

[Install]
WantedBy=multi-user.target
"""

    SERVICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SERVICE_FILE.write_text(service_content)

    # 安装并启动
    _run_systemctl("daemon-reload")
    _run_systemctl("enable", SERVICE_NAME)
    _run_systemctl("start", SERVICE_NAME)

    import time
    time.sleep(1)
    svc_status = _get_service_status()

    click.echo()
    click.echo("Agent 已安装为 systemd 服务")
    click.echo(f"  服务文件: {SERVICE_FILE}")
    click.echo(f"  服务状态: {svc_status}")
    click.echo(f"  查看日志: journalctl -u {SERVICE_NAME} -f")


# ============================================================
# logs — 查看日志
# ============================================================

@main.command()
@click.option("-n", "--lines", default=50, type=int, help="显示行数")
@click.option("-f", "--follow", is_flag=True, help="实时跟踪")
def logs(lines, follow):
    """查看 Agent 日志"""
    cmd = ["journalctl", "-u", SERVICE_NAME]
    if follow:
        cmd.append("-f")
    cmd.extend(["-n", str(lines)])
    os.execvp("journalctl", cmd)


if __name__ == "__main__":
    main()
