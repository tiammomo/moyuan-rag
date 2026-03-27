# Skills 远端安装与安全模型

## 核心原则

这个仓库里的 `skills` 远端拉取能力必须默认关闭。

原因很简单：

- 远端下载会把供应链风险引入 RAG 系统
- 一旦 skill 可以在运行时不受控进入本地，就很难区分“业务配置”与“执行载荷”
- 当前仓库的主目标是稳定的知识问答，不是通用插件平台

因此推荐默认值：

- `ENABLE_REMOTE_SKILL_INSTALL=false`

## 允许远端安装时的最小控制面

只有当管理员显式开启后，系统才允许使用远端来源安装 skill。

建议配置项：

- `ENABLE_REMOTE_SKILL_INSTALL`
- `SKILL_INSTALL_ROOT`
- `SKILL_REMOTE_ALLOWED_HOSTS`
- `SKILL_REMOTE_MAX_PACKAGE_MB`
- `SKILL_REMOTE_REQUIRE_CHECKSUM`
- `SKILL_REMOTE_TIMEOUT_SEC`

## 远端安装流程

```mermaid
flowchart LR
    A["Admin requests remote install"] --> B["Validate host allowlist"]
    B --> C["Download package to quarantine"]
    C --> D["Verify checksum / size / mime"]
    D --> E["Extract to quarantine"]
    E --> F["Validate manifest and directory structure"]
    F --> G["Move to extracted registry"]
    G --> H["Write DB metadata"]
    H --> I["Mark version installed"]
```

## 必做校验

### 1. 来源校验

只允许白名单 host：

- 官方内部仓库
- 可信的对象存储域名
- 明确维护的 release 源

禁止：

- 任意 GitHub raw 链接
- 任意用户输入 URL
- 任意重定向后的未知域名

### 2. 文件大小校验

必须限制最大包大小，避免：

- 意外磁盘占满
- 恶意压缩包
- 大文件拖垮本地环境

### 3. 类型与结构校验

只接受明确的包类型，例如：

- `.zip`
- `.tar.gz`

解压后必须存在：

- `skill.yaml`
- `SKILL.md`
- 至少一个 `prompts/` 入口文件

### 4. Checksum 校验

推荐强制要求：

- `sha256`

如果没有 checksum：

- 第一阶段直接拒绝安装

### 5. 路径穿越防护

解压时必须拒绝：

- `../`
- 绝对路径
- 指向安装根目录外部的符号链接

## 明确禁止的内容

第一阶段建议直接禁止以下文件进入安装目录：

- `.exe`
- `.dll`
- `.bat`
- `.ps1`
- `.sh`
- `.py`
- `.js`
- 任意二进制可执行文件

原因不是这些文件本身一定危险，而是第一阶段的 skill 根本不应该包含可执行代码。

## 安装状态机

推荐状态：

- `pending`
- `downloading`
- `verifying`
- `extracting`
- `installed`
- `failed`
- `rolled_back`

这样后续前端可以直接展示状态，并支持管理员排查。

## 回滚策略

如果同一个 `skill` 升级失败：

- 保留上一版 `is_current=true`
- 新版本标记为 `failed`
- 不修改运行中的机器人绑定关系

如果安装过程中失败：

- 删除 quarantine 临时目录
- 不写入正式 extracted 目录
- 保留失败日志和错误消息

## 前端交互约束

前端上不应该出现“粘贴链接立刻安装并生效”的按钮。

推荐交互：

1. 管理员进入 `/skills`
2. 选择“从远端安装”
3. 输入允许来源的包地址与 checksum
4. 提交安装任务
5. 在详情页查看校验、安装、失败原因
6. 安装成功后再手动绑定机器人

注意：

- 安装 ≠ 启用
- 启用 ≠ 绑定
- 绑定 ≠ 在线问答立刻下载执行

## 推荐结论

对这个仓库来说，最稳妥的方案是：

- 第一阶段只支持本地包安装
- 第二阶段再做远端安装
- 远端安装始终走显式控制面和严格校验
- 永远不要在问答请求链路里即时拉取远端 skill

## 实现前置

如果要真正写代码，先完成：

- [skills-definition-and-boundary.md](./skills-definition-and-boundary.md)
- [skills-architecture.md](./skills-architecture.md)
- [skills-bootstrap-slice.md](./skills-bootstrap-slice.md)
