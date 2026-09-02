export interface AuthSession {
  principal: string
  expires_at: number
  csrf_token: string
}

export interface LoginRequest {
  password: string
}

export type AuthState =
  | { status: 'checking' }
  | { status: 'anonymous'; message?: string }
  | { status: 'authenticated'; session: AuthSession; message?: string }
