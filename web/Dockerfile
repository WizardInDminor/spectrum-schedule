FROM node:22-alpine AS build
WORKDIR /srv/web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /srv/web
ENV NODE_ENV=production
COPY --from=build /srv/web ./
EXPOSE 3000
CMD ["npm", "run", "start"]
