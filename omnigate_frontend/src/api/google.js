import request from '@/utils/request'

export function importGoogleAccounts(data) {
  return request({
    url: '/api/google/accounts/import',
    method: 'post',
    data,
  })
}

export function pageGoogleAccounts(params) {
  return request({
    url: '/api/google/accounts',
    method: 'get',
    params,
  })
}

export function getGoogleAccountDetail(id) {
  return request({
    url: `/api/google/accounts/${id}`,
    method: 'get',
  })
}

export function updateGoogleAccountBase(id, data) {
  return request({
    url: `/api/google/accounts/${id}`,
    method: 'put',
    data,
  })
}

export function listGoogleFamilyMembers(id) {
  return request({
    url: `/api/google/accounts/${id}/family-members`,
    method: 'get',
  })
}

export function listGoogleInviteLinks(id) {
  return request({
    url: `/api/google/accounts/${id}/invite-links`,
    method: 'get',
  })
}

export function deleteGoogleAccount(id) {
  return request({
    url: `/api/google/accounts/${id}`,
    method: 'delete',
  })
}
