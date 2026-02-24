# Endfield Combat Simulator (终末地战斗模拟器)

基于《明日方舟：终末地》技术测试机制构建的 Python 战斗模拟系统。支持多角色排轴、法术异常、伤害计算。

## ✨ 主要功能

*   **高精度模拟**：基于 0.1s Tick 的时间轴引擎。
*   **元素反应**：支持 灼热/电磁/自然/冷凝 的附着、法术爆发及异色反应（燃烧、导电、腐蚀等）。
*   **现代化 Web 界面**：React + TypeScript + Vite 前端，FastAPI 后端，支持实时模拟、角色配置、时间轴编辑。
*   **多种运行模式**：CLI 命令行、Streamlit 快速可视化、完整 Web 应用。

## 🛠️ 安装与运行

### 后端安装

1. **克隆仓库**
   ```bash
   git clone https://github.com/Dim-Halo/endfield_sim.git
   cd endfield_sim
   ```

2. **安装 Python 依赖**
   ```bash
   pip install -r requirements.txt
   ```

### 运行方式

#### 1. Web 应用（推荐）

**启动后端服务器：**
```bash
python api_server.py
# 或使用 uvicorn
uvicorn api_server:app --reload --port 8000
```

**启动前端（新终端）：**
```bash
cd web
npm install  # 首次运行需要安装依赖
npm run dev
```

访问 `http://localhost:5173` 使用完整的 Web 界面，支持：
- 角色配置与装备管理
- 可视化时间轴编辑器
- 实时模拟结果展示
- DPS 统计与伤害分布图表

#### 2. Streamlit 快速可视化

```bash
streamlit run app.py
```

适合快速查看战斗快照、Buff 监控和动作时间轴。

#### 3. CLI 命令行模式

```bash
python main.py
```

使用预设队伍进行快速测试和调试。

## 📚 文档

详细文档位于 `docs/` 目录：
- `ARCHITECTURE_UPGRADE.md` - 系统架构说明
- `QTE_SYSTEM_GUIDE.md` - QTE 系统使用指南
- `OPERATOR_CONFIG_GUIDE.md` - 角色配置系统
- `WEAPON_SYSTEM_GUIDE.md` - 武器系统文档
- `USER_GUIDE.md` - 用户使用指南

开发者指南请参考 `CLAUDE.md`。

## 🏗️ 技术栈

**后端：**
- Python 3.8+
- FastAPI (REST API)
- 事件驱动架构 (EventBus)
- Tick-based 模拟引擎

**前端：**
- React 18
- TypeScript
- Vite (构建工具)
- Zustand (状态管理)
- Recharts (数据可视化)