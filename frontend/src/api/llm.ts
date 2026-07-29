import request from './request'

export interface LLMConfigDTO {
  id: number
  name: string
  provider: string
  api_key?: string       // 仅写入时使用 (write_only)
  has_key: boolean       // 后端是否有加密 key
  model: string
  base_url: string
  is_active: boolean
}

/** 获取当前用户的所有 LLM 配置 */
export function fetchLLMConfigs(): Promise<LLMConfigDTO[]> {
  return request.get('/auth/llm-configs/') as any
}

/** 创建 LLM 配置 */
export function createLLMConfig(data: Partial<LLMConfigDTO>): Promise<LLMConfigDTO> {
  return request.post('/auth/llm-configs/', data) as any
}

/** 更新 LLM 配置 */
export function updateLLMConfig(id: number, data: Partial<LLMConfigDTO>): Promise<LLMConfigDTO> {
  return request.patch(`/auth/llm-configs/${id}/`, data) as any
}

/** 删除 LLM 配置 */
export function deleteLLMConfig(id: number): Promise<void> {
  return request.delete(`/auth/llm-configs/${id}/`) as any
}

/** 设为当前配置 */
export function setActiveLLMConfig(id: number): Promise<any> {
  return request.post(`/auth/llm-configs/${id}/set-active/`) as any
}
