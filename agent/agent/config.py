"""Agent 配置管理"""
import os
from pathlib import Path

import yaml

CONFIG_DIR = Path.home() / ".config" / "pve-agent"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


class Config:
    """Agent 本地配置"""

    def __init__(self):
        self.platform_url: str = ""       # Django 平台地址
        self.agent_token: str = ""        # 集群 agent_token
        self.agent_id: str = ""           # 注册后获得
        self.cluster_id: str = ""         # 集群 ID
        self.pve_api_endpoint: str = ""   # PVE API 地址
        self.pve_username: str = ""       # PVE 用户名
        self.pve_password: str = ""       # PVE 密码
        self.scan_interval: int = 3600    # 扫描间隔(秒)
        self.heartbeat_interval: int = 60 # 心跳间隔(秒)

    @classmethod
    def load(cls) -> "Config":
        """从配置文件加载"""
        cfg = cls()
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                data = yaml.safe_load(f) or {}
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        return cfg

    def save(self):
        """保存到配置文件"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "platform_url": self.platform_url,
            "agent_token": self.agent_token,
            "agent_id": self.agent_id,
            "cluster_id": self.cluster_id,
            "pve_api_endpoint": self.pve_api_endpoint,
            "pve_username": self.pve_username,
            "pve_password": self.pve_password,
            "scan_interval": self.scan_interval,
            "heartbeat_interval": self.heartbeat_interval,
        }
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def is_registered(self) -> bool:
        return bool(self.agent_id)
