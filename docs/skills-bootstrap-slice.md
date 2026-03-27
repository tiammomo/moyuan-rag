# Skills Bootstrap Slice

## 本轮完成了什么

这份文档对应 `skills` 的第一批可运行实现，不再只是设计稿。

当前已经落地：

- 后端新增 `SKILL_INSTALL_ROOT` 和 `ENABLE_REMOTE_SKILL_INSTALL`
- 本地文件注册表已接入 `backend/data/skills/registry/installed.json`
- 新增只读 Skills API
- 新增机器人技能绑定表与绑定 API
- 新增本地 zip skill 包安装入口
- 远端安装默认拒绝
- 前端新增 `/skills` 列表页与 `/skills/[slug]` 详情页
- 仓库内置了一个 demo skill：`rag-citation-guide`

## 当前实现边界

这一版采用的是“文件注册表 + 显式绑定表”的 bootstrap 方案：

- skill 元数据和包内容来自文件系统
- 机器人绑定关系写入 MySQL
- 绑定关系已经可查可管
- 但 skill 还没有正式注入 chat runtime prompt 合并链路

换句话说：

- 现在已经能安装、列出、查看、绑定
- 下一步才是把绑定后的 skill 真正影响机器人回答

## 本地目录结构

```text
backend/data/skills/
├── registry/
│   └── installed.json
└── extracted/
    └── rag-citation-guide/
        └── 0.1.0/
            ├── skill.yaml
            ├── SKILL.md
            └── prompts/
```

## 已实现 API

### Skills

- `GET /api/v1/skills`
- `GET /api/v1/skills/{skill_slug}`
- `POST /api/v1/skills/install-local`
- `POST /api/v1/skills/install-remote`

### Robot Skill Bindings

- `GET /api/v1/robots/{robot_id}/skills`
- `POST /api/v1/robots/{robot_id}/skills/{skill_slug}`
- `PUT /api/v1/robots/{robot_id}/skills/{skill_slug}`
- `DELETE /api/v1/robots/{robot_id}/skills/{skill_slug}`

## UI 入口

- `/skills`
  - 查看已安装 skill
  - 管理员可上传本地 zip skill 包
- `/skills/[slug]`
  - 查看 README、manifest、prompt 入口文件
  - 查看当前绑定到哪些机器人

## 内置 Demo Skill

当前仓库内置的 demo skill：

- `rag-citation-guide`

这个 skill 的目标很简单：

- 结论先行
- 明确引用
- 证据不足时主动说明

它主要用于 README 演示和本地联调，不依赖远端下载。

## 验证方式

这轮实际验证过：

- `python -m py_compile` 校验新增后端文件
- `python -m pytest tests/test_skill_service.py`
- `npm run type-check`
- `docker compose up -d --build backend front`
- 真实 API smoke test：skills 列表、详情、机器人绑定
- Playwright 实测 `/skills` 与 `/skills/[slug]`

## 当前已知限制

- skill 绑定还没有进入聊天 runtime
- 远端安装仍然只做显式拒绝
- 前端暂未在机器人编辑页提供 skill 绑定 UI

## 下一步

继续看：

- [skills-runtime-integration-plan.md](./skills-runtime-integration-plan.md)
