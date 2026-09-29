import { createContext, ReactNode, useCallback, useContext, useRef, useState } from 'react'

const Ctx = createContext<(msg: string) => void>(() => {})

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<string | null>(null)
  const timer = useRef<number>()
  const show = useCallback((m: string) => {
    setMsg(m)
    clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setMsg(null), 2600)
  }, [])
  return (
    <Ctx.Provider value={show}>
      {children}
      {msg && <div id="toast" role="status">{msg}</div>}
    </Ctx.Provider>
  )
}

export const useToast = () => useContext(Ctx)
