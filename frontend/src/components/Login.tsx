import { useState } from 'react'
import { getCookie, setCookie } from '../cookies'
import { getSessions } from '../api'  // ➕ 新增导入

type Props = { onLogin: (token: string, name?: string) => void; onGoRegister: () => void; }

export default function Login({ onLogin, onGoRegister }: Props) {
  const [token, setToken] = useState(getCookie('identity_token') || '')
  const [error, setError] = useState<string | null>(null)   // ➕ 错误状态
  const [loading, setLoading] = useState(false)             // ➕ 加载状态

  const login = async () => {
    setError(null)
    const t = token.trim()
    if (!t) {
      setError('Please enter your identity token.')
      return
    }
    setLoading(true)
    try {
      // 先校验 token：调用 get_sessions
      const res = await getSessions(t)
      // 校验通过
      setCookie('identity_token', t, 30)
      onLogin(t, res.username)
    } catch (err) {
      console.error(err)
      setError('Invalid token or server unavailable.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{display:'flex', minHeight:'100vh', alignItems:'center', justifyContent:'center', fontFamily:'Inter, system-ui', padding:16}}>
      <div style={{width: '420px'}}>
        <h2 style={{textAlign:'center'}}>Login</h2>
        <div style={{
          display:'flex', flexDirection:'column', gap:12,
          marginTop:16, alignItems: 'center'
        }}>
          <input
            value={token}
            onChange={e => setToken(e.target.value)}
            placeholder="Identity Token"
            style={{
              width: '100%', padding:12,
              border:'1px solid #ddd', borderRadius:8
            }}
          />
          <button
            onClick={login}
            disabled={loading}
            style={{
              width: '120px', padding:12, borderRadius:8,
              background:'#2563eb', color:'#fff', border:'none',
              opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer'
            }}
          >
            {loading ? 'Checking...' : 'Login'}
          </button>

          {error && (
            <div style={{color:'#dc2626', fontSize:14, marginTop:4}}>
              {error}
            </div>
          )}

          <div style={{fontSize:14}}>
            New here?{' '}
            <button
              onClick={onGoRegister}
              style={{
                border:'none', background:'none',
                color:'#2563eb', cursor:'pointer'
              }}
            >
              Create account
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
