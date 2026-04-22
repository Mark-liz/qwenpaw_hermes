---
name: self_evolution
description: "Self-evolution capabilities: persist knowledge with memory tool, create and update skills with skill_evolution tool. Use proactively to grow smarter across sessions."
metadata:
  builtin_skill_version: "1.0"
  qwenpaw:
    emoji: "🧬"
    requires: {}
---

# Self-Evolution — Grow Smarter Every Session

This skill enables you to **learn and improve across sessions**. You have two powerful tools for self-evolution:

## 🧠 Memory Tool (`memory`)

Save durable information to persistent memory that survives across sessions. Memory is injected into future turns automatically.

### Two Memory Stores

| Target | File | Purpose | Limit |
|--------|------|---------|-------|
| `memory` | MEMORY.md | Your personal notes — env facts, project conventions, tool quirks, lessons learned | 2200 chars |
| `user` | USER.md | What you know about the user — name, role, preferences, communication style, pet peeves | 1375 chars |

### Actions

- **add**: Add a new entry. `memory(action="add", content="...", target="memory")`
- **replace**: Update existing entry. `memory(action="replace", old_text="...", content="...", target="memory")`
- **remove**: Delete an entry. `memory(action="remove", old_text="...", target="memory")`

### When to Save (Proactive!)

- User corrects you or says "remember this" / "don't do that again"
- User shares a preference, habit, or personal detail (name, role, timezone)
- You discover something about the environment (OS, installed tools, project structure)
- You learn a convention, API quirk, or workflow specific to this user's setup
- User expresses frustration about a recurring issue

### When NOT to Save

- Task progress, session outcomes, completed-work logs
- Temporary TODO state
- Trivial/obvious info that's easily re-discovered
- Raw data dumps

**Priority**: User preferences and corrections > environment facts > procedural knowledge.

## 🛠️ Skill Evolution Tool (`skill_evolution`)

Create, edit, and manage your own skills that persist and are loaded in future sessions. Skills are your procedural memory — reusable approaches for recurring task types.

### Actions

- **create**: Create a new skill. `skill_evolution(action="create", name="my-skill", content="---\nname: my-skill\n...")`
- **patch**: Targeted find-and-replace (preferred for fixes). `skill_evolution(action="patch", name="my-skill", old_string="...", new_string="...")`
- **edit**: Full rewrite of SKILL.md (major overhauls only). `skill_evolution(action="edit", name="my-skill", content="...")`
- **delete**: Remove a skill you created. `skill_evolution(action="delete", name="my-skill")`

### When to Create a Skill

- Complex task succeeded (5+ steps) — save the approach for reuse
- You overcame errors that could recur
- User corrected your approach and the corrected version worked
- You discovered a non-trivial, repeatable workflow
- User asks you to "remember this procedure"

### Good Skill Structure

```markdown
---
name: my-skill
description: "Short description of when and how to use this skill"
metadata:
  builtin_skill_version: "1.0"
  qwenpaw:
    emoji: "🔧"
    requires: {}
---

# Skill Title

## When to Use
- Trigger condition 1
- Trigger condition 2

## Steps
1. Step one with exact command
2. Step two with expected output
3. Step three with error handling

## Pitfalls
- Common mistake and how to avoid it

## Verification
- How to confirm the task succeeded
```

### When to Patch a Skill

If you use a skill and find it outdated, incomplete, or wrong:
- **Patch it immediately** — don't wait to be asked
- Use `action="patch"` for small, targeted fixes
- Use `action="edit"` only for major overhauls
- Skills that aren't maintained become liabilities

## 🔄 The Self-Evolution Loop

Self-evolution is **capability accumulation**: you extend yourself by:

1. **Remembering knowledge** → `memory` tool (declarative knowledge)
2. **Creating skills** → `skill_evolution` tool (procedural knowledge)
3. **Updating skills when you find gaps** → `skill_evolution` patch action
4. **Recording user context** → `memory` tool with target="user"

Each session, you start with all your accumulated memories and skills. The more you save, the more capable and personalized you become.

## ⚠️ Important Rules

- All writes are security-scanned. Malicious content will be blocked.
- Memory is bounded — remove old entries before adding new ones if near the limit.
- Don't delete built-in skills — disable them in skill.json instead.
- After complex tasks (5+ tool calls), offer to save the approach as a skill.
- If a skill you loaded was missing steps or had wrong info, update it before finishing.
