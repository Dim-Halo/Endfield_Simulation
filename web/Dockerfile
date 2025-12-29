# 前端Dockerfile (多阶段构建)
FROM node:18-alpine AS builder

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段 - 使用nginx提供静态文件
FROM nginx:alpine

# 复制构建产物到nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置（用于SPA路由）
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
