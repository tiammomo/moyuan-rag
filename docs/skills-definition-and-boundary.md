# Skills 定义与产品边界

## 为什么这个仓库里的 `skills` 不能直接照搬外部概念

当前仓库是一个以 RAG 为核心的知识问答系统，主链路是：

- 文档入库
- 混合检索
- 上下文拼装
- 机器人问答
- 召回评测

因此，这里的 `skills` 不应该被定义成“任意代码插件”或“运行时动态注入的远端能力”，否则会把现有系统从一个可控的 RAG 应用，拉向高风险的插件平台。

## 在本项目中的推荐定义

在这个仓库里，一个 `skill` 推荐被定义为：

> 一个可复用、可审核、可绑定到机器人或会话的“提示词与工作流包”，用于约束问答风格、增强特定场景下的 RAG 行为，并为机器人附加可解释的能力标签。

它更像：

- prompt bundle
- retrieval strategy preset
- answer formatting preset
- domain workflow template

而不是：

- 任意 Python 代码执行器
- 任意 shell 脚本插件
- 在请求过程中即时拉取并执行的远端包

## 一个 skill 应该包含什么

推荐最小结构：

```text
skill/
├── skill.yaml
├── SKILL.md
├── prompts/
│   ├── system.md
│   ├── retrieval.md
│   └── answer.md
├── templates/
│   └── examples.json
└── assets/
    └── icon.png
```

其中：

- `skill.yaml`
  - 元数据、版本、作者、兼容范围、依赖声明
- `SKILL.md`
  - 面向人类的说明文档
- `prompts/*.md`
  - 真正给机器人或流程使用的提示模板
- `templates/`
  - 样例输入、输出模板、结构化约束
- `assets/`
  - 图标、截图等展示资源

## 在 RAG 产品里的具体作用

推荐把 `skill` 作用在这三个层面：

### 1. 机器人级能力

给一个机器人增加明确的行为标签，例如：

- 财报解读
- 合同问答
- 产品说明书问答
- FAQ 精简回复
- 带引用的详细回答

### 2. 检索级策略

让 skill 影响检索参数，而不是绕开检索：

- 默认 `top_k`
- 是否启用 rerank
- retrieval prompt 模板
- 回答时引用策略
- 相似度阈值建议值

### 3. 展示级模板

让 skill 影响回答的组织方式：

- 是否强制分点
- 是否必须带“结论 / 证据 / 风险”
- 是否输出表格
- 是否输出引用块

## 明确不做什么

为了避免范围失控，第一阶段不建议做这些能力：

- 不支持任意代码执行
- 不支持运行时拉取远端 skill 后立即生效
- 不支持 skill 直接修改底层模型配置
- 不支持 skill 在请求过程中访问任意外部网络
- 不支持多个 skill 之间形成不透明的依赖树

## 产品边界结论

结论很明确：

- `skills` 是 RAG 之上的“受控能力包”
- 它应该增强机器人，而不是替代机器人、知识库或模型配置
- 它的安装、审核、启停、绑定都必须是显式动作
- 远端下载属于控制面能力，不属于在线问答链路

## 和现有仓库模块的关系

建议关系如下：

- `knowledge`
  - 继续负责文档和索引
- `robots`
  - 继续负责模型、知识库绑定和问答参数
- `skills`
  - 负责“这个机器人要以什么风格、什么流程、什么约束去消费现有 RAG 能力”

换句话说：

- 知识库提供内容
- 机器人提供主体配置
- skill 提供场景化行为模板

## 下一步

如果要把这套定义推进为可实现方案，请继续看：

- [skills-architecture.md](./skills-architecture.md)
- [skills-remote-install-security.md](./skills-remote-install-security.md)
- [skills-bootstrap-plan.md](./skills-bootstrap-plan.md)
