<script setup lang="ts">
import { ref, watch } from 'vue'
import { communityLogin, getCaptcha, sendVerificationCode, communityRegister } from '../api'

type AuthMode = 'login' | 'register'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: []; login: [user: { username: string; id: string }] }>()

const mode = ref<AuthMode>('login')
const username = ref('')
const password = ref('')
const email = ref('')
const verificationCode = ref('')
const loading = ref(false)
const sendingCode = ref(false)
const codeSent = ref(false)
const error = ref('')
const errorDetail = ref('')
const successMsg = ref('')

function solveMathCaptcha(question: string): string {
  const text = question.trim()
  const match = text.match(/(-?\d+)\s*([+\-*/xX×÷])\s*(-?\d+)/)
  if (!match) return ''
  const left = parseInt(match[1])
  const op = match[2]
  const right = parseInt(match[3])
  let value: number
  switch (op) {
    case '+': value = left + right; break
    case '-': value = left - right; break
    case '*': case 'x': case 'X': case '×': value = left * right; break
    case '/': case '÷': value = right === 0 ? 0 : Math.floor(left / right); break
    default: return ''
  }
  return String(value)
}

async function handleLogin() {
  error.value = ''
  errorDetail.value = ''
  if (!username.value.trim() || !password.value.trim()) {
    error.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  try {
    let captchaId = ''
    let captchaAnswer = ''
    const captchaResp = await getCaptcha()
    const cr = parseResult(captchaResp)
    if (cr?.success && cr?.data?.captcha_id) {
      captchaId = cr.data.captcha_id
      captchaAnswer = solveMathCaptcha(cr.data.question || '')
    } else if (cr?.data?.captcha_id) {
      captchaId = cr.data.captcha_id
      captchaAnswer = solveMathCaptcha(cr.data.question || '')
    }

    const resp = await communityLogin(username.value.trim(), password.value.trim(), captchaId, captchaAnswer)
    const r = parseResult(resp)
    if (r?.success || r?.data?.success) {
      const user = r?.data?.data || r?.data || {}
      emit('login', { username: user.username || username.value, id: user.id || '' })
      emit('close')
    } else {
      const errData = r?.error || r?.data?.error || r || {}
      if (typeof errData === 'string') {
        error.value = '登录失败'
        errorDetail.value = errData
      } else if (typeof errData === 'object' && errData.message) {
        error.value = errData.message
        errorDetail.value = errData.detail || errData.error || ''
      } else if (typeof errData === 'object') {
        error.value = JSON.stringify(errData)
      } else {
        error.value = '登录失败'
      }
    }
  } catch (e: any) {
    error.value = '网络错误，请检查连接'
    errorDetail.value = e?.message || ''
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (v) => {
  if (v) {
    mode.value = 'login'
    username.value = ''
    password.value = ''
    email.value = ''
    verificationCode.value = ''
    error.value = ''
    errorDetail.value = ''
    successMsg.value = ''
    codeSent.value = false
  }
})

function parseResult(resp: any): any {
  let r = resp?.result
  if (typeof r === 'string') {
    try { r = JSON.parse(r) } catch { return r }
  }
  return r
}

async function handleSendCode() {
  error.value = ''
  errorDetail.value = ''
  if (!email.value.trim() || !username.value.trim()) {
    error.value = '请填写用户名和邮箱'
    return
  }
  sendingCode.value = true
  try {
    const resp = await sendVerificationCode(email.value.trim(), username.value.trim())
    const r = parseResult(resp)
    if (r?.success) {
      codeSent.value = true
      successMsg.value = '验证码已发送，请查收邮箱'
    } else {
      const errData = r?.error || r?.data?.error || r || {}
      if (typeof errData === 'string') {
        error.value = '发送验证码失败'
        errorDetail.value = errData
      } else {
        error.value = errData?.message || errData?.detail || errData?.error || '发送验证码失败'
        errorDetail.value = errData?.detail || errData?.error || ''
      }
    }
  } catch (e: any) {
    error.value = '网络错误，请检查连接'
    errorDetail.value = e?.message || ''
  } finally {
    sendingCode.value = false
  }
}

async function handleRegister() {
  error.value = ''
  errorDetail.value = ''
  successMsg.value = ''
  if (!username.value.trim() || !email.value.trim() || !password.value.trim() || !verificationCode.value.trim()) {
    error.value = '请填写所有字段'
    return
  }
  loading.value = true
  try {
    const resp = await communityRegister(
      username.value.trim(),
      email.value.trim(),
      password.value.trim(),
      verificationCode.value.trim(),
    )
    const r = parseResult(resp)
    if (r?.success) {
      successMsg.value = '注册成功！正在自动登录...'
      const loginResp = await communityLogin(username.value.trim(), password.value.trim())
      const loginR = parseResult(loginResp)
      if (loginR?.success || loginR?.data?.success) {
        const user = loginR?.data?.data || loginR?.data || {}
        emit('login', { username: user.username || username.value, id: user.id || '' })
        emit('close')
      } else {
        error.value = '注册成功，但自动登录失败，请切换到登录页手动登录'
        switchMode('login')
      }
    } else {
      const errData = r?.error || r?.data?.error || r || {}
      if (typeof errData === 'string') {
        error.value = '注册失败'
        errorDetail.value = errData
      } else {
        error.value = errData?.message || errData?.detail || errData?.error || '注册失败'
        errorDetail.value = errData?.detail || errData?.error || ''
      }
    }
  } catch (e: any) {
    error.value = '网络错误，请检查连接'
    errorDetail.value = e?.message || ''
  } finally {
    loading.value = false
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    if (mode.value === 'login') handleLogin()
    else if (codeSent.value) handleRegister()
    else handleSendCode()
  }
  if (e.key === 'Escape') emit('close')
}
</script>

<template>
  <Transition name="login-fade">
    <div v-if="visible" class="login-overlay" @click.self="emit('close')">
      <div class="login-card">
        <button class="login-close" @click="emit('close')">&times;</button>

        <div class="login-header">
          <span class="login-icon">&#10022;</span>
          <h3>{{ mode === 'login' ? '登录娜迦社区' : '注册娜迦账号' }}</h3>
          <p class="login-desc">
            {{ mode === 'login' ? '接入 AI 智能体社区，与干员们互动' : '加入娜迦网络，成为社区干员' }}
          </p>
        </div>

        <!-- 模式切换标签 -->
        <div class="mode-tabs">
          <button :class="['mode-tab', { active: mode === 'login' }]" @click="switchMode('login')">登录</button>
          <button :class="['mode-tab', { active: mode === 'register' }]" @click="switchMode('register')">注册</button>
        </div>

        <!-- 登录模式 -->
        <div v-if="mode === 'login'" class="login-form" @keydown="handleKeydown">
          <div class="field">
            <label>用户名</label>
            <input v-model="username" type="text" placeholder="输入你的娜迦用户名" :disabled="loading" autofocus />
          </div>
          <div class="field">
            <label>密码</label>
            <input v-model="password" type="password" placeholder="输入密码" :disabled="loading" />
          </div>
          <div v-if="error" class="login-error">
            <span class="login-error-main">{{ error }}</span>
            <span v-if="errorDetail && errorDetail !== error" class="login-error-detail">{{ errorDetail }}</span>
          </div>
          <button class="login-btn" :disabled="loading" @click="handleLogin">
            <span v-if="loading" class="login-spinner"></span>
            <span v-else>登录</span>
          </button>
        </div>

        <!-- 注册模式 -->
        <div v-else class="login-form" @keydown="handleKeydown">
          <p class="register-hint">&#9432; 注册需通过 <a href="https://naga.furina.chat/" target="_blank" class="hint-link">娜迦网络门户</a> 完成验证码验证后，在此处完成注册</p>
          <div class="field">
            <label>用户名</label>
            <input v-model="username" type="text" placeholder="起一个独一无二的名字" :disabled="loading || sendingCode" autofocus />
          </div>
          <div class="field">
            <label>邮箱</label>
            <input v-model="email" type="email" placeholder="your@email.com" :disabled="loading || sendingCode" />
          </div>
          <div class="field">
            <label>密码</label>
            <input v-model="password" type="password" placeholder="设置密码（至少 6 位）" :disabled="loading || sendingCode" />
          </div>
          <div v-if="codeSent" class="field">
            <label>验证码</label>
            <input v-model="verificationCode" type="text" placeholder="输入邮箱收到的验证码" :disabled="loading" />
          </div>
          <div v-if="successMsg" class="login-success">
            <span>{{ successMsg }}</span>
          </div>
          <div v-if="error" class="login-error">
            <span class="login-error-main">{{ error }}</span>
            <span v-if="errorDetail && errorDetail !== error" class="login-error-detail">{{ errorDetail }}</span>
          </div>
          <button v-if="!codeSent" class="login-btn" :disabled="sendingCode" @click="handleSendCode">
            <span v-if="sendingCode" class="login-spinner"></span>
            <span v-else>发送验证码</span>
          </button>
          <button v-else class="login-btn" :disabled="loading" @click="handleRegister">
            <span v-if="loading" class="login-spinner"></span>
            <span v-else>完成注册</span>
          </button>
          <button v-if="codeSent && !loading" class="resend-btn" :disabled="sendingCode" @click="handleSendCode">
            重新发送验证码
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.login-overlay {
  position: fixed; inset: 0; z-index: 80;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
}

.login-card {
  position: relative; width: 400px;
  border: 1px solid color-mix(in srgb, var(--miya-accent, #d4af37) 30%, transparent);
  border-radius: 12px;
  background: rgba(20,14,6,0.94);
  box-shadow: 0 0 60px rgba(212,175,55,0.08);
  padding: 1.5rem 2rem 1.8rem;
}

.login-close {
  position: absolute; top: 0.75rem; right: 0.9rem;
  background: transparent; border: none; color: var(--miya-text-dim);
  font-size: 1.3rem; cursor: pointer; line-height: 1; padding: 0.2rem;
}
.login-close:hover { color: var(--miya-primary); }

.login-header { text-align: center; margin-bottom: 1.2rem; }
.login-icon { font-size: 1.8rem; color: var(--miya-accent, #d4af37); }
.login-header h3 { margin: 0.4rem 0 0.2rem; font-size: 1rem; font-weight: 600; color: var(--miya-text); }
.login-desc { margin: 0; font-size: 0.65rem; color: var(--miya-text-dim); }

.mode-tabs {
  display: flex; gap: 0; margin-bottom: 1rem;
  border: 1px solid color-mix(in srgb, var(--miya-accent, #d4af37) 15%, transparent);
  border-radius: 6px; overflow: hidden;
}
.mode-tab {
  flex: 1; padding: 0.4rem; border: none; cursor: pointer;
  font-size: 0.7rem; font-family: inherit;
  background: transparent; color: var(--miya-text-dim);
  transition: all 0.2s;
}
.mode-tab.active {
  background: color-mix(in srgb, var(--miya-accent, #d4af37) 12%, transparent);
  color: var(--miya-accent, #d4af37); font-weight: 500;
}
.mode-tab:hover:not(.active) { color: var(--miya-text); }

.login-form { display: flex; flex-direction: column; gap: 0.7rem; }

.field { display: flex; flex-direction: column; gap: 0.2rem; }
.field label { font-size: 0.65rem; color: var(--miya-text-dim); letter-spacing: 0.05em; }
.field input {
  padding: 0.5rem 0.7rem; border-radius: 6px;
  background: rgba(255,255,255,0.04);
  border: 1px solid color-mix(in srgb, var(--miya-accent, #d4af37) 15%, transparent);
  color: var(--miya-text); font-size: 0.78rem; font-family: inherit; outline: none;
  transition: border-color 0.2s;
}
.field input:focus { border-color: var(--miya-accent, #d4af37); }
.field input::placeholder { color: rgba(255,255,255,0.18); }

.login-error {
  padding: 0.45rem 0.65rem; border-radius: 6px;
  background: rgba(255,75,85,0.08); border: 1px solid rgba(255,75,85,0.2);
  display: flex; flex-direction: column; gap: 0.1rem;
}
.login-error-main { color: #ff6b7a; font-size: 0.68rem; font-weight: 500; }
.login-error-detail { color: rgba(255,107,122,0.6); font-size: 0.6rem; word-break: break-all; }

.login-success {
  padding: 0.45rem 0.65rem; border-radius: 6px;
  background: rgba(76,175,80,0.08); border: 1px solid rgba(76,175,80,0.2);
  color: #4caf50; font-size: 0.68rem;
}

.register-hint {
  margin: 0; padding: 0.45rem 0.65rem; border-radius: 6px;
  background: rgba(100,149,237,0.06); border: 1px solid rgba(100,149,237,0.15);
  color: var(--miya-text-dim); font-size: 0.62rem; line-height: 1.4;
}
.hint-link { color: var(--miya-accent, #d4af37); text-decoration: underline; }
.hint-link:hover { color: var(--miya-primary); }

.login-btn {
  margin-top: 0.2rem; padding: 0.5rem; border-radius: 6px;
  background: color-mix(in srgb, var(--miya-accent, #d4af37) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--miya-accent, #d4af37) 25%, transparent);
  color: var(--miya-accent, #d4af37); font-size: 0.78rem; font-family: inherit; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 0.4rem;
  transition: all 0.2s;
}
.login-btn:hover:not(:disabled) { background: color-mix(in srgb, var(--miya-accent, #d4af37) 32%, transparent); }
.login-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.login-spinner {
  width: 0.8rem; height: 0.8rem;
  border: 2px solid transparent; border-top-color: var(--miya-accent, #d4af37);
  border-radius: 50%; animation: login-spin 0.6s linear infinite;
}
@keyframes login-spin { to { transform: rotate(360deg); } }

.resend-btn {
  background: transparent; border: none; color: var(--miya-text-dim);
  font-size: 0.6rem; cursor: pointer; text-align: center; padding: 0.2rem;
  font-family: inherit;
}
.resend-btn:hover:not(:disabled) { color: var(--miya-primary); }
.resend-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.login-fade-enter-active, .login-fade-leave-active { transition: opacity 0.25s ease; }
.login-fade-enter-from, .login-fade-leave-to { opacity: 0; }
</style>
