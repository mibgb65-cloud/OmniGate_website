import request from '@/utils/request'

export function pageUsers(params) {
  return request({
    url: '/api/users',
    method: 'get',
    params,
  })
}

export function getUserInfo(userId) {
  return request({
    url: `/api/users/${userId}`,
    method: 'get',
  })
}

export function createUser(data) {
  return request({
    url: '/api/users',
    method: 'post',
    data,
  })
}

export function updateUser(userId, data) {
  return request({
    url: `/api/users/${userId}`,
    method: 'put',
    data,
  })
}

export function updateUserPassword(userId, data) {
  return request({
    url: `/api/users/${userId}/password`,
    method: 'put',
    data,
  })
}

export function assignUserRoles(userId, data) {
  return request({
    url: `/api/users/${userId}/roles`,
    method: 'put',
    data,
  })
}

export function updateUserStatus(userId, status) {
  return request({
    url: `/api/users/${userId}/status/${status}`,
    method: 'put',
  })
}

export function deleteUser(userId) {
  return request({
    url: `/api/users/${userId}`,
    method: 'delete',
  })
}
