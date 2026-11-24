FROM node:24-alpine AS build
WORKDIR /web
COPY package*.json .
RUN npm ci
COPY src src
COPY public public
COPY vite.config.js index.html ./
ENV VITE_API_URL=/api
RUN npm run build

FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
