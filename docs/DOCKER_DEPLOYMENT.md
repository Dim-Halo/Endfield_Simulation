# Docker 部署指南

本项目支持使用 Docker 和 Docker Compose 进行一键部署。

## 📋 前置要求

- Docker 20.10+
- Docker Compose 2.0+

## 🚀 快速开始

### 1. 构建并启动所有服务

```bash
docker-compose up -d
```

这将启动：
- **后端API服务**：运行在 `http://localhost:8000`
- **前端Web服务**：运行在 `http://localhost:3000`

### 2. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend
```

### 3. 停止服务

```bash
docker-compose down
```

### 4. 重新构建

```bash
# 重新构建并启动
docker-compose up -d --build

# 仅重新构建后端
docker-compose build backend

# 仅重新构建前端
docker-compose build frontend
```

## 🔧 配置说明

### 端口配置

默认端口映射：
- 后端：`8000:8000`
- 前端：`3000:80`

修改端口：编辑 `docker-compose.yml` 中的 `ports` 配置。

### 环境变量

**后端环境变量**（在 `docker-compose.yml` 的 `backend.environment` 中配置）：
- `PYTHONUNBUFFERED=1`：实时输出日志

**前端环境变量**（在 `docker-compose.yml` 的 `frontend.environment` 中配置）：
- `VITE_API_URL`：后端API地址
  - 本地开发：`http://localhost:8000`
  - 生产环境：修改为实际的后端域名

### 生产环境配置

生产环境部署时，修改 `docker-compose.yml`：

```yaml
frontend:
  environment:
    - VITE_API_URL=https://your-backend-domain.com
```

## 📦 单独构建镜像

### 构建后端镜像

```bash
docker build -t endfield-backend:latest .
docker run -d -p 8000:8000 --name endfield-backend endfield-backend:latest
```

### 构建前端镜像

```bash
cd web
docker build -t endfield-frontend:latest .
docker run -d -p 3000:80 --name endfield-frontend endfield-frontend:latest
```

## 🔍 健康检查

检查服务是否正常运行：

```bash
# 检查后端
curl http://localhost:8000/characters

# 检查前端
curl http://localhost:3000
```

## 🐛 故障排查

### 容器无法启动

```bash
# 查看容器状态
docker-compose ps

# 查看详细日志
docker-compose logs backend
docker-compose logs frontend
```

### 前端无法连接后端

1. 检查 `docker-compose.yml` 中的 `VITE_API_URL` 配置
2. 确保后端服务已启动：`docker-compose ps backend`
3. 检查网络连接：`docker network inspect endfield_endfield-network`

### 端口冲突

如果端口被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8001:8000"  # 将本地端口改为8001
```

## 📊 资源使用

查看容器资源使用情况：

```bash
docker stats
```

## 🔄 更新部署

代码更新后重新部署：

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建并启动
docker-compose up -d --build

# 3. 清理旧镜像（可选）
docker image prune -f
```

## 🌐 生产环境部署建议

1. **使用反向代理**：在前面加 Nginx/Traefik 处理 HTTPS
2. **持久化数据**：如需持久化，添加 volumes 配置
3. **资源限制**：添加 CPU/内存限制
4. **日志管理**：配置日志驱动和轮转
5. **监控告警**：集成 Prometheus/Grafana

### 示例：添加资源限制

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 📝 文件说明

- `Dockerfile`：后端Python应用的Docker镜像配置
- `web/Dockerfile`：前端React应用的Docker镜像配置（多阶段构建）
- `docker-compose.yml`：服务编排配置
- `.dockerignore`：Docker构建时忽略的文件

## 🆘 获取帮助

如遇问题，请查看：
1. Docker日志：`docker-compose logs`
2. 容器状态：`docker-compose ps`
3. 网络配置：`docker network ls`
