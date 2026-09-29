import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import { api, setUnauthorizedHandler, token, User } from './api'

interface AuthCtx { user: User | null; ready: boolean; login: (l: string, p: string) => Promise<void>; logout: () => void }
const Ctx = createContext<AuthCtx>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)
  const logout = useCallback(() => { token.set(null); setUser(null) }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    if (!token.get()) { setReady(true); return }
    api.me().then(setUser).catch(() => token.set(null)).finally(() => setReady(true))
  }, [logout])

  const login = async (l: string, p: string) => {
    const r = await api.login(l, p)
    token.set(r.token)
    setUser(r.user)
  }
  return <Ctx.Provider value={{ user, ready, login, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
