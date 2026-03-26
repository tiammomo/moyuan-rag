ARG NODE_BASE_IMAGE=docker.m.daocloud.io/library/node:20-alpine

# Stage 1: Dependencies
FROM ${NODE_BASE_IMAGE} AS deps
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Stage 2: Builder
FROM ${NODE_BASE_IMAGE} AS builder
WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p public

# Build arguments for environment variables
ARG NEXT_PUBLIC_API_URL=http://localhost:38084
ARG INTERNAL_API_URL=http://localhost:38084
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV INTERNAL_API_URL=$INTERNAL_API_URL

# Build the application
RUN npm run build

# Stage 3: Runner
FROM ${NODE_BASE_IMAGE} AS runner
WORKDIR /app

ENV NODE_ENV=production
ARG NEXT_PUBLIC_API_URL=http://localhost:38084
ARG INTERNAL_API_URL=http://localhost:38084
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV INTERNAL_API_URL=$INTERNAL_API_URL

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Set ownership
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
