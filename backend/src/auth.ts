import { createHash, timingSafeEqual } from 'node:crypto';
import { FastifyReply, FastifyRequest } from 'fastify';

function credentialDigest(value: string): Buffer {
  return createHash('sha256').update(value, 'utf8').digest();
}

export async function verifyApiKey(request: FastifyRequest, reply: FastifyReply) {
  const header = request.headers['x-api-key'];
  const providedKey = typeof header === 'string' ? header : '';
  const expectedKey = request.server.config.INGEST_API_KEY;

  if (!timingSafeEqual(credentialDigest(providedKey), credentialDigest(expectedKey))) {
    reply.status(403).send({ error: 'Forbidden' });
    return;
  }
}
