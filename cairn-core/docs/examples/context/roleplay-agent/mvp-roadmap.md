# MVP 路线图

## 1. 总体阶段

| 阶段 | 目标 | 包含内容 | 明确不做 | 推荐后续命令 |
|------|------|----------|----------|--------------|
| Phase 0 | 建立可运行骨架 | Web 应用骨架、基础配置、基础对话接入 | 复杂用户体系 | `cc-propose bootstrap-roleplay-app` |
| Phase 1 | 打通练习主链路 | 角色模板选择、会话创建、多轮对话 | 历史记录 | `cc-propose roleplay-session-core` |
| Phase 2 | 增加反馈闭环 | 练习结束反馈、基础总结结构 | 高级评分与对比 | `cc-propose feedback-summary` |

## 2. MVP 交付顺序

1. 先建立项目骨架与运行链路
2. 再打通练习主链路
3. 最后补反馈闭环

## 3. 首批推荐 Change

| 阶段 | change-id 建议 | 目标 | 依赖 | 风险 |
|------|----------------|------|------|------|
| Phase 0 | bootstrap-roleplay-app | 建立项目骨架 | 无 | 技术方向未完全冻结 |
| Phase 1 | roleplay-session-core | 打通练习主流程 | bootstrap-roleplay-app | 对话状态边界 |
| Phase 2 | feedback-summary | 输出结构化反馈 | roleplay-session-core | 反馈质量与稳定性 |

## 4. 风险与观察点

| 类型 | 描述 | 建议处理方式 |
|------|------|--------------|
| LLM 依赖 | 对话和反馈质量依赖模型能力 | 首期先做可接受而非完美输出 |
| 范围膨胀 | 用户可能很快希望支持自定义角色与历史记录 | 明确先不做 |

## 5. 下一步建议

- 建议先执行：`cc-propose bootstrap-roleplay-app`
- 建议先定义的 change：项目骨架、练习主链路、反馈总结
- 暂不建议立即进入的范围：评分系统、历史记录、多人模式
