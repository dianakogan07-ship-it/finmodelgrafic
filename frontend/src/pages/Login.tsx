import { FormEvent, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'

export default function Login() {
  const { user, login } = useAuth()
  const [l, setL] = useState('')
  const [p, setP] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try { await login(l.trim(), p) } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <section id="login" className="screen">
      <form className="login-card" onSubmit={submit}>
        <h1>СУЗ</h1>
        <div className="field"><label htmlFor="lg">Логин</label>
          <input id="lg" value={l} onChange={e => setL(e.target.value)} autoComplete="username" required /></div>
        <div className="field"><label htmlFor="pw">Пароль</label>
          <input id="pw" type="password" value={p} onChange={e => setP(e.target.value)} autoComplete="current-password" required /></div>
        {err && <p className="err" role="alert">{err}</p>}
        <button className="btn" type="submit" disabled={busy}>{busy ? 'Вход…' : 'Войти'}</button>
      </form>
    </section>
  )
}
