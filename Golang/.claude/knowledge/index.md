### 知识索引

领域知识的轻量索引。每条用一句话说清核心逻辑。
格式：`**触发关键词** : 一句话核心逻辑 → 文件路径.函数名（可选）`

---

### 触发条件（何时向用户建议沉淀）

满足以下任一条件时，应建议沉淀到 knowledge/：

| 条件 | 示例 |
|------|------|
| 发现 Go 最佳实践与团队规范的差异 | "发现 xx 场景应该用 xxx 模式" |
| 踩坑并找到解决方案 | 某问题排查过程有价值 |
| 技术决策及其理由 | 选了 A 方案而未选 B |
| 业务规则的特殊处理 | 某字段在 xx 情况下需要特殊处理 |
| 第三方库的坑 | 某库在 xx 场景下有 bug |

---

### 知识分类

#### 业务知识

业务领域特定规则，通常与数据模型和状态机相关。

#### 技术约定

项目特定的实现模式、框架使用规范。

#### 踩坑记录

问题描述 + 原因 + 解决方案。可被 future self 快速查找复用。

---

### 沉淀流程

1. 发现有价值的信息
2. 用 `/** 关键词 */` 格式标注在发现位置
3. 在对应分类下追加条目
4. 格式：`**关键词** : 核心逻辑 → 出处`

---

#### 业务知识

（随实践积累补充）

#### 技术约定

* **Goroutine并发退出** : 使用 `golang.org/x/sync/errgroup` 管理并发退出，context 传播取消信号，禁止手动 `sync.WaitGroup` 除非有特殊原因
* **触发场景** : 新增涉及并发 HTTP 调用/gRPC 调用/goroutine 启动的代码时
* **errgroup 典型模式** :
  ```go
  g, ctx := errgroup.WithContext(ctx)
  g.Go(func() error {
      return doSomething(ctx)
  })
  if err := g.Wait(); err != nil {
      // 错误处理
  }
  ```
* **Harness试点验收** : 发布前先用验收清单确认生命周期、规则边界、reviewer 契约和样例是否可跑通 → `knowledge/pilot-checklist.md`
* **Harness接入预检** : 当需要验收或排查当前项目对框架的接入完整性时，执行 `cc-preflight`；`knowledge/integration-preflight-checklist.md` 是该命令的执行依据，而不是隐性入口 → `commands/cc-preflight.md`
* **cc-new-project回归评测** : 修改 `cc-new-project`、项目级模板或项目生命周期路由后，先用回归样例验证是否仍能正确完成项目定义、MVP 路线图和首批 change backlog，并自然桥接到后续 `cc-propose` → `knowledge/cc-new-project-eval-cases.md`
* **Harness接入高频问题** : 接入真实项目时，优先排查 `cc-init` 边界、路径解释、命令冲突、checkpoint 展示契约和验证等级等常见跑偏点 → `knowledge/common-integration-pitfalls.md`
* **cc-propose回归评测** : 修改 `cc-propose` 提问策略、路由边界、roadmap 对齐逻辑或 checkpoint 后，先用回归样例验证是否仍能正确区分新项目与已有项目 change，并把 change 放回 phase / backlog 语义中收敛 → `knowledge/cc-propose-eval-cases.md`
* **cc-apply回归评测** : 修改 `cc-apply`、验证等级规则、测试策略、task 顺序约束或相关样例后，先用回归样例验证不会退化成“只保 `go build`”，也不会跳过 `依赖 / Wave` 强行推进 → `knowledge/cc-apply-eval-cases.md`
* **Harness协议回归评测** : 修改命令口径、机器工作流、生命周期状态机、HARD-GATE、Git 策略、验证矩阵、schema 或校验脚本后，先跑协议回归样例与 `cc-verify` → `knowledge/cc-harness-protocol-eval-cases.md`
* **cc-review回归重点** : 审查实现结果时，除了核对 spec 和证据，还要检查 task promised outcome、roadmap 对齐和执行顺序是否真正落地 → `commands/cc-review.md`
* **系统讲解命令** : 当目标是帮助用户深入掌握大型复杂项目时，使用 `cc-explain-system` 输出系统定位、架构、数据流、技术机制、难点与阅读路径 → `commands/cc-explain-system.md`
* **Checkpoint结果列** : 所有 checkpoint 表的状态必须写入 `结果` 列，禁止把 `[x]` / `[ ]` 塞进 `检查项` 列冒充结果，结果值只允许 `✅`、`❌`、`⚠️`、`N/A`
* **具体优于抽象** : 默认先写具体实现，只有在多实现、测试替身或明确解耦诉求出现时再抽象接口
* **接口后置设计** : 接口从调用方需要出发定义，优先小接口，避免为了“未来可能需要”预留
* **无数据不优化** : 性能优化先看 benchmark、pprof、逃逸分析，没有数据就不要引入 `sync.Pool` 或复杂优化
* **Channel不是默认更优** : `channel` 适合表达数据流，`mutex/atomic` 适合本地共享状态，需按场景选择同步策略

#### 踩坑记录

（随实践积累补充）
