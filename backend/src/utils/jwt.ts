import jwt from 'jsonwebtoken'

export function signAccessToken(payload: { sub: string; role: string }) {
  const secret = process.env.JWT_SECRET
  if (!secret) throw new Error('Missing JWT_SECRET')

  const expiresIn = (process.env.JWT_EXPIRES_IN ?? '15m') as unknown
  return (jwt.sign as unknown as (p: unknown, s: string, o: unknown) => string)(
    payload,
    secret,
    { expiresIn },
  )
}

export function verifyAccessToken(token: string): { sub: string; role: string } {
  const secret = process.env.JWT_SECRET
  if (!secret) throw new Error('Missing JWT_SECRET')

  const decoded = jwt.verify(token, secret) as unknown as { sub?: unknown; role?: unknown }
  const sub = String(decoded.sub ?? '')
  const role = String(decoded.role ?? '')
  if (!sub || !role) throw new Error('Invalid token payload')
  return { sub, role }
}

