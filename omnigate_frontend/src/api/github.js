import request from '@/utils/request'

export function importGithubAccounts(data) {
  return request({
    url: '/api/github/accounts/import',
    method: 'post',
    data,
  })
}

export function pageGithubAccounts(params) {
  return request({
    url: '/api/github/accounts',
    method: 'get',
    params,
  })
}

export function getGithubAccount(id) {
  return request({
    url: `/api/github/accounts/${id}`,
    method: 'get',
  })
}

export function updateGithubAccount(id, data) {
  return request({
    url: `/api/github/accounts/${id}`,
    method: 'put',
    data,
  })
}

export function updateGithubAccountStatus(id, data) {
  return request({
    url: `/api/github/accounts/${id}/status`,
    method: 'patch',
    data,
  })
}

export function deleteGithubAccount(id) {
  return request({
    url: `/api/github/accounts/${id}`,
    method: 'delete',
  })
}
