---
name: self_evolution
description: "自进化能力：使用 memory 工具持久化知识，使用 skill_evolution 工具创建和更新技能。主动使用这些能力，让每次会话都更聪明。"
metadata:
  builtin_skill_version: "1.0"
  qwenpaw:
    emoji: "🧬"
    requires: {}
---

# 自进化 —— 每次会话都在成长

此技能让你能够**跨会话学习和改进**。你有两个强大的自进化工具：

## 🧠 记忆工具 (`memory`)

将持久化信息保存到跨会话的持久记忆中。记忆会自动注入到未来的对话轮次中。

### 两个记忆存储

| 目标 | 文件 | 用途 | 上限 |
|------|------|------|------|
| `memory` | MEMORY.md | 你的个人笔记 — 环境事实、项目约定、工具特性、经验教训 | 2200 字符 |
| `user` | USER.md | 你对用户的了解 — 姓名、角色、偏好、沟通风格、注意事项 | 1375 字符 |

### 操作

- **add**：添加新条目。`memory(action="add", content="...", target="memory")`
- **replace**：更新现有条目。`memory(action="replace", old_text="...", content="...", target="memory")`
- **remove**：删除条目。`memory(action="remove", old_text="...", target="memory")`

### 何时保存（主动！）

- 用户纠正你或说"记住这个"/"别再这样了"
- 用户分享了偏好、习惯或个人细节（姓名、角色、时区）
- 你发现了关于环境的信息（操作系统、已安装工具、项目结构）
- 你学到了特定于此用户设置的约定、API 特性或工作流
- 用户对某个反复出现的问题表示不满

### 何时不保存

- 任务进度、会话结果、已完成工作日志
- 临时 TODO 状态
- 微不足道/显而易见、容易被重新发现的信息
- 原始数据转储

**优先级**：用户偏好和纠正 > 环境事实 > 程序性知识。

## 🛠️ 技能进化工具 (`skill_evolution`)

创建、编辑和管理你自己的技能，这些技能会持久化并在未来会话中加载。技能是你的程序性记忆 —— 针对重复任务类型的可复用方法。

### 操作

- **create**：创建新技能。`skill_evolution(action="create", name="my-skill", content="---\nname: my-skill\n...")`
- **patch**：定向查找替换（首选修复方式）。`skill_evolution(action="patch", name="my-skill", old_string="...", new_string="...")`
- **edit**：完整重写 SKILL.md（仅用于大幅修改）。`skill_evolution(action="edit", name="my-skill", content="...")`
- **delete**：删除你创建的技能。`skill_evolution(action="delete", name="my-skill")`

### 何时创建技能

- 复杂任务成功完成（5 步以上）— 保存方法以便复用
- 你克服了可能再次出现的错误
- 用户纠正了你的方法，纠正后的版本有效
- 你发现了一个非平凡的、可重复的工作流
- 用户要求你"记住这个流程"

### 良好的技能结构

```markdown
---
name: my-skill
description: "何时以及如何使用此技能的简短描述"
metadata:
  builtin_skill_version: "1.0"
  qwenpaw:
    emoji: "🔧"
    requires: {}
---

# 技能标题

## 何时使用
- 触发条件 1
- 触发条件 2

## 步骤
1. 第一步及具体命令
2. 第二步及预期输出
3. 第三步及错误处理

## 常见陷阱
- 常见错误及避免方法

## 验证
- 如何确认任务成功
```

### 何时修补技能

如果你使用技能时发现它过时、不完整或错误：
- **立即修补** — 不要等到被要求
- 使用 `action="patch"` 进行小的、有针对性的修复
- 仅在进行大幅修改时使用 `action="edit"`
- 不维护的技能会变成负担

## 🔄 自进化循环

自进化是**能力积累**：你通过以下方式扩展自己：

1. **记住知识** → `memory` 工具（陈述性知识）
2. **创建技能** → `skill_evolution` 工具（程序性知识）
3. **发现差距时更新技能** → `skill_evolution` 的 patch 操作
4. **记录用户上下文** → `memory` 工具 target="user"

每次会话，你都以所有积累的记忆和技能开始。保存得越多，你就越有能力、越个性化。

## ⚠️ 重要规则

- 所有写入都会进行安全扫描。恶意内容将被阻止。
- 记忆是有上限的 — 如果接近限制，请先删除旧条目再添加新条目。
- 不要删除内置技能 — 改为在 skill.json 中禁用。
- 复杂任务（5 次以上工具调用）完成后，主动提议将方法保存为技能。
- 如果你加载的技能缺少步骤或信息有误，请在完成前更新它。
