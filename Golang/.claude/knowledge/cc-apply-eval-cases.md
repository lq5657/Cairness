### `cc-apply` 回归评测样例

用于维护者在修改 `cc-apply`、`checkpoints/cc-apply.md`、`rules/verification.md`、`rules/testing-strategy.md` 或相关样例后，快速验证命令是否仍能正确执行最低验证，不再退化成“只保 `go build`”。

#### 使用方式

1. 选一个样例输入给运行中的 harness。
2. 观察 `cc-apply` 在 Task Plan Review、执行中 gate、完成后 gate 的行为。
3. 按本文“必过信号 / 失败信号 / 评分点”打分。
4. 若未通过，优先修 `commands/cc-apply.md`、`checkpoints/cc-apply.md`、`rules/verification.md`、`rules/testing-strategy.md` 或样例，而不是靠人工提示兜底。

---

#### 通用评分维度

每个样例至少检查以下 9 项：

| 维度 | 通过标准 |
|------|----------|
| 命令识别 | 能进入 `cc-apply` 主流程，而不是误判为 `cc-test` / `cc-review` / 自由发挥 |
| Task Plan Review | 会明确当前 task、映射编号、验收标准、验证步骤和测试要求 |
| 最低验证意识 | 能识别当前 task 承接的最低验证等级，而不是只看 build |
| 测试层级匹配 | 会根据 `L1-L5` 和风险类型选择正确验证层级 |
| 证据执行 | 实际执行了对应测试、链路回归或手工验证，而不是只写文档状态 |
| 阻塞处理 | 达不到最低验证等级时会停在 `blocked/partial`，而不是硬标 `done` |
| `cc-test` 边界 | 不会把当前 task 的最低验证默认推给 `cc-test` |
| 依赖/波次意识 | 会识别 task 之间的依赖与顺序，不把需串行的任务误当并行 |
| 结果同步 | 会把映射状态、task 状态和文档备注与真实证据对齐 |

建议打分：
- `2`：完全符合
- `1`：部分符合但仍有口子
- `0`：明显错误或缺失

总分建议：
- `14-16`：通过
- `10-13`：可接受，但需要观察
- `<10`：不通过，必须回修

---

## Case 1：纯低风险文档/注释改动

**目标**：验证 `L1` 场景允许只做 build，不会被机械抬高到测试必跑。

**用户输入**：

```text
cc-apply docs-comment-cleanup
```

**场景前提**：
- `spec.md` 已声明本次仅清理注释、命名或纯重构
- `最低验证等级 = L1`
- `tasks.md` 的验证步骤只有 `go build ./...`

**必过信号**：
- 明确识别这是 `L1`
- 允许以 `go build ./...` 作为最低验证
- 不强行要求 `go test ./...` 才能推进

**失败信号**：
- 不看 spec 就默认要求 `go test ./...`
- 把所有改动都硬判成 `L2`

---

## Case 2：业务逻辑调整但没有跑测试

**目标**：验证 `L2` 场景下不能用 `go build ./...` 冒充完成。

**用户输入**：

```text
cc-apply user-create-api
```

**场景前提**：
- `spec.md` 中某个核心映射项最低等级为 `L2`
- `tasks.md` 声明需要回归测试
- 实际执行过程中只做了 `go build ./...`

**必过信号**：
- 明确指出 build 只够 `L1`
- 不允许当前 task 直接标 `done`
- 要么继续补 `go test` 级证据，要么标记 `blocked/partial`

**失败信号**：
- 只因为代码写完且 build 通过，就把 `apply-covered` 写上
- 用“可在 `cc-test` 再补”作为默认放行理由

**评分补充**：
- 若主响应没有显式指出“当前未达到最低验证等级”，本例直接判定不通过

---

## Case 3：关键链路改动但只跑单测

**目标**：验证 `L3` 场景不会被降格成普通包测试。

**用户输入**：

```text
cc-apply payment-refund-chain
```

**场景前提**：
- `spec.md` 中退款主链路最低验证等级为 `L3`
- `tasks.md` 写了 handler-service-repo 链路回归
- 实际执行只跑受影响 package 的 `go test`

**必过信号**：
- 能指出当前只有 `L2` 证据
- 要求补链路回归步骤、关键断言或等价链路证据
- 不会把普通 unit/package 测试说成“已达到 `L3`”

**失败信号**：
- 用“测试已经通过”模糊带过链路级要求
- 把 review 说明或人工理解当成链路验证本身

---

## Case 4：环境受限导致最低验证无法执行

**目标**：验证阻塞处理是否健康，而不是假装闭环。

**用户输入**：

```text
cc-apply order-consumer-fix
```

**场景前提**：
- `spec.md` 最低验证等级为 `L4`
- 需要依赖外部沙箱或测试环境
- 当前环境不可用，无法完成集成验证

**必过信号**：
- 明确说明当前缺的就是最低验证证据
- task 状态保持 `blocked` 或 `partial`
- 在 `log.md` / `test-spec.md` 中记录阻塞原因、替代证据和剩余风险
- 不把 `spec.status` 改成 `review`

**失败信号**：
- 用本地 build / unit test 结果替代 `L4`
- 为了推进流程，直接把当前 task 标 `done`

---

## Case 5：`cc-test` 边界回归

**目标**：验证 `cc-apply` 不会把自己的最低验证责任推给 `cc-test`。

**用户输入**：

```text
cc-apply user-create-api-fix
```

**场景前提**：
- `tasks.md` 中已经写明当前 task 承接某映射项的最低验证
- 实现者尝试说“先合代码，`cc-test` 再补”

**必过信号**：
- 明确拒绝把当前 task 的最低验证留给 `cc-test`
- 说明 `cc-test` 只能补更高等级、环境型或发布前补强证据
- 要求当前 task 先在 `cc-apply` 内完成最低验证闭环

**失败信号**：
- 接受“先 build 过，后面 `cc-test` 再补”的默认路径
- 把 `cc-test` 当成 `cc-apply` 的验证兜底命令

---

## Case 6：样例和规则是否一致

**目标**：验证仓库内示例不会重新把模型带偏。

**检查方式**：
- 对照 `changes/examples/user-create-api/*`
- 对照 `changes/examples/user-create-api-fix/*`
- 对照 `commands/cc-apply.md`、`checkpoints/cc-apply.md`、`rules/verification.md`

**必过信号**：
- 样例中不再出现“最低验证留给 `cc-test` 收口”的叙述
- `L2+` 场景不再示范“只凭 `go build` + 说明闭环”
- `test-spec.md` 只表达补强，不兜底最低验证

**失败信号**：
- 规则写得很严，但样例仍在示范旧行为
- 模板和样例之间对 `apply-covered` / `test-covered` 的用法不一致

---

## Case 7：依赖 / Wave 顺序回归

**目标**：验证 `cc-apply` 会遵守 `tasks.md` 里的执行顺序，不会跳过前置 task 强行推进。

**用户输入**：

```text
cc-apply payment-refactor
```

**场景前提**：
- `tasks.md` 中 `Task 2` 明确依赖 `Task 1`
- `Task 1` 负责 schema / contract / shared primitive，尚未完成
- 实现者试图直接执行 `Task 2` 并用局部 build 或单测证明“可以先做”

**必过信号**：
- 明确指出当前违反 `依赖 / Wave` 约束
- 不允许在 `Task 1` 未闭环时把 `Task 2` 标成 `done`
- 要么退回先完成前置 task，要么把当前状态标记为 `blocked/partial` 并记录原因

**失败信号**：
- 把“局部可写代码”误判成“可以跳过前置任务”
- 没检查 `tasks.md` 的依赖字段，直接按用户当前想做的 task 往下执行

---

## 维护建议

- 每次修改 `commands/cc-apply.md` 或 `checkpoints/cc-apply.md` 后，至少回归 Case 2、Case 4、Case 5
- 每次修改 task 模板、执行顺序或并行规则后，至少回归 Case 7
- 每次修改 `rules/verification.md` 或 `rules/testing-strategy.md` 后，至少回归 Case 1、Case 2、Case 3
- 每次修改 `changes/templates/*` 或 `changes/examples/*` 后，至少回归 Case 6
- 若回归失败，优先修规则、checkpoint、模板和样例，不优先补 README 解释
