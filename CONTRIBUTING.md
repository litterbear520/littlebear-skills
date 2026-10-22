# 贡献指南

欢迎改技能、加技能。这份说明写给人，也写给帮你改仓库的 agent。

## 一个技能长什么样

每个技能放在 `skills/<技能名>/`，文件夹名就是技能名，用小写字母和连字符：

```text
skills/my-skill/
├── SKILL.md        # 必需：YAML 头 + 步骤
├── scripts/        # 可选：确定性的活交给脚本
├── references/     # 可选：按需才读的长资料
└── assets/         # 可选：模板、样式、字体
```

`SKILL.md` 开头的 YAML 至少写两项：

```markdown
---
name: my-skill
description: 这个技能做什么，以及什么时候用。agent 只看这一段决定要不要加载它，触发场景要写全。
---
```

## 写技能时守住的几条

- **路径相对技能目录。** 技能会被装到各种位置（`~/.claude/skills/`、插件缓存、别的工具的目录），脚本和文档里不写死仓库路径，也不假设仓库根在哪。脚本用自己所在的位置找资源，比如 Python 的 `Path(__file__).resolve().parents[1]`。
- **判断给模型，计数给脚本。** 统计、渲染、校验写成脚本，结果可复现；模型只做需要理解的那一步。
- **依赖写清楚。** 需要的运行时、别的技能、外部账号，在 `SKILL.md` 和 README 里都写明；没装时先问用户，别默默降级。
- **个人数据不进技能目录。** 运行产物放 `runs/` 这类已被 `.gitignore` 忽略的目录。

## 加一个新技能

1. 建 `skills/<技能名>/SKILL.md`，按上面的格式写。
2. 在 `README.md` 和 `README.en.md` 里各加一行“技能一览”，再加一节“技能详解”，把徽章里的技能数加一。
3. 本地验证：

   ```bash
   npx skills add . --list          # 应列出新技能
   claude plugin validate .         # 插件清单仍然通过
   ```

`.claude-plugin/marketplace.json` 不用改：插件会加载 `skills/` 下的全部技能。

## 维护者备忘

- `skills/worldcup-bet-advisor/web/` 由 Vercel 按 Root Directory `skills/worldcup-bet-advisor/web` 自动构建。挪这个目录时，要同步改 Vercel 项目设置。
- 新技能上线后，同步到博客的 [SkillHub](https://huangsitao.fun/skills)。
