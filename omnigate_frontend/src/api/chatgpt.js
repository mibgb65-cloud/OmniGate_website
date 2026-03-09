import request from '@/utils/request'

export function createChatgptAccount(data) {
  return request({
    url: '/api/chatgpt/accounts',
    method: 'post',
    data,
  })
}

export function createChatgptAccountsBatch(data) {
  return request({
    url: '/api/chatgpt/accounts/batch',
    method: 'post',
    data,
  })
}

export function dispatchChatgptBatchRegisterTask(data) {
  return request({
    url: '/api/chatgpt/tasks/batch-register',
    method: 'post',
    data,
  })
}

export function getChatgptTaskStatus(taskRunId, config = {}) {
  return request({
    url: `/api/chatgpt/tasks/${taskRunId}`,
    method: 'get',
    ...config,
  })
}

export function getChatgptTaskStatusByRootRunId(rootRunId, config = {}) {
  return request({
    url: `/api/chatgpt/tasks/root/${rootRunId}`,
    method: 'get',
    ...config,
  })
}

export function dispatchChatgptSessionSyncTask(id) {
  return request({
    url: `/api/chatgpt/accounts/${id}/session/sync`,
    method: 'post',
  })
}

export function pageChatgptAccounts(params) {
  return request({
    url: '/api/chatgpt/accounts',
    method: 'get',
    params,
  })
}

export function getChatgptAccount(id) {
  return request({
    url: `/api/chatgpt/accounts/${id}`,
    method: 'get',
  })
}

export function updateChatgptAccount(id, data) {
  return request({
    url: `/api/chatgpt/accounts/${id}`,
    method: 'put',
    data,
  })
}

export function updateChatgptAccountStatus(id, data) {
  return request({
    url: `/api/chatgpt/accounts/${id}/status`,
    method: 'patch',
    data,
  })
}

export function batchUpdateChatgptAccountStatus(data) {
  return request({
    url: '/api/chatgpt/accounts/batch/status',
    method: 'patch',
    data,
  })
}

export function deleteChatgptAccount(id) {
  return request({
    url: `/api/chatgpt/accounts/${id}`,
    method: 'delete',
  })
}

export function batchDeleteChatgptAccounts(data) {
  return request({
    url: '/api/chatgpt/accounts/batch',
    method: 'delete',
    data,
  })
}
