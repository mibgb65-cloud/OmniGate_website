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

export function dispatchGoogleAccountSyncTask(id) {
  return request({
    url: `/api/google/accounts/${id}/sync`,
    method: 'post',
  })
}

export function dispatchGoogleBatchSyncTask(accountIds) {
  return request({
    url: '/api/google/accounts/sync/batch',
    method: 'post',
    data: { accountIds },
  })
}

export function dispatchGoogleStudentEligibilitySyncTask(id) {
  return request({
    url: `/api/google/accounts/${id}/student-eligibility/sync`,
    method: 'post',
  })
}

export function dispatchGoogleFamilyInviteTask(id, invitedAccountEmail) {
  return request({
    url: `/api/google/accounts/${id}/family-members/invite`,
    method: 'post',
    data: { invitedAccountEmail },
  })
}

export function getGoogleTaskRunStatus(taskRunId) {
  return request({
    url: `/api/google/tasks/${taskRunId}`,
    method: 'get',
  })
}

export function getGoogleLatestTaskRunStatusByRootRunId(rootRunId) {
  return request({
    url: `/api/google/tasks/root/${rootRunId}`,
    method: 'get',
  })
}

export function batchGetGoogleLatestTaskRunStatusesByRootRunIds(rootRunIds) {
  return request({
    url: '/api/google/tasks/root/status/batch',
    method: 'post',
    data: { rootRunIds },
  })
}
