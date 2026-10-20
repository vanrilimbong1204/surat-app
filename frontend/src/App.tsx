import { NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Register from './pages/Register'
import Upload from './pages/Upload'
import LetterPage from './pages/LetterPage'
import Threads from './pages/Threads'
import Settings from './pages/Settings'

const NAV = [
  { to: '/', label: 'Beranda', icon: '◧' },
  { to: '/surat', label: 'Register', icon: '☰' },
  { to: '/unggah', label: 'Unggah', icon: '+', primary: true },
  { to: '/benang', label: 'Benang', icon: '⟟' },
  { to: '/pengaturan', label: 'Pengaturan', icon: '⚙' },
]

export default function App() {
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <img src="/favicon.svg" alt="" />
          <div>
            <div className="brand-name">Arsip Surat</div>
            <div className="brand-sub">masuk · keluar · benang</div>
          </div>
        </div>
        <nav>
          {NAV.map(n => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `nav ${isActive ? 'on' : ''} ${n.primary ? 'nav-primary' : ''}`}>
              <span className="nav-ic">{n.icon}</span>{n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/surat" element={<Register />} />
          <Route path="/surat/:id" element={<LetterPage />} />
          <Route path="/unggah" element={<Upload />} />
          <Route path="/benang" element={<Threads />} />
          <Route path="/pengaturan" element={<Settings />} />
        </Routes>
      </main>
      <nav className="tabbar">
        {NAV.map(n => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `tab ${isActive ? 'on' : ''} ${n.primary ? 'tab-primary' : ''}`}>
            <span className="tab-ic">{n.icon}</span><span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
