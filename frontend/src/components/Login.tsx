import { useState } from 'react'
import '../styles/Login.css'

interface LoginProps {
  onLogin: () => void
}

export default function Login({ onLogin }: LoginProps) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password }),
        credentials: 'include', // Important for cookies
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Login failed')
      }

      // Login successful
      onLogin()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Restaurant Voice Agent</h1>
        <h2>Dashboard Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              disabled={loading}
              autoFocus
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading || !password}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        <p className="hint">
          Default password: <code>admin123</code> (change in .env)
        </p>
      </div>
    </div>
  )
}
