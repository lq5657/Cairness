---
alwaysApply: true
---
### 工程上下文

首次使用时执行 /init 让 AI 分析工程并填充本文件。

#### 1. 应用概况

* 应用名: （待填充）
* 简介: （一句话描述）
* 技术栈: Golang 1.21+ / Gin / GORM / （根据项目实际填写）
* 构建工具: Go Modules (`go.mod`)

#### 2. 目录结构与模块职责

执行 `tree -d -L 3` 后填充。

#### 3. 分层架构 (结合 Go 常见规范)

Handler (internal/handler/)     ← 入口层，HTTP 解析，参数校验
↓
Service (internal/service/)     ← 业务编排，事务边界
↓
Manager (internal/manager/)     ← 领域能力，单一职责，可复用（按需）
↓
Repository (internal/repo/)     ← 数据访问，封装 GORM 和缓存

#### 4. 关键依赖


| 中间件           | 用途       | 备注 |
| ---------------- | ---------- | ---- |
| Redis            | 缓存控制   |      |
| MySQL            | 关系型存储 |      |
| （根据项目填写） |            |      |
