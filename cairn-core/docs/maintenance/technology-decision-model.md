# 技术决策模型

## 目的

技术决策是影响架构、依赖、验证、部署或长期维护的项目级或变更级约束。

Harness 将决策协议保持语言无关，并将语言特定选项移入运行时技术目录。

## 运行时资产

```text
.claude/runtime/protocol.yaml
.claude/runtime/languages/<language>.yaml
.claude/runtime/technology/<language>.yaml
.claude/schemas/technology-decision-catalog.schema.json
```

`protocol.yaml` 定义通用行为：

- 在加载技术目录之前，先解析当前活跃的语言 profile。
- 加载活跃语言 profile 声明的目录。
- 仅询问由当前项目或变更上下文触发的决策。
- 展示推荐方案、备选方案、采纳理由、排除理由和待定风险。
- 对阻断性 `P0` 决策要求用户显式确认。
- 将未解决的选择记录为 pending，而非最终架构。

`runtime/languages/<language>.yaml` 指向活跃目录：

```yaml
technology_decisions:
  catalog: .claude/runtime/technology/<language>.yaml
```

`runtime/technology/<language>.yaml` 包含语言特定的决策组和选项。Go 可以涉及 `chi`、Gin、GORM、`sqlc`、NATS、Kafka 和 `slog`；其他语言 profile 应提供各自的等价选项，而不改变通用协议。

## 语言 Profile 解析

活跃语言 profile 在技术决策之前解析：

1. 从 `.cairness/context/project-definition.md` 或 `.cairness/context/project-context.md` 读取显式项目状态。
2. 如果项目状态缺失，检查各语言 profile 声明的仓库标记文件。
3. 如果多个 profile 匹配或没有 profile 匹配，询问用户选择。
4. 对于没有代码事实的新项目，即使只安装了一个 profile，也必须询问用户确认语言/生态系统。
5. 确认后，加载所选 profile 的技术目录。

`language_profile.default` 仅是本 Harness 包的内置默认 profile。它不得在新项目中静默决定语言。

## 命令行为

`cc-new-project` 使用目录进行项目级选择。它应询问影响初始架构、依赖集或 MVP 路线的 `P0` 决策。当非阻断性 `P1` 决策不影响第一个变更时，可以延后处理。

`cc-propose` 使用目录进行变更级选择。它应仅询问由当前变更触发的决策组。例如，添加 MQ 消费者可能触发 `async_messaging`；修改一个简单 handler 不应重新打开整个项目技术栈。

运行时 readset 将此建模为按需输入：`cc-propose` 不将语言技术目录包含在 `always_reads` 中；而是在 `conditional_reads.when_technology_decision_is_required` 下暴露它。提案必须先判断所请求的变更是否确实需要新的或变更的技术决策。如果不需要，应依赖项目上下文、dev map、现有代码和 topic rules，而非读取目录。

成熟替代方案检查与此相关但有所不同。技术目录提供经过筛选的项目或语言选项；成熟替代方案检查则询问当前问题是否已有成熟的本地模式、官方标准或成熟的开源方案值得在自定义实现之前进行比较。仅当本地复用不明确且自建成本、运维风险、依赖影响或长期维护成本有实质意义时才触发。结果记录在现有 `spec.md` 的成熟替代方案、方案对比和技术决策章节中。

`cc-init` 默认不加载目录。它应从上下文文件和低成本仓库证据中记录直接观察到的项目事实和未解决的未知项。未来的 `cc-enrich-context` 模式可能仅将目录作为现有项目的显式事实发现辅助工具；它必须记录观察到的选择和未解决的事实，而非要求用户重新选择技术——除非用户明确希望重新设计。

## 项目状态输出

项目级决策记录在：

```text
.cairness/context/project-definition.md
.cairness/context/architecture-outline.md
.cairness/context/project-context.md
.cairness/context/dev-map.md
```

变更级决策记录在：

```text
.cairness/changes/<change-id>/spec.md
.cairness/changes/<change-id>/log.md
```

## 确认标准

阻断性技术决策仅在输出包含以下内容时视为已解决：

- 选定方案。
- 已考虑的备选方案。
- 为什么选定方案适合本项目或本变更。
- 为什么被排除的方案当前不采用。
- 剩余风险或待跟进事项。
- 用户确认或显式的 pending 状态。

如果缺少用户确认，命令必须将决策保持为 pending，并避免将下游工作呈现为就绪状态。
