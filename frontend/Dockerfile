# Étape 1 : build Vite (TypeScript -> fichiers statiques)
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Étape 2 : Caddy sert les fichiers statiques et relaie /api vers FastAPI
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
