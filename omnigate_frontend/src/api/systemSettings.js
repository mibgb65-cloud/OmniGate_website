import request from '@/utils/request'

export function getCloudMailSystemSettings() {
  return request({
    url: '/api/system-settings/cloudmail',
    method: 'get',
  })
}

export function updateCloudMailSystemSettings(data) {
  return request({
    url: '/api/system-settings/cloudmail',
    method: 'put',
    data,
  })
}
