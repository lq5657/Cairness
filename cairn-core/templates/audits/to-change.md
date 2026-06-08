### Audit → Change 桥接模板

文件位置：`.cairness/audits/<audit-id>/to-change.md`

用途：
- 把 `cc-inspect-codebase` 产出的审查报告，转成一个可以进入 `cc-propose` 的正式 change 草稿
- 避免人工从 Findings 手工重写一遍 spec，降低信息丢失和语义漂移
- 这不是 `.cairness/changes/<change-id>/spec.md` 的替代品，而是它的上游桥接材料

使用方式：
1. 先完成 `.cairness/audits/<audit-id>/report.md`
2. 选出本次要治理的 Findings，避免把不相关问题打包进一个 change
3. 填写本模板
4. 再生成 `.cairness/changes/<change-id>/spec.md` 与 `tasks.md`

```text
audit_id: <audit-id>
change_id: <planned-change-id>
created_at: YYYY-MM-DD HH:MM
owner: Claude Code / Maintainer
status: draft
```

#### 1. 来源审查

- 审查报告：`.cairness/audits/<audit-id>/report.md`
- 审查模式：`architecture` / `logic` / `observability` / `test-debt`
- 审查范围：
- 本次选中的 Findings：
  - `Critical/Important/Minor` + 一句话摘要

#### 2. 为什么转成 change

- 不修会带来的风险：
- 为什么现在修：
- 为什么这些问题适合放在同一个 change：
- 为什么没有纳入的 Findings 不在本次处理：

#### 3. Change 边界

- **本次 change 要解决什么**：
- **本次 change 不解决什么**：
- **是否只做治理，不做新功能**：是/否
- **建议 change 类型**：
  - `refactor`
  - `bugfix`
  - `hardening`
  - `observability`
  - `test-debt`

#### 4. Findings 映射

| Audit Finding | 风险级别 | 拟落到 spec 的位置 | 拟落到 task 的位置 | 备注 |
|---------------|----------|--------------------|--------------------|------|
| 例如：Handler 承载业务规则 | Important | §2 代码现状 / §8 风险与关注点 | Task 1 | 收紧边界 |

#### 5. 建议写入 spec 的内容

##### 5.1 背景与目标

- 建议背景：
- 建议目标：

##### 5.2 代码现状（Research Findings）

- 直接复用 audit 里的哪些证据：
- 哪些证据还需要补代码定位：

##### 5.3 功能点 / 治理点

- [ ] 治理点 1：
- [ ] 治理点 2：

##### 5.4 风险与关注点

- 是否涉及：
  - 资金：
  - 状态流转：
  - 权限：
  - 数据库：
  - 对外接口：
  - 配置：
  - 可观测性：
  - 测试债：

#### 6. 建议写入 tasks 的内容

| Task | 目标 | 建议文件范围 | 验收标准 |
|------|------|--------------|----------|
| Task 1 | 例如：收紧边界 | `handler`, `service` | 业务规则不再停留在入口层 |

拆分原则：
- 一个 change 只治理一类主问题，避免把架构、逻辑、可观测性、测试债全部混在一起
- 每个 task 仍保持 3-5 个文件的原子范围
- 若 audit 提出了多个方向的问题，优先拆成多个 change，而不是一个大杂烩 change

#### 7. 验证迁移

| Audit 结论 | 建议验证等级 | 建议测试层级 | 原因 |
|------------|--------------|--------------|------|
| 例如：Handler 错误映射不稳定 | `L3` | `transport` + `chain` | 需要同时证明协议映射和主链路行为 |

#### 8. 依赖与并发

- 是否依赖其他进行中 change：
- 是否建议 `parallel_safe = false`：
- 是否存在同文件或同调用链冲突：

#### 9. 建议生成的 change 元数据

```text
change_id: <planned-change-id>
status: propose
depends_on: []
parallel_safe: true | false
branch: feat/<planned-change-id>
complexity: 🟢简单 | 🟡中等 | 🔴复杂
```

#### 10. 进入 `cc-propose` 前自检

- [ ] 只选中了真正要处理的 Findings，没有把审查报告整份搬进一个 change
- [ ] 已明确本次 change 的边界和不处理项
- [ ] 已把 audit 证据映射到 spec 的“代码现状”与“风险”章节
- [ ] 已把主要治理动作映射到 tasks
- [ ] 已选定最低验证等级和测试层级
- [ ] 若涉及高风险规则，已准备好数据库 / 接口 / 配置 / 可观测性 / 发布回滚章节
