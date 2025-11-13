FROM node:18-slim

WORKDIR /app

COPY ../../mcp/gateway/package*.json ./
RUN npm install --omit=dev

COPY ../../mcp/gateway/ ./

ENV NODE_ENV=production

EXPOSE 8000

CMD ["node", "app.js"]