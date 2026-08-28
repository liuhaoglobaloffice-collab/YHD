# S6 生产部署 - 前端镜像（构建 + nginx 托管）
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install

COPY . .
# 生产环境：前端 API 走同域（由 nginx 代理到后端）
ENV VITE_API_BASE=
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]