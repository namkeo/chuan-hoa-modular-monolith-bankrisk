# Stage 1: Build React Frontend SPA bundle
FROM node:20-alpine AS builder
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

# Stage 2: Unified Production Web FE & Express Gateway Service
FROM node:20-alpine
WORKDIR /app

# Install production dependencies for Express server gateway
COPY package*.json ./
COPY server/package*.json ./server/
RUN cd server && npm ci --only=production

# Copy compiled React static bundle & Express server source
COPY --from=builder /app/client/dist ./client/dist
COPY server/ ./server/

EXPOSE 4000
ENV PORT=4000
ENV NODE_ENV=production

CMD ["node", "server/server.js"]
