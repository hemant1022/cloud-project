import { Boxes, LockKeyhole, Mail, ShieldCheck, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiErrorMessage } from '../api'
import { useAuth } from '../auth/AuthContext'
import { ErrorBanner } from '../components/ui'

export default function Login() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-slate-900 p-10 text-white lg:flex">
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-brand-600 p-2.5">
            <Boxes className="h-6 w-6" />
          </span>
          <div>
            <p className="text-lg font-semibold">StockPilot</p>
            <p className="text-sm text-slate-400">Inventory Management</p>
          </div>
        </div>

        <div className="max-w-md space-y-6">
          <h1 className="text-3xl font-semibold leading-tight">
            Track every product, catch low stock early, and keep inventory value in view.
          </h1>
          <ul className="space-y-4 text-sm text-slate-300">
            <li className="flex gap-3">
              <TrendingUp className="mt-0.5 h-5 w-5 shrink-0 text-brand-100" />
              Live dashboard for total inventory value and stock health.
            </li>
            <li className="flex gap-3">
              <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-brand-100" />
              Role-based access for admins, managers, and viewers.
            </li>
            <li className="flex gap-3">
              <Boxes className="mt-0.5 h-5 w-5 shrink-0 text-brand-100" />
              CSV imports with admin approval for new categories and suppliers.
            </li>
          </ul>
        </div>

        <p className="text-xs text-slate-500">Inventory Management App · AWS EKS project</p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden">
            <span className="inline-flex rounded-xl bg-brand-600 p-2.5 text-white">
              <Boxes className="h-6 w-6" />
            </span>
            <h1 className="mt-4 text-2xl font-semibold">StockPilot</h1>
            <p className="text-sm text-slate-500">Sign in to manage inventory</p>
          </div>

          <div className="card p-6">
            <h2 className="text-xl font-semibold text-slate-900">Sign in</h2>
            <p className="mt-1 text-sm text-slate-500">Use the admin credentials from your environment file.</p>

            <form className="mt-6 space-y-4" onSubmit={submit}>
              <ErrorBanner message={error} />

              <div>
                <label className="label" htmlFor="email">
                  Email
                </label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    className="input pl-9"
                    placeholder="admin@inventory.local"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="label" htmlFor="password">
                  Password
                </label>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    id="password"
                    type="password"
                    required
                    autoComplete="current-password"
                    className="input pl-9"
                    placeholder="••••••••"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-xs text-slate-500">
            Credentials come from ADMIN_EMAIL and ADMIN_PASSWORD in your .env file.
          </p>
        </div>
      </div>
    </div>
  )
}
