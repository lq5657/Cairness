# cc-propose

## 用途

创建变更提案，产出 `changes/<change-id>/spec.md` 与 `tasks.md`。

## 命令格式

- `cc-propose <需求描述>`

## 执行流程

1. Research：读代码、查链路、识别现有实现
2. 提问澄清：逐个提问并等待回答
3. YAGNI 裁剪：剔除“未来可能需要”的功能
4. 生成 Spec：重点补齐背景、功能点、风险、待澄清
5. 生成 Tasks：按 3-5 文件粒度拆 task
6. HARD-GATE：等待用户确认再进入 `cc-apply`

## 强制边界

- `spec.md` 的“待澄清”章节全部解决前，禁止进入 `cc-apply`
- 创建提案时必须检查是否与现有 change 存在文件级或链路级冲突
- 若存在明显依赖，必须在 `spec.md` 中记录 `depends_on`
- 若涉及 DB、API、配置、可观测性、测试、发布等专题，必须增量读取对应规则

## 失败处理

- 若提问后仍有未解决澄清项，保持 `status: propose`
- 若已产出部分 spec/tasks 但信息不足以继续，记录为 `partial` 或 `blocked`

## 建议读取

- `context/project-context.md`
- `checkpoints/cc-propose.md`
- 相关专题规则
