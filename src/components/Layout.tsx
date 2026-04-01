import { Outlet } from 'react-router-dom'
import { Nav } from './Nav'
import { Footer } from './Footer'
import { AIAssistant } from './AIAssistant'

export function Layout() {
  return (
    <div className="app-shell">
      <Nav />
      <main className="app-main">
        <Outlet />
      </main>
      <Footer />
      <AIAssistant />
    </div>
  )
}
