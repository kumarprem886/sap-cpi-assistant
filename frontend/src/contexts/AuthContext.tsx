import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

export interface User {
  id: string
  email: string
  username: string
  full_name: string
  role: 'admin' | 'developer'
  is_active: boolean
  last_login: string | null
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, fullName: string, password: string) => Promise<void>
  logout: () => void
  updateUser: (u: User) => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]     = useState<User | null>(null)
  const [token, setToken]   = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Boot: restore from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('cpi_token')
    if (stored) {
      setToken(stored)
      axios.defaults.headers.common['Authorization'] = `Bearer ${stored}`
      axios.get('/api/auth/me')
        .then(r => setUser(r.data))
        .catch(() => {
          localStorage.removeItem('cpi_token')
          setToken(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const r = await axios.post('/api/auth/login', { email, password })
    const { access_token, user: u } = r.data
    localStorage.setItem('cpi_token', access_token)
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    setToken(access_token)
    setUser(u)
  }

  const register = async (email: string, username: string, full_name: string, password: string) => {
    const r = await axios.post('/api/auth/register', { email, username, full_name, password })
    const { access_token, user: u } = r.data
    localStorage.setItem('cpi_token', access_token)
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    setToken(access_token)
    setUser(u)
  }

  const logout = () => {
    localStorage.removeItem('cpi_token')
    delete axios.defaults.headers.common['Authorization']
    setToken(null)
    setUser(null)
  }

  const updateUser = (u: User) => setUser(u)

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, updateUser, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
