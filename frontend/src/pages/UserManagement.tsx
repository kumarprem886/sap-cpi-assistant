import { useState, useEffect, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, Plus, Trash2, KeyRound, Loader2, X, Check, ShieldAlert, UserCheck, UserX } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { usersAPI } from '../api/client'

interface UserRow {
  id: string
  email: string
  username: string
  full_name: string
  role: 'admin' | 'developer'
  is_active: boolean
  created_at: string | null
  last_login: string | null
}

function initials(u: UserRow) {
  if (u.full_name?.trim()) {
    const parts = u.full_name.trim().split(' ')
    return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
  }
  return u.username.slice(0, 2).toUpperCase()
}

function Avatar({ user }: { user: UserRow }) {
  const colors = [
    'bg-blue-700', 'bg-purple-700', 'bg-green-700',
    'bg-orange-700', 'bg-pink-700', 'bg-teal-700',
  ]
  const color = colors[user.username.charCodeAt(0) % colors.length]
  return (
    <div className={`w-8 h-8 rounded-full ${color} flex items-center justify-center text-xs font-bold text-white shrink-0`}>
      {initials(user)}
    </div>
  )
}

// ── Add User Modal ──────────────────────────────────────────────────────────────

interface AddUserModalProps {
  onClose: () => void
  onCreated: (u: UserRow) => void
}

function AddUserModal({ onClose, onCreated }: AddUserModalProps) {
  const [email, setEmail]       = useState('')
  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole]         = useState<'developer' | 'admin'>('developer')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const r = await usersAPI.create({ email, username, full_name: fullName, password, role })
      onCreated(r.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to create user')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-white text-base">Add New User</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white p-1 rounded">
            <X size={16} />
          </button>
        </div>

        {error && (
          <div className="mb-4 px-3 py-2.5 bg-red-900/30 border border-red-800/60 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Email</label>
              <input type="email" className="input-field text-sm" placeholder="user@example.com"
                value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            <div>
              <label className="label">Username</label>
              <input type="text" className="input-field text-sm" placeholder="johndoe"
                value={username} onChange={e => setUsername(e.target.value)} required />
            </div>
          </div>
          <div>
            <label className="label">Full Name <span className="text-gray-600 font-normal">(optional)</span></label>
            <input type="text" className="input-field text-sm" placeholder="John Doe"
              value={fullName} onChange={e => setFullName(e.target.value)} />
          </div>
          <div>
            <label className="label">Password</label>
            <input type="password" className="input-field text-sm" placeholder="At least 6 characters"
              value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <div>
            <label className="label">Role</label>
            <select className="select-field text-sm" value={role}
              onChange={e => setRole(e.target.value as 'developer' | 'admin')}>
              <option value="developer">Developer</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex gap-2 pt-1">
            <button type="submit" disabled={loading}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors">
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              Create User
            </button>
            <button type="button" onClick={onClose}
              className="px-3 py-2 text-sm text-gray-400 hover:text-white transition-colors ml-auto">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Reset Password Modal ────────────────────────────────────────────────────────

interface ResetPasswordModalProps {
  user: UserRow
  onClose: () => void
}

function ResetPasswordModal({ user, onClose }: ResetPasswordModalProps) {
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [done, setDone]         = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await usersAPI.resetPassword(user.id, password)
      setDone(true)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-sm shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-white text-base">Reset Password</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white p-1 rounded">
            <X size={16} />
          </button>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          Setting new password for <span className="text-white font-medium">{user.username}</span>
        </p>

        {done ? (
          <div className="flex items-center gap-2 px-3 py-3 bg-green-900/30 border border-green-800/60 rounded-lg text-green-300 text-sm">
            <Check size={14} className="shrink-0" />
            Password reset successfully.
          </div>
        ) : (
          <>
            {error && (
              <div className="mb-4 px-3 py-2.5 bg-red-900/30 border border-red-800/60 rounded-lg text-red-300 text-sm">
                {error}
              </div>
            )}
            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="label">New Password</label>
                <input type="password" className="input-field text-sm" placeholder="At least 6 characters"
                  value={password} onChange={e => setPassword(e.target.value)} required autoFocus />
              </div>
              <div className="flex gap-2 pt-1">
                <button type="submit" disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors">
                  {loading ? <Loader2 size={14} className="animate-spin" /> : <KeyRound size={14} />}
                  Reset
                </button>
                <button type="button" onClick={onClose}
                  className="px-3 py-2 text-sm text-gray-400 hover:text-white transition-colors ml-auto">
                  Close
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

// ── Main page ───────────────────────────────────────────────────────────────────

export default function UserManagement() {
  const { user: me } = useAuth()
  const navigate = useNavigate()

  const [users, setUsers]           = useState<UserRow[]>([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState('')
  const [showAdd, setShowAdd]       = useState(false)
  const [resetTarget, setResetTarget] = useState<UserRow | null>(null)
  const [updatingId, setUpdatingId] = useState<string | null>(null)

  // Redirect non-admins
  useEffect(() => {
    if (me && me.role !== 'admin') {
      navigate('/', { replace: true })
    }
  }, [me, navigate])

  useEffect(() => {
    if (!me || me.role !== 'admin') return
    setLoading(true)
    usersAPI.list()
      .then(r => setUsers(r.data))
      .catch(err => setError(err?.response?.data?.detail ?? 'Failed to load users'))
      .finally(() => setLoading(false))
  }, [me])

  const handleToggleActive = async (u: UserRow) => {
    setUpdatingId(u.id)
    try {
      const r = await usersAPI.update(u.id, { is_active: !u.is_active })
      setUsers(prev => prev.map(x => x.id === u.id ? r.data : x))
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Update failed')
    } finally {
      setUpdatingId(null)
    }
  }

  const handleRoleChange = async (u: UserRow, role: string) => {
    setUpdatingId(u.id)
    try {
      const r = await usersAPI.update(u.id, { role })
      setUsers(prev => prev.map(x => x.id === u.id ? r.data : x))
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Update failed')
    } finally {
      setUpdatingId(null)
    }
  }

  const handleDelete = async (u: UserRow) => {
    if (!window.confirm(`Delete user "${u.username}"? This cannot be undone.`)) return
    setUpdatingId(u.id)
    try {
      await usersAPI.delete(u.id)
      setUsers(prev => prev.filter(x => x.id !== u.id))
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Delete failed')
    } finally {
      setUpdatingId(null)
    }
  }

  if (!me || me.role !== 'admin') return null

  const formatDate = (d: string | null) => {
    if (!d) return '—'
    return new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-900/40 flex items-center justify-center">
            <Users size={20} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">User Management</h1>
            <p className="text-xs text-gray-500">
              {users.length} {users.length === 1 ? 'user' : 'users'} registered
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus size={15} />
          Add User
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-900/30 border border-red-800/60 rounded-lg text-red-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-200 ml-3">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500">
            <Loader2 size={20} className="animate-spin mr-2" />
            Loading users…
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-600">
            <Users size={32} className="mb-3 opacity-40" />
            <p className="text-sm">No users yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wide">User</th>
                  <th className="px-4 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Username</th>
                  <th className="px-4 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Role</th>
                  <th className="px-4 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Last Login</th>
                  <th className="px-4 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wide text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {users.map(u => {
                  const isMe = u.id === me.id
                  const busy = updatingId === u.id
                  return (
                    <tr key={u.id} className={`transition-colors hover:bg-gray-800/40 ${!u.is_active ? 'opacity-60' : ''}`}>
                      {/* Name / Email */}
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <Avatar user={u} />
                          <div>
                            <p className="text-white font-medium leading-tight">
                              {u.full_name || u.username}
                              {isMe && (
                                <span className="ml-2 text-xs bg-blue-900/50 text-blue-300 border border-blue-800 px-1.5 py-0.5 rounded-full">you</span>
                              )}
                            </p>
                            <p className="text-gray-500 text-xs leading-tight mt-0.5">{u.email}</p>
                          </div>
                        </div>
                      </td>

                      {/* Username */}
                      <td className="px-4 py-3.5 text-gray-400 font-mono text-xs">{u.username}</td>

                      {/* Role */}
                      <td className="px-4 py-3.5">
                        {busy ? (
                          <Loader2 size={14} className="animate-spin text-gray-500" />
                        ) : (
                          <select
                            className="bg-gray-800 border border-gray-700 rounded-md px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-blue-500 disabled:opacity-50"
                            value={u.role}
                            disabled={isMe}
                            title={isMe ? "You can't change your own role" : undefined}
                            onChange={e => handleRoleChange(u, e.target.value)}
                          >
                            <option value="developer">Developer</option>
                            <option value="admin">Admin</option>
                          </select>
                        )}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5">
                        <button
                          onClick={() => handleToggleActive(u)}
                          disabled={isMe || busy}
                          title={isMe ? "You can't deactivate yourself" : u.is_active ? 'Deactivate' : 'Activate'}
                          className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                            u.is_active
                              ? 'bg-green-900/30 border-green-800 text-green-300 hover:bg-red-900/30 hover:border-red-800 hover:text-red-300'
                              : 'bg-red-900/30 border-red-800 text-red-300 hover:bg-green-900/30 hover:border-green-800 hover:text-green-300'
                          }`}
                        >
                          {u.is_active ? <UserCheck size={11} /> : <UserX size={11} />}
                          {u.is_active ? 'Active' : 'Disabled'}
                        </button>
                      </td>

                      {/* Last Login */}
                      <td className="px-4 py-3.5 text-gray-500 text-xs whitespace-nowrap">{formatDate(u.last_login)}</td>

                      {/* Actions */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => setResetTarget(u)}
                            title="Reset password"
                            className="p-1.5 rounded-md text-gray-500 hover:text-blue-400 hover:bg-blue-900/30 transition-colors"
                          >
                            <KeyRound size={14} />
                          </button>
                          <button
                            onClick={() => handleDelete(u)}
                            disabled={isMe || busy}
                            title={isMe ? "You can't delete yourself" : 'Delete user'}
                            className="p-1.5 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-900/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Admin note */}
      {users.length > 0 && (
        <div className="mt-4 flex items-start gap-2 text-xs text-gray-600">
          <ShieldAlert size={13} className="shrink-0 mt-0.5 text-gray-700" />
          <span>Role and status changes take effect immediately. Users will need to log in again for role changes to reflect in their session.</span>
        </div>
      )}

      {/* Modals */}
      {showAdd && (
        <AddUserModal
          onClose={() => setShowAdd(false)}
          onCreated={u => { setUsers(prev => [...prev, u]); setShowAdd(false) }}
        />
      )}
      {resetTarget && (
        <ResetPasswordModal
          user={resetTarget}
          onClose={() => setResetTarget(null)}
        />
      )}
    </div>
  )
}
