# 诺贝尔奖生成器 Skill

只需输入要 1～3 名颁奖的人的姓名、机构、学术研究领域或者其他关键信息，AI 会在网络上自动搜集其人像、文献、讲座等相关信息，为其匹（编）配（造）合适的奖项，撰写颁奖词，并生成一张诺贝尔奖颁奖海报。

## 安装

请先安装 Node.js（包含 npm/npx）和 Git，然后在终端运行：

```bash
npx -y skills@latest add HanHanRin/nobel-prize-generator-skill --skill nobel-prize-portrait -g
```

按提示选择要安装到的 Agent。`-g` 表示安装到用户目录，可在多个项目中使用。

## 使用

将 `SKILL.md` 作为 Skill 入口安装到支持目录型 Skill 的 Agent 环境中。核心脚本位于 `scripts/`，参考资料位于 `references/`。
