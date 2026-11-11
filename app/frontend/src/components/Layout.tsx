import {
  Bell,
  Boxes,
  CheckSquare,
  LayoutDashboard,
  LogOut,
  Package,
  Tags,
  Upload,
} from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { useAuth } from '../auth/AuthContext'
import type { Role } from '../types'
import { Badge } from './ui'

interface NavItem {
  to: string
  label: string
  icon: typeof LayoutDashboard
  roles: Role[]
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'manager', 'viewer'] },
  { to: '/products', label: 'Products', icon: Package, roles: ['admin', 'manager', 'viewer'] },
  { to: '/alerts', label: 'Alerts', icon: Bell, roles: ['admin', 'manager', 'viewer'] },
  { to: '/import', label: 'Import CSV', icon: Upload, roles: ['admin', 'manager'] },
  { to: '/approvals', label: 'Approvals', icon: CheckSquare, roles: ['admin'] },
  { to: '/catalog', label: 'Catalog', icon: Tags, roles: ['admin', 'manager'] },
]

export default function Layout() {
  const { user, logout, hasRole } = useAuth()
  const navigate = useNavigate()

  const visibleItems = navItems.filter((item) => hasRole(...item.roles))

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    clsx(
      'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition',
      isActive
        ? 'bg-brand-50 text-brand-700'
        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
    )

  return (
    <div className="min-h-screen md:flex">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white px-4 py-5 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <span className="rounded-lg bg-brand-600 p-2 text-white">
            <Boxes className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">StockPilot</p>
            <p className="text-xs text-slate-500">Inventory Management</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {visibleItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={navLinkClass}>
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-4 border-t border-slate-200 pt-4">
          <p className="truncate px-2 text-xs text-slate-500">{user?.email}</p>
          <div className="mt-2 px-2">
            <Badge tone={user?.role === 'admin' ? 'brand' : user?.role === 'manager' ? 'blue' : 'slate'}>
              {user?.role}
            </Badge>
          </div>
          <button type="button" onClick={handleLogout} className="btn-secondary mt-3 w-full">
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-8">
          <div className="flex items-center gap-2 md:hidden">
            <span className="rounded-lg bg-brand-600 p-1.5 text-white">
              <Boxes className="h-4 w-4" />
            </span>
            <span className="text-sm font-semibold">StockPilot</span>
          </div>
          <p className="hidden text-sm text-slate-500 md:block">
            {user ? `Signed in as ${user.email}` : ''}
          </p>
          <div className="flex items-center gap-2">
            <button type="button" onClick={handleLogout} className="btn-secondary md:hidden">
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </header>

        <nav className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-white px-3 py-2 md:hidden">
          {visibleItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={navLinkClass}>
              <item.icon className="h-4 w-4" />
              <span className="whitespace-nowrap">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
