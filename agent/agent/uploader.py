"""上报器 — 将扫描数据推送到 Django 平台"""
import logging

import requests

logger = logging.getLogger(__name__)


class Uploader:
    """向 Django 平台上报数据"""

    def __init__(self, platform_url: str):
        self.base_url = platform_url.rstrip("/")
        self.session = requests.Session()

    def _post(self, path: str, data: dict) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: dict = None) -> dict | list:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def register(self, agent_token: str, pve_endpoint: str,
                 pve_username: str, pve_password: str,
                 hostname: str, scan_interval: int) -> dict:
        """注册 Agent"""
        return self._post("/api/agent/register/", {
            "agent_token": agent_token,
            "pve_api_endpoint": pve_endpoint,
            "pve_username": pve_username,
            "pve_password": pve_password,
            "hostname": hostname,
            "scan_interval": scan_interval,
        })

    def heartbeat(self, agent_id: str, status: str = "online",
                  current_task: str = "") -> dict:
        """发送心跳"""
        return self._post("/api/agent/heartbeat/", {
            "agent_id": agent_id,
            "status": status,
            "current_task": current_task,
        })

    def upload_scan(self, agent_id: str, cluster_id: str,
                    scan_data: dict) -> dict:
        """上传扫描数据"""
        payload = {
            "agent_id": agent_id,
            "cluster_id": cluster_id,
            **scan_data,
        }
        return self._post("/api/agent/scan/upload/", payload)

    def get_tasks(self, agent_id: str) -> list:
        """获取下发任务"""
        return self._get("/api/agent/tasks/", {"agent_id": agent_id})
