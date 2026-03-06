import request from '@/utils/request'

export function listRoles() {
  return request({
    url: '/api/roles',
    method: 'get',
  })
}
