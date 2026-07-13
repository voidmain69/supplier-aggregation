/**
 * Minimal ULID generator for client-side idempotency keys (Crockford base32, time + randomness).
 * Not used for domain ids — the server owns those — only to make POSTs safely retryable.
 */

const ENCODING = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';

function randomChar(): string {
  // charAt never returns undefined, so no non-null assertion is needed.
  return ENCODING.charAt(Math.floor(Math.random() * ENCODING.length));
}

export function ulid(): string {
  let ts = Date.now();
  const time: string[] = [];
  for (let i = 0; i < 10; i++) {
    time.unshift(ENCODING.charAt(ts % 32));
    ts = Math.floor(ts / 32);
  }
  let random = '';
  for (let i = 0; i < 16; i++) random += randomChar();
  return time.join('') + random;
}
