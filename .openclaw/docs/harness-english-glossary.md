# Harness 术语表（英文 → 中文 → 在 harness 里的作用）

> 来源语境：主要基于 Anthropic《Harness design for long-running application development》与 OpenAI《Harness engineering》相关讨论整理。
> 目标：帮助在设计 agent engineering harness / ACP harness 时，快速对齐术语含义与系统作用。

---

## long-running
- **中文**：长时间运行的
- **在 harness 里的作用**：描述任务会持续很久、跨多个步骤和阶段。harness 需要支持长周期执行、状态保持、上下文管理、失败恢复，而不是只处理一次性短调用。

## long-running agent
- **中文**：长时运行智能体
- **在 harness 里的作用**：指能够在数小时、多轮迭代中持续推进任务的 agent。harness 需要为它提供稳定的执行环境、交接机制和控制回路。

## frontend
- **中文**：前端
- **在 harness 里的作用**：作为任务领域之一，要求 harness 能支持 UI 生成、页面运行、交互验证、截图与浏览器操作等能力。

## high-quality frontend designs
- **中文**：高质量前端设计
- **在 harness 里的作用**：说明 harness 不只追求“能运行”，还要支持对美观性、一致性、交互质量等更高层目标的评估与优化。

## without human intervention
- **中文**：无需人工中途介入
- **在 harness 里的作用**：体现 harness 的目标之一是让 agent 自主推进任务。为了做到这一点，harness 需要具备明确的约束、反馈、验证和恢复机制。

## prompt engineering
- **中文**：提示词工程
- **在 harness 里的作用**：用于影响模型行为，但通常只是基础层。文章强调仅靠 prompt engineering 不够，最终要靠 harness 提供更稳的工程结构。

## hit ceilings
- **中文**：撞到天花板 / 遇到提升瓶颈
- **在 harness 里的作用**：提示系统仅靠提示词优化会遇到上限，因此需要通过分工、反馈回路、上下文机制等 harness 设计继续提升能力。

## GAN-inspired
- **中文**：受 GAN（生成对抗网络）启发的
- **在 harness 里的作用**：表示借用“生成者 + 评估者”相互博弈、推动质量提升的结构思想，用于多 agent harness 设计。

## Generative Adversarial Networks (GANs)
- **中文**：生成对抗网络
- **在 harness 里的作用**：不是直接用 GAN 模型，而是借其“生成与判别分离”的思路来设计 generator/evaluator 角色分工。

## generator
- **中文**：生成者
- **在 harness 里的作用**：负责真正产出内容（如代码、界面、实现方案）的 agent。它是执行端，需要持续接收反馈并迭代。

## generator agent
- **中文**：生成型智能体 / 执行型智能体
- **在 harness 里的作用**：作为主要生产者，完成实现工作。harness 需要给它任务范围、上下文、工具和来自 evaluator 的反馈。

## evaluator
- **中文**：评估者
- **在 harness 里的作用**：负责独立审查 generator 的输出质量，防止系统只会“做”而不会“判”。

## evaluator agent
- **中文**：评估型智能体 / 审查型智能体
- **在 harness 里的作用**：承担 QA、评分、挑错、验收等职责。它是 harness 里的关键制衡力量，防止自评过宽。

## grading criteria
- **中文**：评分标准 / 评价准则
- **在 harness 里的作用**：把原本模糊的“好不好”转成明确维度，让 evaluator 能稳定打分、比较和反馈。

## subjective quality
- **中文**：主观质量
- **在 harness 里的作用**：说明某些任务（如设计）无法只靠自动测试判断，harness 需要额外的评审标准和审美/偏好校准机制。

## gradable
- **中文**：可评分的 / 可打分的
- **在 harness 里的作用**：表示任务质量可以被拆分成多个维度并进行相对稳定的评价，是 evaluator 能够工作的前提。

## few-shot examples
- **中文**：少样本示例
- **在 harness 里的作用**：用于校准 evaluator 的评判口径，减少评分漂移，让其更接近人类偏好或既定标准。

## score drift
- **中文**：评分漂移
- **在 harness 里的作用**：指评估标准随着时间或轮次逐渐不一致。harness 需要通过示例、固定标准或阈值来抑制漂移。

## baseline
- **中文**：基线 / 参照水平
- **在 harness 里的作用**：作为比较对象，用来衡量 harness 相对单 agent 或简单流程的提升幅度。

## go off the rails
- **中文**：脱轨 / 跑偏
- **在 harness 里的作用**：描述长任务中 agent 偏离目标的常见失败模式。harness 的一个核心价值就是减少这种跑偏。

## context window
- **中文**：上下文窗口
- **在 harness 里的作用**：决定模型一次能看到多少历史与输入，是长任务设计中的硬约束。

## context window fills up
- **中文**：上下文窗口被填满
- **在 harness 里的作用**：意味着历史过长，导致早期信息被挤掉、质量下降，因此需要 compaction、reset 或 handoff 机制。

## context anxiety
- **中文**：上下文焦虑
- **在 harness 里的作用**：指模型因为感觉上下文快满而提前草率收尾。harness 需要通过 reset、handoff 等设计来缓解这种行为。

## context reset
- **中文**：上下文重置
- **在 harness 里的作用**：清空旧上下文、开启干净的新会话，再通过结构化交接工件让新 agent 接着做。适合特别长、特别复杂的任务。

## compaction
- **中文**：上下文压缩
- **在 harness 里的作用**：将旧历史浓缩成摘要，让同一个 agent 继续工作。它保留连续性，但不一定能彻底消除上下文焦虑。

## clean slate
- **中文**：干净起点 / 空白起点
- **在 harness 里的作用**：指让 agent 以几乎无旧包袱的新上下文继续任务，是 context reset 的核心价值之一。

## handoff
- **中文**：交接
- **在 harness 里的作用**：把当前工作状态移交给后续 agent/session，使任务可以跨轮次、跨会话继续。

## artifact
- **中文**：工件 / 产物
- **在 harness 里的作用**：指结构化中间产物，如计划、状态摘要、评估报告、契约文件、日志等，是上下文传递和可追踪性的关键载体。

## handoff artifact
- **中文**：交接工件
- **在 harness 里的作用**：专门用于跨 session/agent 交接的结构化材料，帮助新执行者快速恢复现场。

## orchestration
- **中文**：编排 / 调度
- **在 harness 里的作用**：控制多个 agent、多个阶段、多个循环如何协同工作，是 harness 的调度骨架。

## orchestration complexity
- **中文**：编排复杂度
- **在 harness 里的作用**：说明多 agent、多阶段、多交接会增加系统复杂度，因此 harness 设计要关注控制成本和结构清晰度。

## self-evaluation
- **中文**：自我评估
- **在 harness 里的作用**：指 generator 自己评价自己的输出。文章指出这通常不可靠，因此 harness 应更偏向独立 evaluator。

## leniency
- **中文**：宽松 / 手下留情
- **在 harness 里的作用**：形容 evaluator 打分过于宽容。harness 需要设计更严格、怀疑式的评估者来抵消这种倾向。

## inclined to be generous
- **中文**：倾向于宽容给分
- **在 harness 里的作用**：进一步强调 LLM 评估时常常过于正面，因此 evaluator 需要单独调教和约束。

## skeptical
- **中文**：怀疑的 / 更挑剔的
- **在 harness 里的作用**：理想的 evaluator 风格。它不轻易通过，更容易发现隐藏问题，推动 generator 持续改进。

## tractable
- **中文**：更可处理的 / 更可控的 / 更容易做成的
- **在 harness 里的作用**：表示某种设计策略在工程上更现实。例如：单独训练/提示 evaluator 通常比让 generator 学会严厉自评更 tractable。

## feedback loop
- **中文**：反馈回路
- **在 harness 里的作用**：构成 agent 持续改进的核心机制。典型流程是：生成 → 评估 → 反馈 → 再生成。

## plateau
- **中文**：平台期
- **在 harness 里的作用**：表示多轮迭代后的改进会趋缓。harness 需要知道何时继续优化、何时止损或转向。

## one-feature-at-a-time
- **中文**：一次只做一个功能
- **在 harness 里的作用**：一种范围控制策略，避免任务过大导致 agent 失控，是长任务拆分的常见实践。

## sprint
- **中文**：冲刺 / 短开发周期
- **在 harness 里的作用**：把长任务拆成多个小周期，每轮聚焦明确范围，便于计划、验收和回滚。

## sprint contract
- **中文**：冲刺契约 / 本轮完成定义
- **在 harness 里的作用**：在 generator 开工前，由 generator 和 evaluator 先约定这一轮做什么、如何验收、什么叫 done。它是对齐预期的关键机制。

## bridge the gap
- **中文**：弥合差距 / 搭桥补缝
- **在 harness 里的作用**：通常指在高层 spec 与可测试实现之间补一层明确约定，让执行和验收真正接上。

## user stories
- **中文**：用户故事
- **在 harness 里的作用**：作为产品需求表达形式，帮助 planner 或 generator 理解“用户想完成什么”，再进一步转化为具体实现任务。

## version control
- **中文**：版本控制
- **在 harness 里的作用**：支撑变更跟踪、回滚、协作与 PR 流程，是长时智能体开发中的关键基础设施。

## verifiable
- **中文**：可验证的
- **在 harness 里的作用**：表示结果是否能通过测试、检查或明确标准被验证，是 evaluator 能可靠工作的基础。

## correctness
- **中文**：正确性
- **在 harness 里的作用**：关注结果“对不对”，如逻辑正确、接口正确、数据正确，是评价代码任务的重要维度。

## usability
- **中文**：可用性 / 易用性
- **在 harness 里的作用**：关注用户能否顺畅完成任务，不仅代码正确，还要真的好用。

## verifiable correctness and usability
- **中文**：可验证的正确性与可用性
- **在 harness 里的作用**：表示某些任务虽然复杂，但仍可通过测试、交互、检查等方式较稳定地判断是否达标。

## full-stack applications
- **中文**：全栈应用
- **在 harness 里的作用**：说明 harness 需要支持跨前端、后端、数据库、接口、验证等多个层面的任务，而不是只看单点代码。

## product depth
- **中文**：产品深度
- **在 harness 里的作用**：评价应用是不是只有表面 demo 感，还是具有真正完整、深入、可持续使用的功能设计。

## wall-clock time
- **中文**：真实耗时 / 钟表时间
- **在 harness 里的作用**：衡量一次 harness 运行在现实世界里花了多久，帮助评估系统成本与吞吐量。

## pivot
- **中文**：转向 / 换路线
- **在 harness 里的作用**：当当前方向效果不佳时，让 generator 不再死磕旧方案，而是切换到新的实现/设计路线。

## threshold
- **中文**：阈值
- **在 harness 里的作用**：规定某项评分或指标至少要达到多少，才能继续下一步。

## hard threshold
- **中文**：硬阈值
- **在 harness 里的作用**：低于阈值就直接失败，没有模糊空间。用于提高质量门槛的可执行性。

## faithful to the spec
- **中文**：忠实于需求说明 / 不跑偏于规格
- **在 harness 里的作用**：确保 generator 的实现没有偏离原始意图，是 planner、contract、evaluator 都要共同维护的目标。

## scope
- **中文**：范围
- **在 harness 里的作用**：定义一轮任务该做什么、不该做什么，是长任务控制失控风险的基础。

## scope management
- **中文**：范围管理
- **在 harness 里的作用**：防止任务无限膨胀，确保每轮工作量适合 agent 稳定完成。

---

## 一句话总结
这些词共同指向同一个设计方向：

> 一个好的 harness，不只是“把模型跑起来”，而是要通过分工、上下文管理、交接工件、反馈回路、评估标准、范围控制和验证机制，让 agent 能在长任务、复杂工程和多轮迭代中持续、可靠地推进工作。
