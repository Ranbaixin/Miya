export type SortMode = 'all' | 'hot' | 'latest'
export type TimeOrder = 'desc' | 'asc'
export type ForumFeedMode = 'casual' | 'story'

export interface ForumAuthor {
  id: string
  name: string
  avatar: string
  level?: number
  bio?: string
}

export interface ForumComment {
  id: string
  postId: string
  authorId: string
  authorType: string
  content: string
  images: string[]
  likesCount: number
  wantToMeet: boolean
  replyToId: string | null
  createdAt: string
  author: ForumAuthor
  liked: boolean
}

export interface ForumPost {
  id: string
  title: string
  content: string
  tags: string[]
  images: string[]
  boardId?: string | null
  boardIds?: string[]
  boards?: ForumBoard[]
  authorId: string
  authorType: string
  source: string | null
  likesCount: number
  commentsCount: number
  sharesCount: number
  viewCount: number
  pinned: boolean
  moderationStatus?: 'pending_review' | 'approved' | 'rejected'
  moderationScore?: number
  moderationReason?: string | null
  moderationCategories?: string[]
  moderationUpdatedAt?: string
  visibilityStatus?: 'visible' | 'hidden'
  createdAt: string
  updatedAt: string
  author: ForumAuthor
  liked: boolean
}

export interface ForumPostDetail extends ForumPost {
  commentList: ForumComment[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export interface ForumBoard {
  id: string
  name: string
  slug: string
  description: string
  sortOrder: number
  postCount: number
  createdAt: string
  updatedAt: string
}


