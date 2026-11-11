import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { loginRequest, TOKEN_KEY, USER_KEY } from '../api'
import type { AuthUser } from '../types'

interface AuthContextValue {
  token: string | null
  user: AuthUser | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  hasRole: (...roles: AuthUser['role'][]) => boolean
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

function readStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser())

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginRequest(email, password)
    localStorage.setItem(TOKEN_KEY, response.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(response.user))
    setToken(response.access_token)
    setUser(response.user)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const hasRole = useCallback(
    (...roles: AuthUser['role'][]) => Boolean(user && roles.includes(user.role)),
    [user],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      hasRole,
    }),
    [token, user, login, logout, hasRole],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return context
}
