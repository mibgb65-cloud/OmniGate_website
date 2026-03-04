const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'

function normalizeBase32Secret(secret) {
  return String(secret || '')
    .toUpperCase()
    .replace(/[\s-]/g, '')
    .replace(/=+$/g, '')
}

function decodeBase32(secret) {
  const normalized = normalizeBase32Secret(secret)
  if (!normalized) {
    throw new Error('TOTP 密钥不能为空')
  }

  let bits = ''
  for (const char of normalized) {
    const index = BASE32_ALPHABET.indexOf(char)
    if (index < 0) {
      throw new Error('TOTP 密钥格式无效')
    }
    bits += index.toString(2).padStart(5, '0')
  }

  const byteLength = Math.floor(bits.length / 8)
  if (byteLength <= 0) {
    throw new Error('TOTP 密钥格式无效')
  }

  const bytes = new Uint8Array(byteLength)
  for (let i = 0; i < byteLength; i += 1) {
    bytes[i] = Number.parseInt(bits.slice(i * 8, i * 8 + 8), 2)
  }
  return bytes
}

function toCounterBytes(counter) {
  const bytes = new Uint8Array(8)
  let value = counter
  for (let i = 7; i >= 0; i -= 1) {
    bytes[i] = value & 0xff
    value = Math.floor(value / 256)
  }
  return bytes
}

export function getTotpRemainingSeconds(period = 30, timestamp = Date.now()) {
  const elapsed = Math.floor(timestamp / 1000) % period
  return period - elapsed
}

export async function generateTotpCode(
  secret,
  { digits = 6, period = 30, timestamp = Date.now() } = {},
) {
  if (!globalThis.crypto?.subtle) {
    throw new Error('当前环境不支持 Web Crypto')
  }

  const keyData = decodeBase32(secret)
  const counter = Math.floor(timestamp / 1000 / period)
  const counterBytes = toCounterBytes(counter)

  const key = await globalThis.crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-1' },
    false,
    ['sign'],
  )
  const signature = new Uint8Array(
    await globalThis.crypto.subtle.sign('HMAC', key, counterBytes),
  )
  const offset = signature[signature.length - 1] & 0x0f
  const binaryCode =
    ((signature[offset] & 0x7f) << 24) |
    ((signature[offset + 1] & 0xff) << 16) |
    ((signature[offset + 2] & 0xff) << 8) |
    (signature[offset + 3] & 0xff)

  const otp = binaryCode % 10 ** digits
  return String(otp).padStart(digits, '0')
}
