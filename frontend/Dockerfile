# Build stage
FROM node:18-alpine as build-stage
WORKDIR /app
COPY package*.json ./
# 使用淘宝镜像加速（可选）
RUN npm config set registry https://registry.npmmirror.com
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

