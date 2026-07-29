import request from './request'

export interface SystemPromptDTO {
  id: number
  name: string
  content: string
  is_default: boolean
  created_at: string
  updated_at: string
}

/** 获取角色约束列表 */
export function fetchSystemPrompts(): Promise<SystemPromptDTO[]> {
  return request.get('/auth/system-prompts/') as any
}

/** 创建约束 */
export function createSystemPrompt(data: { name: string; content?: string }): Promise<SystemPromptDTO> {
  return request.post('/auth/system-prompts/', data) as any
}

/** 更新约束 */
export function updateSystemPrompt(id: number, data: { name?: string; content?: string }): Promise<SystemPromptDTO> {
  return request.patch(`/auth/system-prompts/${id}/`, data) as any
}

/** 删除约束 */
export function deleteSystemPrompt(id: number): Promise<void> {
  return request.delete(`/auth/system-prompts/${id}/`) as any
}
