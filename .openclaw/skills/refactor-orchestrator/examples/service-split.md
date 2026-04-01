# Example: Service / Module Split

> 这是 `refactor-orchestrator` 的一个通用领域实例，展示如何把通用重构编排方法应用到
> “把职责过重的单体模块 / 脚本 / service 拆成边界更清晰的多个模块” 这类任务上。

## 1. 适用场景

当用户提出以下类型需求时，可参考本 example：

- “把这个大模块拆一下”
- “这个 service 太肥了，拆开”
- “把 orchestration 和 implementation 分开”
- “把一个大脚本拆成多个职责清晰的模块”
- “把调用、prompt、业务编排拆开”
- “这个文件什么都干了，帮我理清边界”

---

## 2. 典型目标

目标通常不是“拆得更多”，而是：

- 每个模块职责更单一
- 依赖方向更清晰
- 调用链更可理解
- 测试和验证更容易
- 后续修改不再牵一发动全身

---

## 3. 关键语义约束示例

- orchestration 层只负责流程编排，不直接承担底层实现细节
- client / adapter 层只负责外部调用，不混入业务判断
- builder / formatter / parser 层只负责构造与转换，不承担状态管理
- service 层只负责明确业务职责，不吞并所有工具逻辑
- shared utilities 不应偷偷携带强业务语义

---

## 4. 一票否决风险示例

- 模块拆完后边界更乱，而不是更清楚
- 拆分后引入循环依赖
- 看起来拆成多个文件，实际耦合仍然不变
- orchestration / service / client 职责仍然混杂
- 配置、状态、异常处理被分散到无法维护
- 旧入口未收口，导致新旧路径并存

---

## 5. 推荐推进顺序

1. 审计当前模块职责图
2. 标出职责过载点、隐藏耦合点、依赖方向
3. 定义目标边界
4. 一次只拆一个边界
5. 独立 QA 验证边界是否真的更清晰
6. 再清理旧调用路径和兼容残留

---

## 6. 典型拆分形态

### 形态 A：单体 analyzer / manager / handler 拆分
例如把一个超大的 `xxx_analyzer.py` 拆成：

- `xxx_client.py`
- `xxx_prompt_builder.py`
- `xxx_service.py`
- `xxx_parser.py`

### 形态 B：脚本型流程拆分
例如把一个大脚本拆成：

- entrypoint
- orchestrator
- business service
- storage adapter
- validation helper

### 形态 C：胖 service 拆分
例如把一个职责过重的 service 拆成：

- read service
- write service
- validation service
- transform layer

---

## 7. QA 特别关注点

QA 在这类任务中应特别检查：

- 新模块边界是否真的更清晰
- 是否仍存在隐藏双入口
- 是否存在循环依赖
- 是否只是“复制粘贴式拆文件”
- 旧调用路径是否仍然偷偷保留
- 配置 / 状态 / 异常处理是否变得更混乱
- 文档和实际调用链是否一致

---

## 8. 状态文件可注入的约束示例

### 关键语义约束
- orchestration 不直接写底层调用细节
- client 不承担业务判断
- parser 不承担状态流转
- service 不吞并所有职责

### 一票否决风险
- 拆分后边界更乱
- 循环依赖
- 新旧入口并存
- 只是形式拆分，没有真实解耦

### 当前阶段明确不做
- 不顺手改全部接口风格
- 不顺手做性能优化
- 不顺手做全量目录重构
- 不顺手改无关业务逻辑

---

## 9. 与当前新闻链路项目的关系

这个 example 与当前新闻链路重构高度相关。

例如：
- `llm_news_analyzer.py` 这类职责过重模块，就很适合用本 example 的思路拆成
  - client
  - prompt builder
  - analysis service
  - parser / result normalizer

因此：
- 通用流程看 `SKILL.md`
- 通用模板看 `references/`
- 如果任务本质是“职责拆分”，优先参考本 example
