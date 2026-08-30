import { FastifyReply, FastifyRequest } from 'fastify';

export async function verifyApiKey(request: FastifyRequest, reply: FastifyReply) {
  const key = request.headers['x-api-key'];
  if (key !== request.server.config.INGEST_API_KEY) {
    reply.status(403).send({ error: 'Forbidden' });
    return;
  }
}
