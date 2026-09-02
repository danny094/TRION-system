import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { fetchApi, fetchApiResponse, SESSION_LOST_EVENT, setCsrfToken } from '@/lib/api/client'
import { useTranslation } from '@/lib/i18n'
import type { AuthSession, AuthState, LoginRequest } from './contracts'
import './AuthGate.css'

export function AuthGate({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const [state, setState] = useState<AuthState>({ status: 'checking' })
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const acceptSession = useCallback((session: AuthSession) => {
    setCsrfToken(session.csrf_token)
    setState({ status: 'authenticated', session })
  }, [])

  useEffect(() => {
    let active = true
    fetchApi<AuthSession>('/auth/session')
      .then((session) => { if (active) acceptSession(session) })
      .catch(() => { if (active) setState({ status: 'anonymous' }) })
    const loseSession = () => {
      setCsrfToken(null)
      setState({ status: 'anonymous', message: t('auth.sessionExpired') })
    }
    window.addEventListener(SESSION_LOST_EVENT, loseSession)
    return () => {
      active = false
      window.removeEventListener(SESSION_LOST_EVENT, loseSession)
    }
  }, [acceptSession, t])

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    try {
      const request: LoginRequest = { password }
      const session = await fetchApi<AuthSession>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(request),
      })
      setPassword('')
      acceptSession(session)
    } catch {
      setState({ status: 'anonymous', message: t('auth.loginFailed') })
    } finally {
      setSubmitting(false)
    }
  }

  async function logout() {
    setSubmitting(true)
    try {
      await fetchApiResponse('/auth/logout', { method: 'POST' })
    } catch {
      setSubmitting(false)
      setState((current) => current.status === 'authenticated'
        ? { ...current, message: t('auth.logoutFailed') }
        : current)
      return
    }
    setSubmitting(false)
    setCsrfToken(null)
    setState({ status: 'anonymous' })
  }

  if (state.status === 'checking') {
    return <main className="auth-gate auth-gate--checking">{t('auth.checkingSession')}</main>
  }

  if (state.status === 'anonymous') {
    return (
      <main className="auth-gate">
        <form className="auth-card" onSubmit={login}>
          <div className="auth-mark" aria-hidden="true">T</div>
          <h1>{t('auth.loginTitle')}</h1>
          <p>{t('auth.loginDescription')}</p>
          <label htmlFor="trion-password">{t('auth.password')}</label>
          <input
            id="trion-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoFocus
          />
          {state.message ? <p className="auth-error" role="alert">{state.message}</p> : null}
          <button type="submit" disabled={submitting}>
            {submitting ? t('auth.loggingIn') : t('auth.login')}
          </button>
        </form>
      </main>
    )
  }

  return (
    <div className="auth-session">
      <div className="auth-session-bar">
        <span>{t('auth.signedInAs', { principal: state.session.principal })}</span>
        <button type="button" onClick={logout} disabled={submitting}>{t('auth.logout')}</button>
      </div>
      {state.message ? <p className="auth-error" role="alert">{state.message}</p> : null}
      {children}
    </div>
  )
}
