import { Link } from 'react-router-dom'
import { ReactNode } from 'react'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ minHeight: '100vh' }}>
      <header
        style={{
          background: 'var(--purple)',
          color: 'white',
          padding: '16px 32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Link to="/" style={{ color: 'white', textDecoration: 'none' }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', fontWeight: 700 }}>
            Best of Opera
          </h1>
          <span style={{ fontSize: '12px', opacity: 0.8 }}>APP2 — Content Module</span>
        </Link>
        <Link to="/new-project">
          <button className="btn-secondary">+ New Project</button>
        </Link>
      </header>
      <main style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px' }}>
        {children}
      </main>
    </div>
  )
}
