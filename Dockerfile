# ── Build stage ──────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

COPY backend/package.json backend/package-lock.json ./
RUN npm ci

COPY backend/tsconfig.json ./
COPY backend/src ./src
RUN npm run build
RUN mkdir -p dist/db/migrations && cp src/db/migrations/*.sql dist/db/migrations/

# ── Production stage ─────────────────────────────────────────────────────────
FROM node:22-alpine AS production

ENV NODE_ENV=production

# Create non-root user
RUN addgroup -g 1001 -S zephyr && \
    adduser -S zephyr -u 1001 -G zephyr

WORKDIR /app

# Copy only production dependencies
COPY backend/package.json backend/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Copy compiled output
COPY --from=builder /app/dist ./dist

USER zephyr

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD node -e "fetch('http://localhost:3000/up').then(r => r.ok || process.exit(1)).catch(() => process.exit(1))"

CMD ["node", "dist/server.js"]
