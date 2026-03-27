# Demo Data UTF-8 Repair

这份文档说明如何修复本地演示环境里因为编码问题产生的 `???` 文本，并给出后续创建中文演示数据时的安全做法。

## 问题现象

如果你在机器人名称、系统提示词或对话标题里看到：

- `README ?????`
- `??????????`
- `?????????? RAG ??????`

这通常不是前端渲染问题，而是数据在写入数据库之前就已经被替换成了问号。

## 产生原因

这类脏数据通常来自：

- Windows 终端里手写 `curl.exe` JSON
- PowerShell 中直接拼接中文 JSON 字符串
- 请求头没有明确走 `application/json; charset=utf-8`

一旦请求体在发送前已经被错误编码，后端收到的内容就会是 `?`，随后被原样写进 MySQL。

## 推荐修复方式

仓库已经提供了 UTF-8 安全的修复脚本：

- Python 主脚本：[backend/scripts/repair_demo_unicode.py](../backend/scripts/repair_demo_unicode.py)
- PowerShell 包装脚本：[backend/scripts/repair-demo-unicode.ps1](../backend/scripts/repair-demo-unicode.ps1)

### 先看计划结果

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\repair-demo-unicode.ps1 -DryRun
```

### 真正执行修复

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\repair-demo-unicode.ps1
```

脚本会做三件事：

1. 把 demo 机器人名称、描述和系统提示词改回正常中文。
2. 扫描该 demo 机器人下的会话标题。
3. 对 `???` 标题做处理：
   - 如果第一条用户消息可恢复，就回填成正常标题。
   - 如果整条会话本身也已经被写坏，就直接删除。

## UTF-8 安全策略

修复脚本内部不会手拼终端 JSON，而是统一使用：

- `json.dumps(..., ensure_ascii=False).encode("utf-8")`
- `Content-Type: application/json; charset=utf-8`

PowerShell 包装脚本本身也会显式设置：

- `InputEncoding = UTF-8`
- `OutputEncoding = UTF-8`

## 后续怎么避免再出现

如果后续还需要通过脚本创建中文演示数据，建议遵循这两个原则：

1. 优先用浏览器前端页面创建中文内容。
2. 如果必须脚本调用 API，优先用 Python 或仓库内现成脚本，不要在 PowerShell 里直接手写中文 JSON 给 `curl.exe`。

## 仓库里的同步改动

本次还顺手统一了前端默认 JSON 请求头：

- [front/src/lib/api-client.ts](../front/src/lib/api-client.ts)

现在前端会显式发送：

```text
Content-Type: application/json; charset=UTF-8
```
