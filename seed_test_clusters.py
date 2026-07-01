#!/usr/bin/env python3
"""
生成 3 个测试集群的网络拓扑数据（无需 Agent）。
用法: python3 seed_test_clusters.py
"""
import os, sys, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from datetime import datetime, timezone
from apps.accounts.models import User
from apps.clusters.models import Cluster
from apps.scanner.models import ClusterNode, NetworkInterface

NOW = datetime.now(timezone.utc)

# ──────────────────────────────────────────
# 获取第一个用户（管理员 buladou）
# ──────────────────────────────────────────
user = User.objects.first()
if not user:
    print("❌ 数据库中没有用户，请先创建用户")
    sys.exit(1)
print(f"✓ 使用用户: {user.username} (id={user.id})")


def create_cluster(name, desc):
    c = Cluster.objects.create(
        user=user, name=name, description=desc,
        status="active", pve_endpoint="https://0.0.0.0:8006",
        pve_token="test-token", total_nodes=0,
        last_scanned_at=NOW,
    )
    print(f"  ✓ 集群: {name} (id={c.id})")
    return c


def create_node(cluster, name, ip=None):
    n = ClusterNode.objects.create(
        cluster=cluster, node_name=name, status="online",
        pve_version="pve-manager/8.2.4", cpu_cores=16, cpu_load=0.35,
        memory_total_mb=32768, memory_used_mb=12000,
        ip_address=ip, scanned_at=NOW,
    )
    print(f"    ✓ 节点: {name}")
    return n


def create_iface(node, name, type_, address="", gateway="",
                 bridge_ports="", bond_mode="", bond_slaves="",
                 vlan_id=None, active=True):
    return NetworkInterface.objects.create(
        node=node, name=name, type=type_, active=active,
        method="static" if address else "",
        address=address, gateway=gateway,
        bridge_ports=bridge_ports,
        bond_mode=bond_mode, bond_slaves=bond_slaves,
        vlan_id=vlan_id, scanned_at=NOW,
    )


# ════════════════════════════════════════════
# Cluster A: 5 节点，bond 嵌套，3 层网段
# ════════════════════════════════════════════
print("\n━━━ Cluster A: 5 节点 bond 嵌套 ━━━")
ca = create_cluster(
    "测试A-五节点Bond",
    "5节点，每节点5网口。vmbr0管理(192.168.10.x)，bond0业务(10.0.1.x)，bond1 Ceph(10.0.2.x)"
)

for i in range(1, 6):
    node = create_node(ca, f"pve-a{i}", ip=f"192.168.10.{i}")

    # vmbr0 (管理网 bridge，包含 bond0 + eno1)
    create_iface(node, "vmbr0", "bridge",
                 address=f"192.168.10.{i}", gateway="192.168.10.254",
                 bridge_ports="bond0 eno1")

    # bond0 (业务网 bond，包含 enp1s0 + enp2s0)
    create_iface(node, "bond0", "bond",
                 bond_mode="802.3ad", bond_slaves="enp1s0 enp2s0")

    # eno1 (管理网物理口，属于 vmbr0)
    create_iface(node, "eno1", "eth")

    # enp1s0, enp2s0 (业务网物理口，属于 bond0)
    create_iface(node, "enp1s0", "eth")
    create_iface(node, "enp2s0", "eth")

    # bond1 (Ceph 网 bond，独立，不在任何 bridge 下)
    create_iface(node, "bond1", "bond",
                 bond_mode="balance-rr", bond_slaves="enp3s0 enp4s0")

    # enp3s0, enp4s0 (Ceph 网物理口，属于 bond1)
    create_iface(node, "enp3s0", "eth")
    create_iface(node, "enp4s0", "eth")

ca.total_nodes = 5
ca.save(update_fields=["total_nodes"])

# ════════════════════════════════════════════
# Cluster B: 3 节点，不等网口数
# ════════════════════════════════════════════
print("\n━━━ Cluster B: 3 节点不等网口 ━━━")
cb = create_cluster(
    "测试B-不等网口",
    "3节点：node-big(5口)、node-small-a(2口)、node-small-b(2口)，共用192.168.20.x网段"
)

# node-big: 4 口 bridge + 4 个物理口
nb = create_node(cb, "node-big", ip="192.168.20.1")
create_iface(nb, "vmbr0", "bridge",
             address="192.168.20.1", gateway="192.168.20.254",
             bridge_ports="eno1 eno2 eno3 eno4")
for eno in ["eno1", "eno2", "eno3", "eno4"]:
    create_iface(nb, eno, "eth")

# node-small-a: 1 口
nsa = create_node(cb, "node-small-a", ip="192.168.20.2")
create_iface(nsa, "vmbr0", "bridge",
             address="192.168.20.2", gateway="192.168.20.254",
             bridge_ports="eno1")
create_iface(nsa, "eno1", "eth")

# node-small-b: 1 口
nsb = create_node(cb, "node-small-b", ip="192.168.20.3")
create_iface(nsb, "vmbr0", "bridge",
             address="192.168.20.3", gateway="192.168.20.254",
             bridge_ports="eno1")
create_iface(nsb, "eno1", "eth")

cb.total_nodes = 3
cb.save(update_fields=["total_nodes"])

# ════════════════════════════════════════════
# Cluster C: 1 节点，双网桥 + VLAN
# ════════════════════════════════════════════
print("\n━━━ Cluster C: 1 节点双桥+VLAN ━━━")
cc = create_cluster(
    "测试C-单节点双桥VLAN",
    "1节点：vmbr0(管理,1口) + vmbr1(业务,2口) + vmbr1.100(VLAN)"
)

nc = create_node(cc, "pve-single", ip="10.0.0.1")

create_iface(nc, "vmbr0", "bridge",
             address="10.0.0.1", gateway="10.0.0.254",
             bridge_ports="eno1")
create_iface(nc, "eno1", "eth")

create_iface(nc, "vmbr1", "bridge",
             bridge_ports="eno2 eno3")
create_iface(nc, "eno2", "eth")
create_iface(nc, "eno3", "eth")

create_iface(nc, "vmbr1.100", "vlan",
             address="172.16.0.1", vlan_id=100)

cc.total_nodes = 1
cc.save(update_fields=["total_nodes"])

# ──────────────────────────────────────────
print("\n━━━ 完成 ━━━")
print(f"  Cluster A: {ca.name} (id={ca.id}) — 5 节点 × 8 网口 = 40 条 NetworkInterface")
print(f"  Cluster B: {cb.name} (id={cb.id}) — 3 节点 × 6 网口 = 18 条 NetworkInterface")
print(f"  Cluster C: {cc.name} (id={cc.id}) — 1 节点 × 5 网口 = 5 条 NetworkInterface")
print(f"\n刷新拓扑页面即可看到 3 个新集群的网络拓扑。")
