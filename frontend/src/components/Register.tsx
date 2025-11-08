import { useState } from 'react'
import { createUser } from '../api'
import { setCookie } from '../cookies'

type Props = { onRegistered: (token: string, name: string) => void; onBack: () => void; }

export default function Register({ onRegistered, onBack }: Props) {
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [issuedToken, setIssuedToken] = useState<string | null>(null)

  const submit = async () => {
    if (!name.trim()) return
    const res = await createUser(name.trim(), desc.trim())
    setIssuedToken(res.identity_token)
  }

  const confirm = () => {
    if (!issuedToken) return
    setCookie('identity_token', issuedToken, 365)
    onRegistered(issuedToken, name.trim())
  }

  return (
    <div style={{display:'flex', minHeight:'100vh', alignItems:'center', justifyContent:'center', fontFamily:'Inter, system-ui', padding:16}}>
      <div style={{width: '470px'}}>
        {!issuedToken ? (
          <>
            <h2 style={{textAlign:'center'}}>Register</h2>
            <div style={{display:'flex', flexDirection:'column', gap:12, marginTop:16}}>
              <input value={name} onChange={e=>setName(e.target.value)} placeholder="Your name"
                     style={{padding:12, border:'1px solid #ddd', borderRadius:8}} />
              <textarea value={desc} onChange={e=>setDesc(e.target.value)} placeholder="A short self-intro"
                        rows={4} style={{padding:12, border:'1px solid #ddd', borderRadius:8}} />
              <div style={{display:'flex', gap:8, justifyContent:'center'}}>
                <button onClick={submit} style={{padding:12, minWidth:120, borderRadius:8, background:'#2563eb', color:'#fff', border:'none'}}>Create</button>
                <button onClick={onBack} style={{padding:12, minWidth:120, borderRadius:8}}>Back</button>
              </div>
            </div>
          </>
        ) : (
          <>
            <h2 style={{textAlign:'center'}}>Identity Token</h2>
            <p style={{marginTop:8}}>Please save this token carefully. You will need it to log in:</p>
            <pre style={{padding:12, background:'#273636ff', border:'1px solid #eee', borderRadius:8, userSelect:'all'}}>{issuedToken}</pre>
            <div style={{display:'flex', justifyContent:'center'}}>
              <button onClick={confirm} style={{padding:12, borderRadius:8, marginTop:12, minWidth:220, background:'#2563eb', color:'#fff', border:'none'}}>I have saved it, continue</button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
