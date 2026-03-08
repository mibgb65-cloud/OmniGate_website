const DEFAULT_PAGE_SIZE = 200

function normalizeExportField(value, fallback = '暂无') {
  const text = String(value ?? '').trim()
  return text || fallback
}

function sanitizeFilenameSegment(value) {
  return String(value ?? '')
    .trim()
    .replace(/[\\/:*?"<>|]+/g, '-')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

function buildTimestamp() {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    '_',
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds()),
  ].join('')
}

export function buildExportFilename(prefix) {
  const safePrefix = sanitizeFilenameSegment(prefix) || 'accounts'
  return `${safePrefix}_${buildTimestamp()}.txt`
}

export function downloadTextFile({ filename, content }) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

export async function fetchAllPagedRecords(fetchPage, params = {}, pageSize = DEFAULT_PAGE_SIZE) {
  const records = []
  let current = 1
  let total = Number.POSITIVE_INFINITY

  while (records.length < total) {
    const pageData = await fetchPage({
      ...params,
      current,
      size: pageSize,
    })

    const pageRecords = Array.isArray(pageData?.records) ? pageData.records : []
    total = Number(pageData?.total || pageRecords.length || 0)
    records.push(...pageRecords)

    if (!pageRecords.length || records.length >= total) {
      break
    }
    current += 1
  }

  return records
}

export function formatGoogleAccountLine(account) {
  return [
    normalizeExportField(account?.email),
    normalizeExportField(account?.password),
    normalizeExportField(account?.recoveryEmail),
    normalizeExportField(account?.totpSecret),
  ].join('----')
}

export function formatGithubAccountLine(account) {
  return [
    normalizeExportField(account?.email),
    normalizeExportField(account?.password),
    normalizeExportField(account?.username),
    normalizeExportField(account?.totpSecret),
  ].join('----')
}

export function formatChatgptAccountLine(account) {
  return [
    normalizeExportField(account?.email),
    normalizeExportField(account?.password),
    normalizeExportField(account?.subTier),
    normalizeExportField(account?.totpSecret),
  ].join('----')
}
