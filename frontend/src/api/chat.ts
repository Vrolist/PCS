import request from './request'

export interface ChatMessageDTO {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ChatConversationDTO {
  id: number
  title: string
  message_count: number
  messages?: ChatMessageDTO[]
  last_message?: { role: string; content: string } | null
  created_at: string
  updated_at: string
}

/** 获取对话列表 */
export function fetchConversations(): Promise<ChatConversationDTO[]> {
  return request.get('/auth/chat/conversations/') as any
}

/** 创建新对话 */
export function createConversation(title?: string): Promise<ChatConversationDTO> {
  return request.post('/auth/chat/conversations/', { title: title || '' }) as any
}

/** 获取对话详情（含消息） */
export function fetchConversation(id: number): Promise<ChatConversationDTO> {
  return request.get(`/auth/chat/conversations/${id}/`) as any
}

/** 删除对话 */
export function deleteConversation(id: number): Promise<void> {
  return request.delete(`/auth/chat/conversations/${id}/`) as any
}

/** 重命名对话 */
export function renameConversation(id: number, title: string): Promise<ChatConversationDTO> {
  return request.patch(`/auth/chat/conversations/${id}/`, { title }) as any
}

/** 添加消息 */
export function createMessage(conversationId: number, role: string, content: string): Promise<ChatMessageDTO> {
  return request.post(`/auth/chat/conversations/${conversationId}/messages/`, { role, content }) as any
}
