"""PVE API 客户端 — 封装 Proxmox VE REST API 调用"""
import logging
import time

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class PVEClient:
    """Proxmox VE API 客户端"""

    def __init__(self, endpoint: str, username: str, password: str):
        self.endpoint = endpoint.rstrip("/")
        self.username = username
        self.password = password
        self.ticket: str = ""
        self.csrf_token: str = ""
        self.session = requests.Session()
        self.session.verify = False  # PVE 默认自签证书

    def authenticate(self):
        """获取认证票据"""
        url = f"{self.endpoint}/api2/json/access/ticket"
        resp = self.session.post(url, json={
            "username": self.username,
            "password": self.password,
        })
        resp.raise_for_status()
        data = resp.json()["data"]
        self.ticket = data["ticket"]
        self.csrf_token = data["CSRFPreventionToken"]
        # 设置 Cookie
        self.session.cookies.set("PVEAuthCookie", self.ticket)
        logger.info("PVE authentication successful")

    def get(self, path: str, params: dict = None) -> dict:
        """发起 GET 请求"""
        url = f"{self.endpoint}/api2/json{path}"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()["data"]

    def _headers(self) -> dict:
        return {"CSRFPreventionToken": self.csrf_token}

    def get_version(self) -> str:
        """获取 PVE 版本"""
        return self.get("/version").get("version", "")

    def get_cluster_status(self) -> list:
        """获取集群状态（含节点列表）"""
        return self.get("/cluster/status")

    def get_node_status(self, node: str) -> dict:
        """获取节点详细状态"""
        return self.get(f"/nodes/{node}/status")

    def get_node_qemu(self, node: str) -> list:
        """获取节点 VM 列表"""
        return self.get(f"/nodes/{node}/qemu")

    def get_node_lxc(self, node: str) -> list:
        """获取节点 LXC 列表"""
        return self.get(f"/nodes/{node}/lxc")

    def get_node_storage(self, node: str) -> list:
        """获取节点存储列表"""
        return self.get(f"/nodes/{node}/storage")

    def get_node_network(self, node: str) -> list:
        """获取节点网络接口"""
        return self.get(f"/nodes/{node}/network")

    def get_ceph_status(self) -> dict | None:
        """获取 Ceph 状态，无 Ceph 则返回 None"""
        try:
            return self.get("/cluster/ceph/status")
        except Exception:
            return None

    def get_vm_config(self, node: str, vmid: int) -> dict:
        """获取 VM 配置"""
        return self.get(f"/nodes/{node}/qemu/{vmid}/config")

    def get_vm_snapshots(self, node: str, vmid: int) -> list:
        """获取 VM 快照列表"""
        return self.get(f"/nodes/{node}/qemu/{vmid}/snapshot")

    def get_lxc_config(self, node: str, vmid: int) -> dict:
        """获取 LXC 容器配置"""
        return self.get(f"/nodes/{node}/lxc/{vmid}/config")
