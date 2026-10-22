<div align="center">

[简体中文](./README.md) · **English**

# Littlebear Skills

**Agent skills I wrote for myself and use every day.**

Slide-style course diagrams, lesson-style explanations in the terminal, BOSS Zhipin job-market reports, and World Cup prediction round-ups.<br/>
One folder per skill, installed with one command into Claude Code, Cursor, Codex, or any other agent that supports Agent Skills.

[![license](https://img.shields.io/badge/license-MIT-C15F3C?style=flat-square)](./LICENSE)
![skills](https://img.shields.io/badge/skills-4-C15F3C?style=flat-square)
[![Agent Skills](https://img.shields.io/badge/standard-Agent_Skills-3b3b3b?style=flat-square)](https://agentskills.io)
[![SkillHub](https://img.shields.io/badge/SkillHub-huangsitao.fun-3b3b3b?style=flat-square)](https://huangsitao.fun/skills)

[Skills](#skills) · [Install](#install) · [Skill details](#skill-details) · [Repository layout](#repository-layout) · [Feedback](#feedback-and-contributing)

<code>npx skills add litterbear520/littlebear-skills</code>

</div>

---

A skill is a folder of instructions, scripts, and resources. The agent loads it when the moment described in `SKILL.md` comes up, and uses it to do one kind of task the same way every time. Every skill here follows the open [Agent Skills](https://agentskills.io) standard, so the same `SKILL.md` works across tools.

> [!NOTE]
> The skills are written in Chinese, and two of them work with Chinese sources (BOSS Zhipin job posts and China Sports Lottery football odds). They work in any language, but replies and reports come out in Chinese by default.

All of these come from my own work: diagrams for blog posts, explanations of code I'm reading, a look at the job market, and a daily round-up during the World Cup. Each one has been used on real tasks and revised after the problems it ran into. They share one rule: **the model makes the judgment calls; scripts do the counting, rendering, and checking**. The same input gives the same output, and it costs fewer tokens.

## Skills

| Skill | What it does | How to use it | Needs |
| ---- | ---- | ---- | ---- |
| [academy-diagram-design](#academy-diagram-design) | Draws slide-style course diagrams as SVG source plus WebP, with a built-in render check | "Draw this with the academy diagram style…" | Node 22+, Chrome |
| [explain](#explain) | Explains a concept or a piece of code as a short lesson in the terminal | Type `/explain <question>` | Nothing |
| [boss-job-analyzer](#boss-job-analyzer) | Scrapes real job posts for a role on BOSS Zhipin and builds a report on tech stacks, education, salaries, and the posts themselves | "What do AI Agent roles on BOSS ask for?" | Python 3, [web-access](https://github.com/eze-is/web-access) |
| [worldcup-bet-advisor](#worldcup-bet-advisor) | Rounds up several AI models' World Cup picks and scorelines alongside live odds for every market, in one HTML report | "What do the models predict for today's World Cup matches?" | Python 3, [web-access](https://github.com/eze-is/web-access) |

## Install

### Option 1: `npx skills` (recommended, works across tools)

[`npx skills`](https://github.com/vercel-labs/skills) is an open installer for Agent Skills that supports more than 70 agents, including Claude Code, Cursor, Codex, and OpenCode. Run it without options to pick from the skills in this repository:

```bash
npx skills add litterbear520/littlebear-skills
```

To install only one, name it with `--skill`:

```bash
npx skills add litterbear520/littlebear-skills --skill explain
```

To update later: `npx skills update`.

### Option 2: Claude Code plugin

Add this repository as a plugin marketplace in Claude Code, then install the plugin. You get all four skills at once, and they update with the repository:

```text
/plugin marketplace add litterbear520/littlebear-skills
/plugin install littlebear-skills@littlebear
```

Plugin skills carry the plugin name as a prefix, such as `/littlebear-skills:explain`. Pick one option; installing both makes every skill show up twice.

### Option 3: Copy by hand

```bash
git clone https://github.com/litterbear520/littlebear-skills.git
cp -r littlebear-skills/skills/explain ~/.claude/skills/      # use the skill you want and your tool's skills directory
```

## Skill details

### academy-diagram-design

<table>
<tr>
<td><img src="./docs/assets/academy-sampling-option1.webp" alt="Sequence diagram: an MCP server asks Claude to summarize research" /></td>
<td><img src="./docs/assets/academy-sending-tool-results.webp" alt="Step bar and message table: a full tool-call round trip" /></td>
</tr>
</table>

Draws slide-style course diagrams: Lora serif type, cream and terracotta blocks, heavy black arrows, message labels sitting on the arrows, message tables, and a conclusion bar along the bottom. Both figures above were drawn with it.

- **One idea per figure**: two to six main elements, large type, plenty of space. Scaled down to a text column, box labels end up about the size of body text.
- **Styles live in one place**: the SVG holds only class names from `assets/academy.css` and coordinates. The render script injects colors, fonts, and sizes, so figures don't drift apart.
- **Rendering is the check**: `scripts/render.mjs` renders in headless Chrome, checks fonts, canvas overflow, overlapping text, font sizes, and the palette, then exports WebP and a PNG preview for the model to look at.
- **One-to-one redraws**: give it an existing figure in English and it measures colors, sizes, and coordinates, redraws it on the same grid, checks the result with a diff image, and then translates the text into Chinese.

**Needs**: Node 22 or later and Chrome (set `CHROME` if it isn't found). Chinese text uses Noto Serif SC / Noto Sans SC installed on the machine; if your project self-hosts those fonts, point `CJK_FONTS_CSS` at that `@font-face` stylesheet.

**More**: [SKILL.md](./skills/academy-diagram-design/SKILL.md) · [Component sizes](./skills/academy-diagram-design/references/components.md) · [Redraw process](./skills/academy-diagram-design/references/replicate.md)

### explain

Turns your question into a short lesson: the problem it solves first, then how it works, how it's implemented, the trade-offs, and when to use it. The whole lesson is one terminal reply, and diagrams are drawn as text with Unicode box-drawing characters.

```text
/explain why the tool executor in this project never throws
```

- **A plan for each kind of question**: "what is it", "how does it work", "why is it designed this way", "which one should I pick", and "why does this happen" each get their own outline.
- **Only code it has read**: every snippet comes from a file read during this session and is labeled with `file:line`, and every claim about when something triggers points to a line of code.
- **Explains, never edits**: it creates and changes no files. It runs only when you type `/explain`; the model never invokes it on its own.

**More**: [SKILL.md](./skills/explain/SKILL.md)

### boss-job-analyzer

> Stop reading job posts one by one. Let the model read dozens of them and tell you what the field actually asks for and what you should learn next.

Turns "what do roles like this on BOSS ask for?" into a job dataset and a single-file HTML report:

- **Scraping**: reuses the login session of your everyday Chrome through web-access's CDP proxy to collect real posts (salary, company, experience and education, skill tags, and the full requirement text).
- **Division of labor**: the model tags each post's tech stack, languages, and duties instead of relying on a fixed dictionary. Scripts compute shares, co-occurrence, and salary distributions, and check the tags for gaps and duplicate spellings.
- **Report**: headline numbers and job-hunting advice, four analysis sections, and a wall of job cards that open the original post (search, experience and education filters, sort by salary). One file that works offline.

**Needs**: Python 3 (standard library only) and [web-access](https://github.com/eze-is/web-access). BOSS has strict anti-scraping, so scraping must go through its CDP proxy; the skill asks before installing it.

**More**: [SKILL.md](./skills/boss-job-analyzer/SKILL.md) · [Site notes](./skills/boss-job-analyzer/references/zhipin-site-notes.md)

> It uses your own legitimate login and browses like a person. Follow the site's terms and keep the request rate low.

### worldcup-bet-advisor

Collects several AI models' picks for each World Cup match (Claude, DeepSeek, GPT, Gemini, GLM, Kimi, and more): their bets, most likely scorelines, and their own words. It adds live odds and vig-free probabilities for every market of the day (match result, handicap, correct score, total goals, half-time/full-time) and puts it all in one HTML report.

- **Presents, doesn't recommend**: the report shows what each model said and what the market thinks, with no picks of its own.
- **The model does one thing**: normalizing scorelines is the only step that needs judgment. Scripts handle fetching, merging, removing the vig, and rendering.
- **Daily site**: optionally publishes each report to Vercel, with a date picker and a profit dashboard. My daily reports from the 2026 World Cup are at **<https://worldcup-bet-site.vercel.app>**.

**Needs**: Python 3 (standard library only) and [web-access](https://github.com/eze-is/web-access) (to open the report, and as a fallback when an API is blocked). Publishing the site also needs Node, pnpm, and a Vercel account; see [site-deploy.md](./skills/worldcup-bet-advisor/references/site-deploy.md).

**More**: [SKILL.md](./skills/worldcup-bet-advisor/SKILL.md) · [Data sources](./skills/worldcup-bet-advisor/references/data-sources.md)

> The report is a round-up of information, not betting advice. Play responsibly.

## Repository layout

```text
littlebear-skills/
├── .claude-plugin/
│   └── marketplace.json        # Claude Code marketplace; the plugin loads every skill under skills/
├── skills/
│   ├── academy-diagram-design/ # SKILL.md + assets/ references/ scripts/ examples/
│   ├── explain/
│   ├── boss-job-analyzer/
│   └── worldcup-bet-advisor/   # also holds web/, the daily report site (Next.js)
└── docs/assets/                # images for the README
```

Each skill is a self-contained folder: the YAML at the top of `SKILL.md` holds `name` and `description`, and the body holds the steps. Scripts and references sit in the same folder and are referenced by relative path, so the skill works wherever it's installed.

## Feedback and contributing

Bug reports, ideas, and requests for new skills are welcome in [Issues](https://github.com/litterbear520/littlebear-skills/issues). Before adding or changing a skill, read [CONTRIBUTING.md](./CONTRIBUTING.md) (in Chinese).

These skills are also listed in the [SkillHub](https://huangsitao.fun/skills) on my blog, together with other skills I use.

## License

Code and docs are under the [MIT](./LICENSE) license. The Lora, Poppins, and Roboto Mono fonts bundled with `academy-diagram-design` are under the SIL Open Font License; the license texts are in [`assets/fonts/`](./skills/academy-diagram-design/assets/fonts/).
