FROM node:18-slim

WORKDIR /app

COPY shared/gateway/src/package*.json ./
RUN npm install --omit=dev

COPY shared/gateway/src/ ./
COPY shared/mcp/servers/ ./servers/

ENV NODE_ENV=production

EXPOSE 8000

CMD ["node", "app.js"]