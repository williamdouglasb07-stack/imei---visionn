FROM node:18-alpine AS builder

WORKDIR /app

# Copiar package files
COPY package.json package-lock.json ./

# Instalar dependências
RUN npm ci

# Copiar código
COPY . .

# Build
RUN npm run build

# Production image
FROM node:18-alpine

WORKDIR /app

# Instalar apenas dependências de produção
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Copiar build do builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Expor porta
EXPOSE 3000

# Variáveis de ambiente
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Executar
CMD ["npm", "start"]
