"""pve-agent CLI 入口"""
import logging
import os
import socket
import sys

import click

from . import __version__
from .config import Config, CONFIG_FILE
from .pve_client import PVEClient
from .scanner import scan_full
from .scheduler import Scheduler
from .uploader import Uploader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@click.group()
@click.version_option(__version__, prog_name="pve-agent")
def main():
    """PVE 集群扫描 Agent — 采集 Proxmox VE 集群数据并上报到管理平台"""
    pass


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
    cfg.cluster_id = ""  # 后续从平台获取
    cfg.save()

    click.echo(f"Agent registered successfully!")
    click.echo(f"  Agent ID:    {cfg.agent_id}")
    click.echo(f"  Scan interval: {cfg.scan_interval}s")
    click.echo(f"  Config saved to: {CONFIG_FILE}")


@main.command()
@click.option("--once", is_flag=True, help="执行单次扫描后退出")
def start(once):
    """启动 Agent（心跳 + 定时扫描）"""
    cfg = Config.load()
    if not cfg.is_registered():
        click.echo("Agent not initialized. Run 'pve-agent init' first.", err=True)
        sys.exit(1)

    click.echo(f"Starting pve-agent (id: {cfg.agent_id})...")
    scheduler = Scheduler(cfg)

    if once:
        scheduler.run_once()
    else:
        scheduler.start()


@main.command()
def scan():
    """执行单次扫描"""
    cfg = Config.load()
    if not cfg.is_registered():
        click.echo("Agent not initialized. Run 'pve-agent init' first.", err=True)
        sys.exit(1)

    pve = PVEClient(cfg.pve_api_endpoint, cfg.pve_username, cfg.pve_password)
    pve.authenticate()

    click.echo("Scanning...")
    scan_data = scan_full(pve)

    uploader = Uploader(cfg.platform_url)
    result = uploader.upload_scan(cfg.agent_id, cfg.cluster_id, scan_data)
    click.echo(f"Upload complete: {result}")


@main.command()
def status():
    """显示 Agent 状态"""
    cfg = Config.load()
    if not cfg.is_registered():
        click.echo("Agent not initialized.")
        return

    click.echo(f"Agent ID:      {cfg.agent_id}")
    click.echo(f"Platform:      {cfg.platform_url}")
    click.echo(f"PVE Endpoint:  {cfg.pve_api_endpoint}")
    click.echo(f"Scan Interval: {cfg.scan_interval}s")
    click.echo(f"Config:        {CONFIG_FILE}")


@main.command()
@click.option("--platform-url", prompt="新平台地址", default="")
@click.option("--scan-interval", prompt="新扫描间隔(秒)", default=0, type=int)
def config(platform_url, scan_interval):
    """修改 Agent 配置"""
    cfg = Config.load()
    if not cfg.is_registered():
        click.echo("Agent not initialized.", err=True)
        sys.exit(1)

    if platform_url:
        cfg.platform_url = platform_url
    if scan_interval > 0:
        cfg.scan_interval = scan_interval
    cfg.save()
    click.echo("Config updated.")


if __name__ == "__main__":
    main()
