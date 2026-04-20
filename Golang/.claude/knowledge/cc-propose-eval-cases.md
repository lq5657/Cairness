### `cc-propose` 回归评测样例

用于维护者在修改 `cc-propose`、`checkpoints/cc-propose.md` 或相关提问策略后，快速验证命令是否仍能正确处理存量需求、change 澄清边界，以及与项目路线图的桥接关系。

#### 使用方式

1. 选一个样例输入给运行中的 harness。
2. 只观察 `cc-propose` 的前半段行为，不要求真的生成最终 `spec.md`。
3. 按本文“必过信号 / 失败信号 / 评分点”打分。
4. 若未通过，先修 `commands/cc-propose.md` 或 `checkpoints/cc-propose.md`，再回归。

---

#### 通用评分维度

每个样例至少检查以下 8 项：

| 维度 | 通过标准 |
|------|----------|
| 命令识别 | 能进入 `cc-propose` 主流程，而不是误判为 `cc-init` / `cc-preflight` / 其他命令 |
| 项目边界判断 | 能识别当前是新项目定义还是已有项目 change |
| Roadmap 对齐 | 若存在项目级定义，能检查本次 change 是否与当前 phase / backlog 对齐 |
| 问题贴合度 | 第一轮问题直接围绕用户原始需求中的核心名词、动作和场景 |
| 理解回显 | 每轮追问前或追问后，能输出当前理解摘要 |
| 技术问题后置 | 在需求未收敛前，不优先追问技术栈、运行形态、存储、模型接入 |
| 范围意识 | 能识别本次要做 / 本次不做，不无限扩写需求 |
| 收敛能力 | 能在合理轮数内把问题收敛到可提案状态，或明确进入 `brainstorm-needed` |

建议打分：
- `2`：完全符合
- `1`：部分符合但有明显跑偏
- `0`：未体现或明显错误

总分建议：
- `14-16`：通过
- `10-13`：可接受，但需要观察
- `<10`：不通过，必须回修

---

## Case 1：新项目请求应路由到 `cc-new-project`

**目标**：验证新项目请求不会继续在 `cc-propose` 中硬做。

**用户输入**：

```text
cc-propose 我要实现一个能够和用户进行对话的智能体，它能作为不同的角色，模拟指定场景下的对话
```

**必过信号**：
- 明确指出这属于项目级定义
- 建议改走 `cc-new-project`
- 不继续在 `cc-propose` 内生成 change 提案

**失败信号**：
- 明明是项目级请求，仍然在 `cc-propose` 中长聊实现细节
- 或者退化成“建议先执行 cc-init”

---

## Case 2：已有项目的正常 change

**目标**：验证存量项目 change 仍保留“先 Research，再提案”的主路径。

**用户输入**：

```text
cc-propose 给现有用户服务增加批量冻结用户接口，要求保留审计日志和原有权限校验
```

**必过信号**：
- 先做本地 Research，识别现有冻结/权限/审计链路
- 提问聚焦业务规则缺口，例如冻结条件、批量失败语义、审计字段
- 不把它错误切回项目级定义讨论

**失败信号**：
- 不查代码就直接提方案
- 完全忽略存量上下文

---

## Case 3：存在项目路线图时的 backlog 对齐

**目标**：验证 `cc-propose` 能把 change 放回项目 roadmap 语义中收敛。

**用户输入**：

```text
cc-propose feedback-summary
```

**场景前提**：
- 已存在 `context/project-definition.md`
- 已存在 `context/mvp-roadmap.md`
- 推荐 backlog 中 `feedback-summary` 位于 Phase 2，依赖 `roleplay-session-core`

**必过信号**：
- 先确认本次 change 在 roadmap 中的位置
- 检查依赖是否满足
- 在 spec 中体现 phase / backlog 对齐关系

**失败信号**：
- 完全忽略 roadmap / phase / 依赖关系
- 把项目级 backlog 名称直接原样塞进 change，而不做范围收敛

---

## Case 4：抽象 change 请求但仍属于已有项目

**目标**：验证 `brainstorm-needed` 仍可用于 change 级抽象需求，而不会滑回项目级定义。

**用户输入**：

```text
cc-propose 让现有告警中心更智能一点，减少无效告警
```

**必过信号**：
- 明确进入 `brainstorm-needed` 或等价短收敛
- 追问“更智能一点”“无效告警”分别具体指什么
- 能把抽象词拆成可回答的问题，而不是泛泛追问“技术栈是什么”
- 收敛后能回到提案主流程，而不是停留在无边界闲聊

**失败信号**：
- 接受抽象描述，不继续具体化
- 直接跳到系统架构、模型、数据库
- 脑暴过程产出独立长期文档，脱离 `cc-propose`

---

## Case 5：项目级 backlog 明显偏离时的阻断

**目标**：验证当请求明显偏离 roadmap 时，`cc-propose` 会先指出偏差而不是硬提案。

**用户输入**：

```text
cc-propose growth-dashboard
```

- 已存在 `context/mvp-roadmap.md`
- 当前 roadmap 还处于 Phase 0 / Phase 1
- `growth-dashboard` 不在推荐 backlog，且与当前 MVP 无直接关系

**必过信号**：
- 先指出偏离当前 roadmap / MVP
- 要求确认是否要调整优先级或更新项目级路线图
- 不把偏离项直接当成普通 change 提案

**失败信号**：
- 直接忽略 roadmap 偏差继续生成 spec/tasks
- 把项目级优先级冲突当成普通细节处理

---

## 维护建议

- 每次修改 `commands/cc-propose.md` 或 `checkpoints/cc-propose.md` 后，至少回归 Case 2、Case 3、Case 5
- 若修改了 `brainstorm-needed` 判定，再额外回归 Case 4
- 若修改了 `cc-new-project` 与 `cc-propose` 的路由边界，再额外回归 Case 1
- 若回归失败，优先修命令规则和 checkpoint，不优先补 README 解释
