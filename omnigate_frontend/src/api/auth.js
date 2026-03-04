import request from '@/utils/request'

export function login(data) {
  return request({
    url: '/api/auth/login',
    method: 'post',
    data,
    skipAuth: true,
  })
}

export function refreshToken(data) {
  return request({
    url: '/api/auth/refresh',
    method: 'post',
    data,
    skipAuth: true,
    skipErrorMessage: true,
  })
}

export function logout(data) {
  return request({
    url: '/api/auth/logout',
    method: 'post',
    data,
  })
}
