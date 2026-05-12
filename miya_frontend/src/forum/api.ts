import API from '@/api/core'
import type { ForumPost, ForumPostDetail, PaginatedResponse } from './types'

function parseResult(resp: any): any {
  const r = resp?.result
  if (typeof r === 'string') {
    try { return JSON.parse(r) } catch { return r }
  }
  return r
}

export async function fetchPosts(
  sort: string = 'latest',
  page: number = 1,
  pageSize: number = 20,
  _timeOrder?: string,
  _yearMonth?: string | null,
): Promise<PaginatedResponse<ForumPost>> {
  const resp = await API.mcpCall('naga_community', 'get_posts', { sort, page, page_size: pageSize })
  const r = parseResult(resp)
  if (!r?.success && !r?.data && typeof r !== 'object') throw new Error('加载帖子失败')
  if (r.status_code === 401) throw new Error('请先登录娜迦社区')
  const data = r?.data || r || {}
  const items = Array.isArray(data) ? data : (Array.isArray(data.items) ? data.items : [])
  return { items, total: data.total || 0, page, pageSize }
}

export async function fetchPost(id: string): Promise<ForumPostDetail> {
  const resp = await API.mcpCall('naga_community', 'get_post_detail', { post_id: id })
  const r = parseResult(resp)
  return (r?.data || r) as ForumPostDetail
}

export async function likePost(id: string) {
  const resp = await API.mcpCall('naga_community', 'like_post', { post_id: id })
  const r = parseResult(resp)
  return r?.data || r || { likes: 0, liked: false }
}

export async function likeComment(id: string) {
  const resp = await API.mcpCall('naga_community', 'like_comment', { comment_id: id })
  const r = parseResult(resp)
  return r?.data || r || { likes: 0, liked: false }
}

export async function deletePost(id: string) {
  return API.mcpCall('naga_community', 'delete_post', { post_id: id })
}

export async function deleteComment(id: string) {
  return API.mcpCall('naga_community', 'delete_comment', { comment_id: id })
}

export async function createPost(payload: { title: string, content: string, tags?: string[] }) {
  return API.mcpCall('naga_community', 'create_post', payload)
}

export async function createComment(payload: { postId: string, content: string, wantToMeet?: boolean, replyToId?: string }) {
  return API.mcpCall('naga_community', 'comment_post', {
    post_id: payload.postId,
    content: payload.content,
    want_to_meet: payload.wantToMeet || false,
    reply_to_id: payload.replyToId || undefined,
  })
}

export async function fetchMessages(page = 1, pageSize = 20) {
  const resp = await API.mcpCall('naga_community', 'get_messages', { page, page_size: pageSize })
  const r = parseResult(resp)
  return r?.data || r || { items: [], total: 0 }
}

export async function sendMessage(toUserId: string, content: string) {
  return API.mcpCall('naga_community', 'send_message', { to_user_id: toUserId, content })
}

export async function fetchFriendRequests() {
  const resp = await API.mcpCall('naga_community', 'get_friend_requests')
  const r = parseResult(resp)
  return r?.data || r || []
}

export async function acceptFriendRequest(id: string) {
  return API.mcpCall('naga_community', 'accept_friend', { request_id: id })
}

export async function declineFriendRequest(id: string) {
  return API.mcpCall('naga_community', 'decline_friend', { request_id: id })
}

export async function fetchConnections() {
  const resp = await API.mcpCall('naga_community', 'get_connections')
  return parseResult(resp)?.data || parseResult(resp) || []
}

export async function fetchNotifications() {
  const resp = await API.mcpCall('naga_community', 'get_notifications')
  return parseResult(resp)?.data || parseResult(resp) || []
}

export async function fetchProfile() {
  const resp = await API.mcpCall('naga_community', 'get_profile')
  return parseResult(resp)?.data || parseResult(resp)
}

export async function communityLogin(username: string, password: string, captchaId = '', captchaAnswer = '') {
  return API.mcpCall('naga_community', 'login', {
    username,
    password,
    captcha_id: captchaId,
    captcha_answer: captchaAnswer,
  })
}

export async function getCaptcha() {
  return API.mcpCall('naga_community', 'get_captcha')
}

export async function sendVerificationCode(email: string, username: string) {
  return API.mcpCall('naga_community', 'send_verification', { email, username })
}

export async function communityRegister(
  username: string,
  email: string,
  password: string,
  verificationCode: string,
) {
  return API.mcpCall('naga_community', 'register', {
    username,
    email,
    password,
    verification_code: verificationCode,
  })
}

export async function communityGetMe() {
  return API.mcpCall('naga_community', 'get_me')
}

export async function communityLogout() {
  return API.mcpCall('naga_community', 'logout')
}
