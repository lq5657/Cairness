---
change_id: kebab-case-id
created: YYYY-MM-DD
updated: YYYY-MM-DD
task_graph:
  version: 1
  tasks:
    - id: T1
      depends_on: []
      parallel_safe: true
      files:
        - path/to/file
---

### 任务拆分 — 需求名称

#### 前置条件

* [ ] `spec.md` 已确认且 `status = propose`
* [ ] `depends_on` 中列出的前置变更已满足执行条件（如有）

#### 依赖 / Wave 总览

#### 变更影响概览

##### 文件变更清单

| 文件 | 操作 | 涉及 Task | 说明 |
|------|------|-----------|------|

##### 受影响接口 / 调用方

| 接口 / 函数 / 入口 | 变更类型 | 上游调用方 | 下游依赖 | 涉及 Task |
|--------------------|----------|------------|----------|-----------|

##### 构建系统变更

#### Spec 覆盖映射

| Spec 章节 / 映射编号 | 覆盖 Task | 说明 |
|----------------------|-----------|------|

#### Task 1: 任务名

* **目标**:
* **不包含范围**:
* **涉及文件**:
  - `path/to/file`
* **上下游 Context**:
* **关键签名**:
* **验收标准**:
* **验证步骤**:
* **渐进可验证要求**:
* **测试要求**:
* **依赖 / Wave**: 以 frontmatter `task_graph` 为准；正文仅解释依赖和并行原因
* **回退方式**:
* **完成后状态**: `todo` / `in_progress` / `blocked` / `partial` / `aborted` / `done`
* **Baseline / Delta**:
* **对应 commit（按需）**:
* **并发注意事项（按需）**:
* **数据库注意事项（按需）**:
