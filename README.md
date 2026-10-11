# 诺贝尔奖生成器 Skill

只需输入要 1～3 名颁奖的人的姓名、机构、学术研究领域或者其他关键信息，AI 会在网络上自动搜集其人像、文献、讲座等相关信息，为其匹（编）配（造）合适的奖项，撰写颁奖词，并生成一张诺贝尔奖颁奖海报。

## 安装

### 方法 1：复制命令到终端安装

请先安装 Node.js（包含 npm/npx）和 Git，然后复制下面这一行命令到终端运行：

```bash
npx -y skills@latest add HanHanRin/nobel-prize-generator-skill --skill nobel-prize-portrait -g
```

按提示选择要安装到的 Agent。`-g` 表示安装到用户目录，可在多个项目中使用。

### 方法 2：把仓库链接交给 Agent 安装

复制本仓库的网页链接，交给支持访问 GitHub 和操作本机环境的 Agent，直接让它帮你安装 Skill 并配置所需环境。可以复制下面这段提示词发送给 Agent：

```text
请帮我安装这个 Skill：
https://github.com/HanHanRin/nobel-prize-generator-skill

请阅读仓库说明、SKILL.md 和相关脚本，把这个 Skill 安装到当前 Agent 的技能目录，并根据我的操作系统配置所需的 Python 环境、依赖库和字体。同时检查图片生成/编辑能力是否可用，完成后验证安装结果和运行环境。
```

## 使用

将 `SKILL.md` 作为 Skill 入口安装到支持目录型 Skill 的 Agent 环境中。核心脚本位于 `scripts/`，参考资料位于 `references/`。
