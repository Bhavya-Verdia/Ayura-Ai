import React, { useState, useRef } from 'react'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import { communityAPI } from '../api/client'
import { useAuth } from '../providers/AuthContext'
import { SkeletonCircle, SkeletonLine } from '../components/Skeleton'
import './Community.css'

// ─── Constants ────────────────────────────────────────────────────────────────
const PAGE_LIMIT = 10
const MAX_CHARS = 500
const WARN_CHARS = 450

const DOSHA_COLORS = [
  '#0D9488', // primary teal
  '#2DD4BF', // primary light
  '#F59E0B', // accent amber
  '#10B981', // sage
  '#F43F5E', // rose
  '#818CF8', // indigo
  '#FB923C', // orange
  '#34D399', // emerald
]

const WELLNESS_TAGS = [
  { keyword: /yoga|pranayam|stretch|breath/i, tag: '🧘 Yoga', color: 'var(--primary)' },
  { keyword: /diet|nutrition|food|eat|meal|recipe/i, tag: '🥗 Nutrition', color: 'var(--accent)' },
  { keyword: /meditat|mindful|calm|peace|zen/i, tag: '🧠 Mindfulness', color: '#818CF8' },
  { keyword: /sleep|rest|recover|insomn/i, tag: '😴 Sleep', color: '#60A5FA' },
  { keyword: /remedy|herb|ayurved|detox|cleanse/i, tag: '🌿 Ayurveda', color: 'var(--sage)' },
  { keyword: /gym|workout|exercise|fitness|run|cardio/i, tag: '🏋️ Fitness', color: 'var(--rose)' },
  { keyword: /stress|anxiety|relax|mood/i, tag: '💆 Wellness', color: '#A78BFA' },
  { keyword: /water|hydrat/i, tag: '💧 Hydration', color: '#38BDF8' },
]

// ─── Helpers ─────────────────────────────────────────────────────────────────
function hashColor(name = '') {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return DOSHA_COLORS[Math.abs(hash) % DOSHA_COLORS.length]
}

function getInitials(name = '') {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || '??'
}

function timeAgo(dateStr) {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.floor((now - then) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
  return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function detectTags(content = '') {
  return WELLNESS_TAGS.filter(({ keyword }) => keyword.test(content))
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────
function PostSkeleton() {
  return (
    <div className="comm-post-skeleton">
      <div className="comm-skeleton-header" style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
        <SkeletonCircle size="44px" />
        <div className="comm-skeleton-meta" style={{ flex: 1 }}>
          <SkeletonLine width="40%" height="14px" />
          <SkeletonLine width="25%" height="11px" style={{ marginTop: '6px' }} />
        </div>
      </div>
      <SkeletonLine width="100%" height="13px" style={{ marginTop: '16px' }} />
      <SkeletonLine width="85%" height="13px" style={{ marginTop: '8px' }} />
      <SkeletonLine width="60%" height="13px" style={{ marginTop: '8px' }} />
    </div>
  )
}

// ─── Post Card ─────────────────────────────────────────────────────────────────
function PostCard({ post, currentUserName, onLike, onDelete, onReport, index }) {
  const [likeAnimating, setLikeAnimating] = useState(false)
  const tags = detectTags(post.content)
  const avatarColor = hashColor(post.author_name)
  const isOwner = post.is_mine ?? (post.author_name === currentUserName)

  const handleLike = async () => {
    setLikeAnimating(true)
    onLike(post.id)
    setTimeout(() => setLikeAnimating(false), 500)
  }

  const handleDelete = () => {
    if (window.confirm('Delete this post? This action cannot be undone.')) {
      onDelete(post.id)
    }
  }

  const handleReport = () => onReport?.(post.id)

  return (
    <motion.div
      className="comm-post-card"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12, scale: 0.97 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: [0.16, 1, 0.3, 1] }}
      layout
    >
      {/* Gradient top border */}
      <div className="comm-post-top-border" />

      {/* Header */}
      <div className="comm-post-header">
        <div
          className="comm-post-avatar"
          style={{ '--avatar-color': avatarColor }}
        >
          {getInitials(post.author_name)}
        </div>
        <div className="comm-post-meta">
          <span className="comm-post-author">{post.author_name}</span>
          <span className="comm-post-time">{timeAgo(post.created_at)}</span>
        </div>
        {isOwner ? (
          <button
            className="comm-post-delete-btn"
            onClick={handleDelete}
            title="Delete post"
            aria-label="Delete post"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
              <path d="M10 11v6M14 11v6" />
              <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
            </svg>
          </button>
        ) : (
          <button
            className="comm-post-delete-btn"
            onClick={handleReport}
            disabled={post.reported_by_me}
            title={post.reported_by_me ? 'Reported' : 'Report post'}
            aria-label={post.reported_by_me ? 'Already reported' : 'Report post'}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill={post.reported_by_me ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
              <line x1="4" y1="22" x2="4" y2="15" />
            </svg>
          </button>
        )}
      </div>

      {/* Content */}
      <p className="comm-post-content">{post.content}</p>

      {/* Wellness tags */}
      {tags.length > 0 && (
        <div className="comm-post-tags">
          {tags.map(({ tag, color }) => (
            <span key={tag} className="comm-post-tag" style={{ '--tag-color': color }}>
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="comm-post-footer">
        <button
          className={`comm-like-btn${post.liked_by_me ? ' liked' : ''}${likeAnimating ? ' pulse' : ''}`}
          onClick={handleLike}
          aria-label={post.liked_by_me ? 'Unlike post' : 'Like post'}
        >
          <svg
            className="comm-heart-icon"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill={post.liked_by_me ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
          <span className="comm-like-count">{post.like_count}</span>
        </button>
      </div>
    </motion.div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function Community() {
  const { user } = useAuth()

  const queryClient = useQueryClient()

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: loading,
  } = useInfiniteQuery({
    queryKey: ['community-posts'],
    queryFn: async ({ pageParam = 0 }) => {
      const res = await communityAPI.list(pageParam, PAGE_LIMIT)
      return {
        posts: res.data || [],
        nextOffset: (res.data || []).length === PAGE_LIMIT ? pageParam + PAGE_LIMIT : null,
        totalCount: res.headers?.['x-total-count'] ? parseInt(res.headers['x-total-count'], 10) : null
      }
    },
    getNextPageParam: (lastPage) => lastPage.nextOffset,
    initialPageParam: 0
  })

  const posts = data?.pages.flatMap((page) => page.posts) || []
  const totalCount = data?.pages[0]?.totalCount ?? posts.length

  const [newContent, setNewContent]   = useState('')
  const [posting, setPosting]         = useState(false)
  const [postError, setPostError]     = useState('')

  const textareaRef = useRef(null)

  const handleLoadMore = () => fetchNextPage()

  // ── Create post ──────────────────────────────
  const createPostMutation = useMutation({
    mutationFn: communityAPI.create,
    onMutate: () => {
      setPosting(true)
      setPostError('')
    },
    onSuccess: (res) => {
      const created = res.data
      queryClient.setQueryData(['community-posts'], (oldData) => {
        if (!oldData) return oldData
        const firstPage = oldData.pages[0]
        return {
          ...oldData,
          pages: [
            {
              ...firstPage,
              posts: [created, ...firstPage.posts],
              totalCount: firstPage.totalCount != null ? firstPage.totalCount + 1 : null
            },
            ...oldData.pages.slice(1)
          ]
        }
      })
      setNewContent('')
      textareaRef.current?.focus()
    },
    onError: (err) => {
      setPostError(err.response?.data?.detail || 'Failed to post. Please try again.')
    },
    onSettled: () => setPosting(false)
  })

  // ── Create post ──────────────────────────────
  const handlePost = () => {
    const trimmed = newContent.trim()
    if (!trimmed || trimmed.length > MAX_CHARS) return
    createPostMutation.mutate(trimmed)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handlePost()
  }

  // ── Like (optimistic) ────────────────────────
  // ── Like (optimistic) ────────────────────────
  const likeMutation = useMutation({
    mutationFn: communityAPI.toggleLike,
    onMutate: async (postId) => {
      await queryClient.cancelQueries({ queryKey: ['community-posts'] })
      const previous = queryClient.getQueryData(['community-posts'])
      queryClient.setQueryData(['community-posts'], (old) => {
        if (!old) return old
        return {
          ...old,
          pages: old.pages.map(page => ({
            ...page,
            posts: page.posts.map(p =>
              p.id === postId
                ? { ...p, liked_by_me: !p.liked_by_me, like_count: p.liked_by_me ? p.like_count - 1 : p.like_count + 1 }
                : p
            )
          }))
        }
      })
      return { previous }
    },
    onError: (err, postId, context) => {
      if (context?.previous) queryClient.setQueryData(['community-posts'], context.previous)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['community-posts'] })
  })

  const handleLike = (postId) => likeMutation.mutate(postId)

  // ── Delete ───────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: communityAPI.remove,
    onMutate: async (postId) => {
      await queryClient.cancelQueries({ queryKey: ['community-posts'] })
      const previous = queryClient.getQueryData(['community-posts'])
      queryClient.setQueryData(['community-posts'], (old) => {
        if (!old) return old
        return {
          ...old,
          pages: old.pages.map(page => ({
            ...page,
            posts: page.posts.filter(p => p.id !== postId),
            totalCount: page.totalCount != null ? Math.max(0, page.totalCount - 1) : 0
          }))
        }
      })
      return { previous }
    },
    onError: (err, postId, context) => {
      if (context?.previous) queryClient.setQueryData(['community-posts'], context.previous)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['community-posts'] })
  })

  const handleDelete = (postId) => deleteMutation.mutate(postId)

  // ── Report ───────────────────────────────────
  const reportMutation = useMutation({
    mutationFn: (postId) => communityAPI.report(postId),
    onMutate: async (postId) => {
      await queryClient.cancelQueries({ queryKey: ['community-posts'] })
      const previous = queryClient.getQueryData(['community-posts'])
      queryClient.setQueryData(['community-posts'], (old) => {
        if (!old) return old
        return {
          ...old,
          pages: old.pages.map(page => ({
            ...page,
            posts: page.posts.map(p => p.id === postId ? { ...p, reported_by_me: true } : p),
          })),
        }
      })
      return { previous }
    },
    onError: (err, postId, context) => {
      if (context?.previous) queryClient.setQueryData(['community-posts'], context.previous)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['community-posts'] }),
  })

  const handleReport = (postId) => {
    if (window.confirm('Report this post to moderators? Posts flagged by several members are hidden pending review.')) {
      reportMutation.mutate(postId)
    }
  }

  const charCount = newContent.length
  const charOverLimit = charCount > MAX_CHARS
  const charNearLimit = charCount > WARN_CHARS && !charOverLimit
  const canPost = newContent.trim().length > 0 && !charOverLimit && !posting

  return (
    <>
      <Helmet>
        <title>Community — Ayura AI</title>
        <meta name="description" content="Connect with the Ayura wellness community. Share your journey, remedies, and tips." />
      </Helmet>

      <div className="comm-root">
        {/* Background ambient glows */}
        <div className="comm-bg-glow comm-bg-glow-1" />
        <div className="comm-bg-glow comm-bg-glow-2" />

        <div className="comm-container">

          {/* ── Page Header ── */}
          <motion.div
            className="comm-header"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="comm-header-left">
              <div className="comm-header-icon">🌿</div>
              <div>
                <h1 className="comm-title">
                  Wellness <span className="gradient-text">Community</span>
                </h1>
                <p className="comm-subtitle">
                  Share your journey, remedies &amp; healing stories
                </p>
              </div>
            </div>
            {totalCount > 0 && (
              <div className="comm-post-count-badge">
                <span>{totalCount}</span>
                <span className="comm-count-label">posts</span>
              </div>
            )}
          </motion.div>

          {/* ── Create Post ── */}
          <motion.div
            className="comm-create-card"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1 }}
          >
            <div className="comm-create-header">
              <div
                className="comm-create-avatar"
                style={{ '--avatar-color': hashColor(user?.name || '') }}
              >
                {getInitials(user?.name || '')}
              </div>
              <span className="comm-create-prompt">
                What's on your wellness mind, <strong>{user?.name?.split(' ')[0] || 'friend'}</strong>?
              </span>
            </div>

            <div className="comm-textarea-wrap">
              <textarea
                ref={textareaRef}
                className="comm-textarea"
                placeholder="Share a remedy, yoga tip, mindfulness insight, or wellness win… (Ctrl+Enter to post)"
                value={newContent}
                onChange={(e) => {
                  setNewContent(e.target.value)
                  setPostError('')
                }}
                onKeyDown={handleKeyDown}
                rows={4}
                maxLength={MAX_CHARS + 50}
                aria-label="New post content"
              />
              <div className={`comm-char-counter${charOverLimit ? ' over' : charNearLimit ? ' warn' : ''}`}>
                {charCount}/{MAX_CHARS}
              </div>
            </div>

            <AnimatePresence>
              {postError && (
                <motion.div
                  className="comm-post-error"
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  {postError}
                </motion.div>
              )}
            </AnimatePresence>

            <div className="comm-create-footer">
              <div className="comm-create-tips">
                <span className="comm-tip-pill">🧘 Yoga</span>
                <span className="comm-tip-pill">🌿 Remedies</span>
                <span className="comm-tip-pill">💡 Tips</span>
              </div>
              <button
                className="comm-post-btn"
                onClick={handlePost}
                disabled={!canPost}
              >
                {posting ? (
                  <>
                    <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', borderTopColor: '#fff' }} />
                    Posting…
                  </>
                ) : (
                  <>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="22" y1="2" x2="11" y2="13" />
                      <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                    Share
                  </>
                )}
              </button>
            </div>
          </motion.div>

          {/* ── Feed ── */}
          <div className="comm-feed">
            {loading ? (
              <>
                <PostSkeleton />
                <PostSkeleton />
                <PostSkeleton />
              </>
            ) : posts.length === 0 ? (
              <motion.div
                className="comm-empty-state"
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
              >
                <div className="comm-empty-icon">🌱</div>
                <h3 className="comm-empty-title">Be the first to share your wellness journey!</h3>
                <p className="comm-empty-sub">
                  The community is waiting. Share a remedy, yoga tip, or healing experience above.
                </p>
              </motion.div>
            ) : (
              <AnimatePresence mode="popLayout">
                {posts.map((post, i) => (
                  <PostCard
                    key={post.id}
                    post={post}
                    currentUserName={user?.name}
                    onLike={handleLike}
                    onDelete={handleDelete}
                    onReport={handleReport}
                    index={i}
                  />
                ))}
              </AnimatePresence>
            )}

            {/* Load More */}
            {!loading && hasNextPage && posts.length > 0 && (
              <motion.div
                className="comm-load-more-wrap"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <button
                  className="comm-load-more-btn"
                  onClick={handleLoadMore}
                  disabled={isFetchingNextPage}
                >
                  {isFetchingNextPage ? (
                    <>
                      <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />
                      Loading…
                    </>
                  ) : (
                    'Load more posts ↓'
                  )}
                </button>
              </motion.div>
            )}

            {!loading && !hasNextPage && posts.length > 0 && (
              <div className="comm-end-of-feed">
                <span>✦ You've reached the end of the feed ✦</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
