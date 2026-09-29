import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ObjectNode } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useToast } from '../lib/toast'

export default function Monitor() {
  const [nodes, setNodes] = useState<ObjectNode[]>([])
  const { logout } = useAuth()
  const toast = useToast()
  const nav = useNavigate()

  useEffect(() => { api.objects().then(setNodes).catch(e => toast(e.message)) }, [toast])

  const soon = () => toast('Вне первой итерации')
  return (
    <section id="monitor" className="screen">
      <nav className="topnav">
        <button onClick={soon}>Учетные записи</button>
        <button onClick={soon}>Проекты конкурентов</button>
        <button onClick={soon}>Внутренние объекты</button>
        <button className="on">Мониторинг</button>
        <button className="exit" onClick={logout} aria-label="Выйти" title="Выйти">⇥</button>
      </nav>
      <div className="orbit">
        <div className="orbit-center">СПИСОК<br />ОБЪЕКТОВ</div>
        {nodes.map(nd => {
          const r = 38, rad = ((nd.angle - 90) * Math.PI) / 180
          return (
            <div key={nd.id} className={'node' + (nd.has_dashboard || nd.tag ? ' active' : '')}
              style={{ left: `${50 + r * Math.cos(rad)}%`, top: `${50 + r * Math.sin(rad)}%` }}>
              <button onClick={() => (nd.has_dashboard ? nav(`/projects/${nd.id}`) : toast(`«${nd.name}» — нет модели`))}>
                <span className={`ball ${nd.style}`} /><span className="nm">{nd.name}</span>
              </button>
              {nd.tag && <span className="tag">{nd.tag}</span>}
            </div>
          )
        })}
      </div>
    </section>
  )
}
