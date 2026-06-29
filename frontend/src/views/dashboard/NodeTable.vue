<template>
  <div class="node-table-card">
    <div class="card-header">
      <span class="card-title">节点详情</span>
      <a href="/clusters" class="view-all">查看全部</a>
    </div>
    <el-table :data="nodes" style="width: 100%">
      <el-table-column prop="name" label="节点名称" min-width="120">
        <template #default="{ row }">
          <span class="node-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="cpu" label="CPU" min-width="160">
        <template #default="{ row }">
          <div class="usage-cell">
            <el-progress
              :percentage="row.cpuPercent"
              :stroke-width="8"
              :color="getCpuColor(row.cpuPercent)"
              :show-text="false"
            />
            <span class="usage-text">{{ row.cpuPercent }}%</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="ram" label="内存" min-width="200">
        <template #default="{ row }">
          <div class="usage-cell">
            <el-progress
              :percentage="row.ramPercent"
              :stroke-width="8"
              :color="'#409eff'"
              :show-text="false"
            />
            <span class="usage-text">{{ row.ramUsed }}/{{ row.ramTotal }} ({{ row.ramPercent }}%)</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="disk" label="磁盘" min-width="140">
        <template #default="{ row }">
          <span class="disk-text">{{ row.diskUsed }}/{{ row.diskTotal }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP地址" min-width="150" />
      <el-table-column prop="pveVersion" label="PVE版本" min-width="160" />
      <el-table-column prop="status" label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'online' ? 'success' : 'warning'" disable-transitions>
            {{ row.status === 'online' ? '在线' : '告警' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
const nodes = [
  { name: 'pve-1', cpuPercent: 35, ramUsed: '8.2GB', ramTotal: '32GB', ramPercent: 25.6, diskUsed: '1.2TB', diskTotal: '4TB', ip: '192.168.1.101', pveVersion: 'pve-manager/8.1.4', status: 'online' },
  { name: 'pve-2', cpuPercent: 82, ramUsed: '12GB', ramTotal: '32GB', ramPercent: 37.5, diskUsed: '2.1TB', diskTotal: '4TB', ip: '192.168.1.102', pveVersion: 'pve-manager/8.1.4', status: 'warning' },
  { name: 'pve-3', cpuPercent: 28, ramUsed: '6GB', ramTotal: '32GB', ramPercent: 18.8, diskUsed: '0.8TB', diskTotal: '4TB', ip: '192.168.1.103', pveVersion: 'pve-manager/8.1.4', status: 'online' },
  { name: 'pve-4', cpuPercent: 55, ramUsed: '10GB', ramTotal: '32GB', ramPercent: 31.3, diskUsed: '1.5TB', diskTotal: '4TB', ip: '192.168.1.104', pveVersion: 'pve-manager/8.1.3', status: 'online' },
]

function getCpuColor(percent: number): string {
  if (percent > 85) return '#f56c6c'
  if (percent >= 70) return '#e6a23c'
  return '#67c23a'
}
</script>

<style scoped>
.node-table-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
  transition: background-color 0.3s, border-color 0.3s;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
}
.view-all {
  font-size: 13px;
  color: var(--primary-color);
  text-decoration: none;
  transition: opacity 0.2s;
}
.view-all:hover {
  opacity: 0.8;
}
:deep(.el-table) {
  background: transparent;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(64, 158, 255, 0.05);
  --el-table-border-color: var(--border-color);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-secondary);
}
:deep(.el-table::before),
:deep(.el-table--border::after) {
  display: none;
}
:deep(.el-table th.el-table__cell) {
  background: transparent;
  border-bottom: 1px solid var(--border-color);
}
:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid var(--border-color);
}
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) {
  background-color: rgba(64, 158, 255, 0.05);
}
:deep(.el-table--border .el-table__inner-wrapper::after),
:deep(.el-table--border::before),
:deep(.el-table--border::after) {
  background-color: var(--border-color);
}
.node-name {
  font-weight: 600;
  color: var(--text-primary);
}
.usage-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.usage-text {
  font-size: 12px;
  color: var(--text-muted);
}
.disk-text {
  font-size: 14px;
  color: var(--text-primary);
}
:deep(.el-tag--success) {
  --el-tag-bg-color: rgba(103, 194, 58, 0.15);
  --el-tag-text-color: #67c23a;
  --el-tag-border-color: transparent;
}
:deep(.el-tag--warning) {
  --el-tag-bg-color: rgba(230, 162, 60, 0.15);
  --el-tag-text-color: #e6a23c;
  --el-tag-border-color: transparent;
}
</style>
