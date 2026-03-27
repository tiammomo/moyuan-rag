# Demo Data UTF-8 Repair

这份文档说明如何修复本地演示环境里因为编码问题产生的 `???` 文本，以及后续如何避免再次写入乱码。

## 问题现象

如果你在这些位置看到问号占位内容：

- `README ?????`
- `??????????`
- `?????????? RAG ??????`

这通常不是前端渲染问题，而是数据在写入数据库之前就已经被错误编码成 `?` 了。

## 产生原因

常见来源包括：

- 在 Windows 终端里手工拼接 `curl.exe` 请求体
- 在 PowerShell 中直接写中文 JSON
- 请求头没有明确走 `application/json; charset=utf-8`

一旦请求体在发送前已经乱码，后端收到的内容就会原样写进数据库。

## 推荐修复方式

仓库已经提供 UTF-8 安全的修复脚本：

- Python 主脚本：[backend/scripts/repair_demo_unicode.py](../backend/scripts/repair_demo_unicode.py)

### 先看修复计划

```bash
python backend/scripts/repair_demo_unicode.py --dry-run
```

### 真正执行修复

```bash
python backend/scripts/repair_demo_unicode.py
```

脚本会做三件事：

1. 把 demo 机器人名称、描述和系统提示词改回正常中文。
2. 扫描该 demo 机器人下的会话标题。
3. 对 `???` 标题做修复：
   - 如果能从第一条用户消息恢复标题，就回填正常中文标题。
   - 如果整条会话本身也已经损坏，就直接删除。

## UTF-8 安全策略

修复脚本内部统一使用：

- `json.dumps(..., ensure_ascii=False).encode("utf-8")`
- `Content-Type: application/json; charset=utf-8`

前端默认 JSON 请求头也已经同步显式设置为：

```text
Content-Type: application/json; charset=UTF-8
```

相关代码在：

- [front/src/lib/api-client.ts](../front/src/lib/api-client.ts)

## 后续如何避免再次出现

如果还需要通过脚本创建中文演示数据，建议遵循这两个原则：

1. 优先使用浏览器前端页面创建中文内容。
2. 如果必须脚本调用 API，优先使用 Python 或仓库内现成脚本，不要在终端里手写中文 JSON。
