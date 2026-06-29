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
