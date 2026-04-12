# cc-inspect-codebase

## 用途

`cc-inspect-codebase` 用于对存量项目做显式、定向的审查。
它适用于“暂时没有新需求，但希望先发现问题”的场景。

它不是：
- 启动阶段默认动作
- `cc-init`
- `cc-review`

## 触发场景

适用于：
- 存量项目健康体检
- 想先识别架构、逻辑、可观测性、测试债问题
- 想把审查发现转成后续治理 change

不适用于：
- 启动时自动执行
- 已有 change 的实现审查
- 项目事实初始化识别
- 直接编码实现

## 命令格式

- `cc-inspect-codebase <mode>`
- `cc-inspect-codebase <mode> <scope>`

## 参数定义

`<mode>` 只能是：
- `architecture`
- `logic`
- `observability`
- `test-debt`

`<scope>` 可表示：
- 全仓
- 某目录
- 某模块
- 某链路
- 某业务主题

未提供 `scope` 时，默认按全仓执行。

## 输出

产出：
- `audits/<audit-id>/report.md`

不产出：
- `changes/<change-id>/spec.md`
- 业务代码修改
- 自动修复结果

## 与其他命令的边界

与 `cc-init` 的区别：
- `cc-init` 识别项目事实
- `cc-inspect-codebase` 识别项目问题

与 `cc-review` 的区别：
- `cc-review` 基于某个已有 change 做实现审查
- `cc-inspect-codebase` 不依赖已有 change，可独立对存量项目审查

与启动阶段的区别：
- 启动阶段只做会话态检查
- `cc-inspect-codebase` 必须由用户显式触发

## 允许读取的范围

允许读取：
- 与当前 `mode` / `scope` 直接相关的目录、代码、配置
- `rules/project-context.md`
- 必要的架构、配置、测试相关规则

不建议读取：
- 与当前审查模式无关的全量专题规则
- 与当前 `scope` 无关的大量代码区域

## 模式定义

### architecture

关注：
- 分层
- 依赖方向
- 模块边界
- 抽象是否失控
- 耦合是否异常

### logic

关注：
- 业务规则是否闭合
- 状态流转是否合法
- 幂等、权限、错误语义是否正确
- 链路上的关键前置条件是否缺失

### observability

关注：
- 日志
- trace
- metrics
- 告警
- 异步链路观测能力

### test-debt

关注：
- 测试覆盖缺口
- 回归证据不足
- 测试分层失衡
- 代码可测性差的问题

## 默认执行流程

1. 确认 `mode`
2. 确认 `scope`；若缺省则按全仓
3. 读取 `project-context.md`
4. 只加载本 `mode` 需要的最小规则
5. 对 `scope` 范围内代码和配置做证据化审查
6. 输出 Findings，按级别分组
7. 明确哪些问题建议转成 change
8. 结束，不自动进入 `cc-promote-audit`

## 证据要求

- 每个关键结论都必须有代码、配置、调用链或目录结构证据
- 禁止只给抽象评价，不给证据
- 禁止把个人偏好表述成缺陷结论

## 失败处理

若 `mode` 不合法，必须停止并要求补充正确 `mode`。
若 `scope` 过大导致审查成本过高，可建议收敛 `scope`。
若证据不足，必须降低结论强度，不得伪造结论。

## 执行后建议

审查完成后，通常有两种后续：
- 若仅记录问题：结束
- 若决定治理问题：执行 `cc-promote-audit <audit-id> <change-id>`

## 需要加载的附加文件

- `checkpoints/cc-inspect-codebase.md`
- `rules/project-context.md`
- 按 `mode` 增量加载相关专题规则
