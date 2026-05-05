FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Accept build-time env vars so NEXT_PUBLIC_ are baked into the bundle
# Pass via docker-compose build.args or --build-arg
ARG NEXT_PUBLIC_VIAGRA_URL=http://localhost:8000
ARG NEXT_PUBLIC_ORCHESTRATOR_URL=http://localhost:8000
ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:4000
ARG NEXT_PUBLIC_VILLA3D_API_URL=http://localhost:8056

ENV NEXT_PUBLIC_VIAGRA_URL=$NEXT_PUBLIC_VIAGRA_URL
ENV NEXT_PUBLIC_ORCHESTRATOR_URL=$NEXT_PUBLIC_ORCHESTRATOR_URL
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_VILLA3D_API_URL=$NEXT_PUBLIC_VILLA3D_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
