import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: '',
    refreshToken: '',
    tokenType: 'Bearer',
    accessExpireSeconds: 0,
    refreshExpireSeconds: 0,
    username: '',
    role: 'ADMIN',
  }),
  getters: {
    hasAccessToken: (state) => Boolean(state.accessToken),
    bearerAccessToken: (state) => (state.accessToken ? `Bearer ${state.accessToken}` : ''),
  },
  actions: {
    setTokenPayload(payload) {
      this.accessToken = payload?.accessToken || ''
      this.refreshToken = payload?.refreshToken || this.refreshToken
      this.tokenType = payload?.tokenType || 'Bearer'
      this.accessExpireSeconds = payload?.accessExpireSeconds || 0
      this.refreshExpireSeconds = payload?.refreshExpireSeconds || 0
      this.username = payload?.username || 'Admin User'
      this.role = payload?.role || 'ADMIN'
    },
    clearAuth() {
      this.accessToken = ''
      this.refreshToken = ''
      this.tokenType = 'Bearer'
      this.accessExpireSeconds = 0
      this.refreshExpireSeconds = 0
      this.username = ''
      this.role = 'ADMIN'
    },
  },
  persist: {
    key: 'omnigate-auth-store',
    storage: localStorage,
    paths: ['accessToken', 'refreshToken', 'tokenType', 'accessExpireSeconds', 'refreshExpireSeconds', 'username', 'role'],
  },
})
