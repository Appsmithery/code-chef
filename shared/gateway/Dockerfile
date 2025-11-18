FROM node:18-slim

WORKDIR /app

COPY gateway/src/package*.json ./
RUN npm install --omit=dev

COPY gateway/src/ ./
COPY gateway/servers/ ./servers/

ENV NODE_ENV=production

EXPOSE 8000

CMD ["node", "app.js"]