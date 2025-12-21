# Vercel 部署指南

本项目包含前端（React + Vite）和后端（FastAPI）两部分。以下是部署方案：

## 方案一：前端部署到Vercel + 后端部署到其他平台（推荐）

### 为什么推荐这个方案？
- 后端的 `/simulate` 端点可能需要较长运行时间
- Vercel Serverless Functions 有执行时间限制（免费版10秒，Pro版60秒）
- 独立部署后端可以获得更好的性能和灵活性

### 步骤：

#### 1. 部署后端到 Railway/Render/Fly.io

**Railway 部署（推荐）：**
```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 部署
railway up
```

在 Railway 项目设置中：
- 设置启动命令：`python api_server.py`
- 确保 `requirements.txt` 包含所有依赖
- 记录部署后的 URL（例如：`https://your-app.railway.app`）

**Render 部署：**
1. 在 Render 创建新的 Web Service
2. 连接 GitHub 仓库
3. 设置：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python api_server.py`
   - 记录部署后的 URL

#### 2. 部署前端到 Vercel

```bash
# 安装 Vercel CLI
npm i -g vercel

# 在项目根目录运行
vercel

# 按提示操作，选择项目设置
```

在 Vercel 项目设置中：
1. 进入 Settings → Environment Variables
2. 添加环境变量：
   - Key: `VITE_API_URL`
   - Value: 你的后端 URL（例如：`https://your-app.railway.app`）
3. 重新部署

或者在部署时直接设置：
```bash
vercel --build-env VITE_API_URL=https://your-backend-url.com
```

## 方案二：全部部署到Vercel（适合短时间模拟）

如果你的模拟时间较短（<10秒），可以将后端也部署为Vercel Serverless Functions。

### 步骤：

1. 创建 `api` 目录并适配后端代码：

```bash
mkdir api
```

2. 创建 `api/index.py`：
```python
from api_server import app

# Vercel需要这个handler
handler = app
```

3. 更新 `vercel.json`：
```json
{
  "version": 2,
  "buildCommand": "cd web && npm install && npm run build",
  "outputDirectory": "web/dist",
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ],
  "env": {
    "VITE_API_URL": "/api"
  }
}
```

4. 确保 `requirements.txt` 在根目录

5. 部署：
```bash
vercel --prod
```

## 当前配置

当前 `vercel.json` 配置为**方案一**（仅前端部署）。

### 本地开发

```bash
# 启动后端
python api_server.py

# 启动前端（新终端）
cd web
npm run dev
```

### 环境变量

在 `web/.env.example` 中查看所需的环境变量。

本地开发时创建 `web/.env`：
```bash
cp web/.env.example web/.env
```

## 注意事项

1. **CORS配置**：确保后端的CORS设置允许你的前端域名
2. **API URL**：部署后记得更新Vercel环境变量中的 `VITE_API_URL`
3. **依赖管理**：确保 `requirements.txt` 包含所有Python依赖
4. **构建缓存**：如果部署失败，尝试清除Vercel构建缓存

## 推荐的后端平台对比

| 平台 | 免费额度 | 优点 | 缺点 |
|------|---------|------|------|
| Railway | $5/月免费额度 | 简单易用，自动部署 | 免费额度有限 |
| Render | 750小时/月 | 慷慨的免费额度 | 冷启动较慢 |
| Fly.io | 3个共享CPU VM | 性能好，全球部署 | 配置稍复杂 |
| Vercel Functions | 100GB-小时/月 | 与前端集成好 | 执行时间限制 |

## 故障排查

### 前端无法连接后端
- 检查 Vercel 环境变量 `VITE_API_URL` 是否正确
- 检查后端 CORS 配置
- 查看浏览器控制台的网络请求

### 后端部署失败
- 检查 `requirements.txt` 是否完整
- 查看部署日志中的错误信息
- 确保 Python 版本兼容（建议 3.9+）

### 模拟超时
- 如果使用 Vercel Functions，考虑升级到 Pro 计划或使用方案一
- 减少模拟时长
- 优化模拟代码性能
