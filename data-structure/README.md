# 数据结构目录

本目录包含 PVE 集群扫描与管理平台的数据结构分析文档，涵盖数据库模型、PVE API 接口、字段映射关系以及数据流架构。

## 目录结构

| 文件 | 说明 |
|------|------|
| [database-models.md](database-models.md) | 当前数据库模型定义、字段说明、模型间关系以及改进建议 |
| [api-interfaces.md](api-interfaces.md) | PVE API 端点参考，Agent 调用 PVE 所需的接口列表与数据格式 |
| [field-mapping.md](field-mapping.md) | PVE API 返回字段与数据库模型字段的详细映射关系，含单位转换 |
| [data-flow.md](data-flow.md) | 数据采集架构、Agent → 服务器 → 数据库的完整数据流 |

## 适用范围

- 数据库模型设计 / 修改
- Agent CLI 工具开发
- API 序列化器实现
- 数据采集与入库逻辑

## 兼容性评估

数据库模型与 PVE API 整体匹配度约 **90%**，核心数据（节点、VM、LXC、Ceph）接入无障碍。

### 已知问题

| 问题 | 影响 | 建议修复 |
|------|------|---------|
| `rootfs_*_gb`、`disk_gb`、Storage `*_gb` 使用 `BigIntegerField` | 存储容量转 GB 后浮点数被截断（如 48.5→48） | 改为 `FloatField` 或改用 MB 单位 + `BigIntegerField` |
| Storage 缺少 `enabled` 字段 | PVE API 返回此字段，模型未收录 | 新增 `BooleanField(default=True)` |
| NetworkInterface 缺少 `mtu`/`bridge_ports`/`bond_mode` | 无法完整存储 Bridge/Bond 配置 | 按需补充 |

> 详细分析见 [database-models.md](database-models.md) 改进建议章节和 [field-mapping.md](field-mapping.md) 通用转换规则。
