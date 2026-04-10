export interface UserInfo {
  id: string
  username: string
  realName: string
  email: string
  avatar?: string
  roles: string[]
  permissions: string[]
  is_superadmin?: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  accessToken: string
  refreshToken: string
  tokenType: string
  expiresIn: number
}
