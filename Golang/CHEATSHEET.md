# Golang Harness 一页速查表

适用对象：第一次接触这套 Spec 驱动开发框架的维护者、接入者、日常使用者。

核心理念：`Code is Cheap, Context is Expensive`

## 1. 先记住的三条

1. `No Spec, No Code`：没有 `changes/<change-id>/spec.md`，禁止 `/apply`
2. `Spec is Truth`：`review/done` 阶段发现 spec 和代码不一致，必须先修偏差
3. `变更即记录`：改代码时必须同步更新 `changes/` 文档

## 2. 目录契约

每个真实变更必须放在：

```text
Golang/.claude/changes/<change-id>/
├── spec.md
├── tasks.md
├── log.md
├── test-spec.md   # 可选
└── review.md      # /review 后生成
```

补充：
- 示例只放在 `changes/examples/`
- 模板只放在 `changes/templates/`
- `change-id` 只能用小写英文/数字加 `-`

## 3. 生命周期

| 状态 | 含义 | 允许命令 |
|------|------|----------|
| `propose` | 提案已生成，尚未开始实现 | `/propose` |
| `apply` | 正在实现，可在 task 边界内暂时不一致 | `/apply`, `/test` |
| `review` | 实现完成，等待审查，要求 spec 与代码一致 | `/review`, `/fix` |
| `done` | 审查通过并归档 | 无 |

失败不中断生命周期，只在文档里记录：
- `blocked`：被环境、信息、依赖阻塞
- `partial`：部分完成
- `aborted`：主动放弃本次尝试

## 4. 日常命令流

### `/init`

用途：
- 分析真实工程结构
- 填写 `rules/project-context.md`

结果要求：
- 写明真实目录、依赖、分层、日志、配置、测试约定
- 不确定的内容标记“待确认”，不能编造

禁止：
- 不要把 `/init` 扩展成“初始化示例变更”
- 不要因为缺少样例去创建 `changes/examples/`
- 不要在 `/init` 阶段创建真实 `changes/<change-id>/`
- 不要因为缺少脚手架去创建仓库根目录 `rules/`、`knowledge/`、`changes/`、`audits/`
- 不要在 `/init` 阶段补齐 `.claude` 下的模板、示例和规则文件

前提：
- 先确保目标项目已经安装好 `.claude/` 脚手架
- `/init` 只负责识别项目事实，不负责安装框架

### `/inspect-codebase <mode> [scope]`

用途：
- 在没有新需求时，对存量项目做代码、设计、逻辑、安全或配置体检

产物：
- `audits/<audit-id>/report.md`

适用场景：
- 暂时没有新需求
- 想先发现问题，再决定是否转成正式 change

参数：
- `<mode>`：必填，取值为 `architecture`、`logic`、`observability`、`test-debt`
- `[scope]`：可选，表示全仓、目录、模块或链路；不填时默认全仓

预设模式：
- `architecture`：看分层、依赖方向、模块边界、抽象是否失控
- `logic`：看业务规则、状态流转、幂等、错误语义、权限前置
- `observability`：看日志、trace、metrics、告警、异步链路观测
- `test-debt`：看测试缺口、回归证据、测试分层、可测性

示例：
- `/inspect-codebase architecture`
- `/inspect-codebase architecture user-domain`
- `/inspect-codebase logic`
- `/inspect-codebase logic payment-refund`
- `/inspect-codebase observability order-consumer`
- `/inspect-codebase test-debt internal/service`

### `/promote-audit <audit-id> <change-id>`

用途：
- 把 audit 报告里的 Findings 收敛成一个正式 change 草稿

产物：
- `audits/<audit-id>/to-change.md`

注意：
- 不要把整份审查报告原样复制成一个 change
- 先明确“本次修什么，不修什么”
- 若问题类型太杂，拆成多个 change

### `/propose <需求>`

流程：
1. 读代码做 Research
2. 提澄清问题
3. 做 YAGNI 裁剪
4. 生成 `spec.md`
5. 生成 `tasks.md`
6. 等待 HARD-GATE 确认

进入 `/apply` 前必须满足：
- 需求明确
- 功能点已识别
- 与现有 change 的冲突已检查
- `待澄清` 全部解决

### `/apply <change-id>`

执行要求：
- 先把 `spec.status` 改为 `apply`
- 按 task 逐个实现
- 每个 task 完成后给出验证证据
- 默认一个 task 一个 commit
- 所有 task 完成后再改为 `review`

硬前置：
- `spec.md`、`tasks.md` 存在
- 用户已确认执行
- 依赖变更已满足
- 当前分支匹配 `change-id`
- 不在 `main/master`

### `/review <change-id>`

两阶段：
1. Spec Compliance
2. Code Quality

产物：
- `changes/<change-id>/review.md`

前置：
- `spec.status = review`
- 代码已存在

### `/fix <change-id>`

用途：
- 回收 `review.md` 中的问题
- 修复代码并同步更新 spec/tasks/log/review

注意：
- 默认只处理 `status = open` 的 Findings
- 已修复问题改为 `fixed`，不要删除审计记录

### `/test <change-id>`

用途：
- 补测试设计
- 补验证证据

要求：
- 在 `test-spec.md` 说明测试层级选择和原因
- bugfix 默认至少有一条回归证据

### `/archive <change-id>`

前置：
- `review.md` 已允许归档
- `spec.status = review`

结果：
- 完成知识沉淀
- `spec.status = done`

## 5. 提案时最容易漏的字段

这些场景出现时，`spec.md` 必须加专门章节说明：

| 场景 | 必填内容 |
|------|----------|
| 数据库变更 | migration 路径、兼容窗口、回滚路径 |
| 对外接口变更 | 兼容性分类、客户端影响、迁移路径 |
| 配置变更 | 配置名、默认值、必填性、环境差异 |
| 关键链路/异步任务 | 日志点、关键字段、metrics/告警观察项 |
| 高风险发布 | 发布方式、开关策略、回滚路径、观察窗口 |

## 6. 验证等级

| 等级 | 含义 | 最低证据 |
|------|------|----------|
| `L1` | Build | `go build ./...` |
| `L2` | Unit/Package | 受影响包 `go test` |
| `L3` | Chain Regression | 主链路回归步骤和结果 |
| `L4` | Integration/Manual Evidence | 集成验证或手工验证证据 |
| `L5` | Migration/Release Safety | 迁移、灰度、回滚、安全说明 |

经验规则：
- 默认从 `L2` 起步
- 关键主链路改动至少 `L3`
- 外部依赖/联调至少 `L4`
- 数据库 schema、灰度、回滚类至少 `L5`

## 7. Git 规则

- 一个 `change-id` 对应一个工作分支
- 推荐分支名：
  - `feat/<change-id>`
  - `fix/<change-id>`
- 禁止在 `main/master` 直接开发
- 默认一个 task 一个 commit
- commit message 固定格式：

```text
[<change-id>] <中文简述>
```

禁止：
- AI 自动 push
- AI 自动 merge 主分支

## 8. 高风险硬规则

### 资金

- 涉及余额、扣款、退款、冻结、授信等逻辑时：
  - `spec.md` 必须标 `⚠️ REQ-HUMAN-REVIEW`
  - 没有人审确认前，禁止 commit

### 状态流转

- 禁止直接改状态字段
- 必须有集中校验入口或状态机

### 权限

- 必须有显式权限校验代码
- 校验必须发生在写操作前

### 敏感信息

- 禁止硬编码 AK/SK、密码、Token、证书私钥
- 禁止在日志打印手机号、身份证、银行卡、Cookie、密码等敏感信息

## 9. Golang 编码底线

- 默认使用 `log/slog`
- 禁止 `fmt.Println`、`log.Println` 充当业务日志
- 错误必须用 `%w` 包装
- 禁止吞错，如 `_ = err`
- 魔法值要提成常量
- 写接口要考虑幂等
- 外部调用必须传 `context` 并设置超时，默认 3 秒
- 金额用 `int64`，单位分
- 时间用 `time.Time`
- 新增 Goroutine 要有退出机制，优先 `errgroup.WithContext`

## 10. Review 看什么

### Stage 1: Spec Compliance

固定检查 5 项：
1. 缺失实现
2. 多余实现
3. 理解偏差
4. 业务规则落地
5. 对外契约准确性

### Stage 2: Code Quality

重点看：
- Critical：安全、资金、并发、数据丢失
- Important：吞错、context、参数校验、兼容风险、可观测性风险
- Minor：注释、Go doc、import 清理

## 11. 并发治理

- 仓库允许多个 change 同时存在
- 默认不允许并行改同一文件或同一主链路
- 有依赖时，在 `spec.md` 写 `depends_on`
- 判断可并行时，在 `tasks.md` 解释并发安全理由
- 发现冲突后，先记录到 `spec.md` / `log.md`，再决定暂停还是重排

## 12. 真实使用顺序

### 接入已有项目

1. 先 `/init`
2. 校验 `rules/project-context.md` 是否真实
3. 选一个低风险需求跑 `/propose -> /apply -> /review`
4. 试点阶段保留人工 review

### 维护这套 harness

建议阅读顺序：
1. `Golang/.claude/CLAUDE.md`
2. `changes/examples/user-create-api/`
3. `changes/examples/user-create-api-fix/`
4. `knowledge/pilot-checklist.md`

## 13. 会话开始时应自检

每次正式执行前，先确认：
- 已读取 `rules/`
- 是否存在真实进行中的 change
- 当前分支是否安全
- 当前 change 是否有依赖或冲突
- 本次最低验证等级是什么

## 14. 最短记忆版

```text
先 /init，再 /propose。
没有 spec 不写代码。
按 task 小步提交。
改代码就改文档。
review 阶段 spec 必须和代码一致。
高风险变更必须把兼容、回滚、观测写清楚。
不在 main 上开发，不自动 push/merge。
```
