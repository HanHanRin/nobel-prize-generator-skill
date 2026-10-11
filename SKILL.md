---
name: nobel-prize-portrait
description: >
  生成诺贝尔奖致敬海报：输入 1~3 位学者姓名（含机构/学校学院/研究领域），
  生成中英双语颁奖词（"为表彰……的杰出贡献/ for ... outstanding contributions
  to ..."），结合线描人像合成官方诺奖风格竖版致敬海报。适用于学者、企业从业者、
  互联网从业者、讲师、团队人物等；可从论文、机构主页、公司介绍、公开讲座、访谈、
  演讲、博客、新闻报道等资料中提炼主题，不必限定学术论文。默认即已认可母版：
  暖灰白纸底、纯黑细线人像、哑金标题姓名、暗酒红底栏、双语颁奖词、
  默认无词云、默认输出 1773x2364。支持 1~3 人合一张（姓名按给定顺序排列）。
  触发场景：用户要求"给XX做一张诺贝尔奖海报""诺奖风海报""为XX颁奖"，
  或输入学者姓名+研究方向要求生成致敬海报时使用。支持换人像重出、
  调整配色与版式。
---

# Nobel Prize Portrait

把线描人像与中英双语颁奖词合成一张 **官方诺贝尔奖风格**的致敬海报
（参考 Niklas Elmehed 官方线描肖像：浅底、顶部奖项名、底部姓名+颁奖词+机构）。

## 默认标准（已认可母版，固化为默认）

以已认可的原版海报为默认标准（实测 1773x2364，3:4）：

- **默认无词云**：纯净纸底 + 线描人像为主体（官方海报风）。需要词云
  时显式加 `--wordcloud`。
- **默认配色 `zhuwei_original`**：
  - 背景 暖灰白纸底 `#ece6e5`
  - 顶部奖项名/分隔线 哑金 `#957b5e`
  - 底栏 暗酒红 `#522d32`
  - 底栏姓名 哑金浅 `#eac5a4`；英文颁奖词 斜体浅金 `#fbdacc`；
    中文颁奖词 近白 `#faebe8`；机构 哑金 `#c9a876`
  - 底栏居中固定双语虚构标注：`虚构奖项 · 学术致敬 / Fictional Award ·
    Academic Tribute`（可读、中文用简体字体）
- **默认输出 1773x2364**（母版实测尺寸，不只是 3:4 比例）。需要高清图时
  显式 `--hi-res`（出 4320x5760），默认不得用高分辨率替代母版尺寸。
- **默认保留彩色线稿**：暖金阴影+黑线原样嵌入；仅显式 `--reline` 走旧黑白重描。
- **文案确认门禁**：用户未逐字确认完整中英文案（含虚构标注）前，脚本不生成海报。
- **多人一张**：`--awardees` 按给定顺序排列多列姓名；`--lineart` 仍为单个
  **预合成**多人图，脚本不自动排布多人站位/不自动匹配头像↔姓名。
- **多人姓名安全间距硬门禁**：多人底栏姓名必须作为独立等宽列渲染，每列水平居中，
  列间至少保留一个西文字符宽度的可见安全空隙；像“Wang De”与“Yan Longxu”
  相邻时，两侧末端 g 等下延字符均不得裁切、压叠、贴边或相互遮挡。生成后必须
  放大检查所有列间字符，发现相碰即缩小字号或加宽列间距后重出。

> 说明：母版人像的细腻线条/暖金晕染来自 AI 生成线稿；脚本默认原样嵌入彩色线稿并
> 套用上述配色。代码复现锁定的是**配色规格、版式比例、文案层级与默认尺寸**，不
> 承诺与 AI 母版像素级一致；换人像/换三人正式稿时仍需实际出图并局部放大核对。

## 工作流程

### Step 0: 解析输入

用户输入 1~3 个人名（含机构/学校学院/研究领域，可能不完整）。逐人处理：

- **默认每人一张独立海报**（单人版式）。多人合一张时需要把多张线稿
  横向拼合后再走同一流程，拼合图宽高比保持 2:3 竖版。
- 机构/研究领域信息用于：①搜索语料关键词；②推断奖项类别（物理/化学/
  医学/经济/文学/和平/自定义）；③生成颁奖词时引用领域。

### Step 1: 收集人物资料 → 贡献主题

人物不限于学者：可能来自高校、研究机构、公司、互联网团队、公开讲座或行业活动。
先读取 [references/source-collection.md](references/source-collection.md)，按权威程度收集资料。
学术人物优先论文和官方主页；企业/非学术人物可使用公司介绍、公开演讲、访谈、博客、
新闻报道、产品案例、专利和开源项目。没有论文不是阻塞项。

目标不是完整学术综述，而是提炼2~4个可写进颁奖词的贡献主题，并保留来源URL。
不要把单句演讲、传闻或二手报道夸大为定论。

**低公开信息预案**：如果检索后发现该人物网络痕迹很少、没有可靠正脸照片，或无法确认其可写贡献，停止猜测并向用户索要：①一张清晰正面半身照片；②ta希望被写成的“杰出贡献”主题（可以是恶搞/虚构方向，例如“摸鱼管理”“周会效率优化”“奶茶供应链建设”）；③希望的奖项领域或机构风格。拿到这些输入后，再生成2套完整候选文案供用户选择。

需要词云时，再把资料整理成 `papers.json`：

**【硬约束】字段名必须严格匹配**，`load_corpus()` 只读三个字段：

```json
[{"title": "篇名", "keywords": ["概念1", "概念2"], "abstract": "摘要文本"}]
```

- `title` 与 `keywords` 各自 **×3 加权**，`abstract` **×1**
- 写 `text`/`content` 等其它字段名会被完全忽略，表现为「频次都是 3 的整数倍」
- 概念词要放进 `keywords`；需要更高权重时同时放进 `keywords` 并在
  `abstract` 里重复若干次
- 收集 30~60 篇即可；诺奖级学者可少而精（20+），突出其获奖方向代表作

### Step 2: 生成颁奖词（中英双语）

颁奖词是**致敬文案**，由你（Agent）基于 Step 1 收集到的资料生成，
**必须来自真实检索到的公开内容**，不得编造领域、产品事实或贡献。

**英文**（官方风格，`for` + 名词短语，不是完整句）：
`for + 其最核心的具体贡献`。例：
- `"for the discovery of X-ray spectroscopy"`（官方风格）
- `"for his pioneering contributions to spatial behavior and urban mobility research"`

**中文**（公告口吻）：
`为表彰其在{领域}领域的{具体贡献}，特授予{奖项名}。` 例：
- `为表彰他在空间行为与城市出行研究领域的杰出贡献`

生成质量要求：
1. 突出 1~2 个最具体的方向（来自官方资料、公开演讲或代表作），不写空泛套话
2. 中英文表达同一贡献，但各自符合语言习惯
3. 长度控制：英文 8~20 词，中文 15~30 字，太长会挤出版面
4. 职业人物可写“推动某类产品、平台、技术或组织实践”，但不写“世界首创”等未证实表述
5. 颁奖词不能只弹空选项。必须先基于资料生成 **2 套完整候选文案**，每套都要展示：奖项英文名、奖项中文名、英文颁奖词、中文颁奖词、虚构机构名、建议站位。用户应做选择题，不是填空；只有用户要求自定义时再接收自由修改。
6. `interaction.ask` 必须包含完整 `question_id`、`header`、`display_message`、`question`、`options`；每个 option 的 `description` 要把完整候选文案逐字写进去，不能只写“方案A/方案B”。

**奖项名与机构**（按领域推断，未命中用自定义）：

| 领域 | 英文奖项名 | 颁奖机构（英文全称） |
|------|-----------|---------------------|
| 物理 | THE NOBEL PRIZE IN PHYSICS | THE ROYAL SWEDISH ACADEMY OF SCIENCES |
| 化学 | THE NOBEL PRIZE IN CHEMISTRY | THE ROYAL SWEDISH ACADEMY OF SCIENCES |
| 生理/医学 | THE NOBEL PRIZE IN PHYSIOLOGY OR MEDICINE | THE NOBEL ASSEMBLY AT KAROLINSKA INSTITUTET |
| 经济 | THE SVERIGES RIKSBANK PRIZE IN ECONOMIC SCIENCES IN MEMORY OF ALFRED NOBEL | THE ROYAL SWEDISH ACADEMY OF SCIENCES |
| 文学 | THE NOBEL PRIZE IN LITERATURE | THE SWEDISH ACADEMY |
| 和平 | THE NOBEL PEACE PRIZE | THE NORWEGIAN NOBEL COMMITTEE |
| 其它 | THE NOBEL PRIZE IN {领域大写英文} | THE ROYAL SWEDISH ACADEMY OF SCIENCES |

年份取当前年份（或用户指定）。中文奖项名如「诺贝尔物理学奖 2025」。

**免责说明**：这是致敬/装饰海报，不是真实诺贝尔奖授予。默认底栏已带独立可读的
双语标注 `虚构奖项 · 学术致敬 / Fictional Award · Academic Tribute`
（`--fictional-label`），表明虚构/致敬性质；虚构奖项须克制、可读、带此标记。

### Step 3: 生成线稿人像

1. 搜索人物公开照片（机构官网 / 公司官网 / Wikipedia / 新闻图 / 授权活动图），
   选清晰正面近景照；企业从业者没有学术头像时，可用公开讲座、采访或官方活动照，
   但必须能确认正脸和身份；**分辨率低于 800px 先放大 2~4 倍**再送入，否则线稿会糊。
   找不到可靠公开照片时，直接向用户索要照片，不使用无法辨认正脸或疑似错人的网图。
   如果同一人物找到 2 张及以上可用候选照，必须把候选图发给用户选择后再生成线稿；
   不能由 Agent 默认采用其中一张进入海报。
2. **中间产物必须保留并逐步交付**：先把每人选定的原始候选照片、多人站位拼合照片
   或多人参考拼版放入当前 Canvas/工作目录，并立即 `present_files` 交付给用户核对身份；
   再基于该照片生成线稿。不要直接从“搜索照片”跳到最终海报。最终海报之外，至少保留：
   原始参考照片、最终线稿、mask、最终海报；用户需要追问或返工时有可追溯链路。
3. 用 `image_edit` 生成线描半身肖像。**母版默认是彩色线稿**：纯黑极细墨线
   勾勒 + 低饱和暖金阴影晕染（如 Niklas Elmehed 官方风），脚本默认原样嵌入保留
   色彩；只有显式 `--reline` 才走旧的灰度硬阈值黑白重描。Prompt 要点：
   - "纯白/暖白纸底，纯黑色极细墨线勾勒，线条如0.3mm针管笔，面部暗部低饱和暖金晕染"
   - "画幅从头顶到胸口以下，双肩完整对称展开不裁切"
   - **必须先看照片再逐条锁死真实识别特征**：眼镜及款式、脸型、发型、
     年龄感、笑容形态；"禁止美化、禁止年轻化、禁止改变五官比例"
   - **模型对学者照片有强烈的"自动加眼镜"倾向**，不戴眼镜必须显式写
     "禁止添加眼镜"
   - "留白面积占画面60%以上"
4. 每生成一张立即 `present_files` 交付

### Step 4: 生成人物剪影 mask（海报版式）

**从最终线稿提取**（不是原照片），海报版式人物要**上移**给底部颁奖词区让位：

```bash
python scripts/make_mask.py \
  --photo line_art.png \
  --output mask_portrait.png \
  --height-ratio 0.55 \        # 海报版式建议 0.5-0.6（比普通版小）
  --dilate 16 \
  --bottom-offset 350          # ≈ 1440×底部条比例 0.24，人物底边离底
```

- 剪影占比 25-35% 较健康；`--audit-only mask.png` 可单独复查轮廓
- **rembg 啃缺问题**（线稿淡色排线被误判背景、轮廓被啃出缺口）：脚本内置
  `_fill_rows()` 修补（填行内空洞 + 底部 25% 区间边界包络），三个调参坑详见
  paper-wordcloud-portrait SKILL.md，勿改逻辑
- 人物底边不贴齐画布底边（有 `--bottom-offset`），头部上方留大片放词区

### Step 5: 合成海报

默认即母版（无词云 + 母版配色 + 1773x2364）。**文案确认门禁**：首次不带
`--confirm-copy` 运行时，脚本只打印待确认文案并中止（退出码 2）；把完整中英文案
逐字发给用户确认后，再加 `--confirm-copy` 重跑才真正出图。编辑已有海报时，
先确认用户指定的基线图片，再只改用户点名的区域；不得自行换用旧稿或错误基线。

```bash
python scripts/compose_poster.py \
  --mask mask_portrait.png --lineart line_art.png \
  --prize-en "THE NOBEL PRIZE IN URBAN PLANNING 2026" \
  --prize-zh "诺贝尔城市规划奖 2026" \
  --awardee "Zhu Wei" \
  --citation-en "for his pioneering contributions to urban analysis" \
  --citation-zh "为表彰他在城市分析领域的杰出贡献" \
  --institution "THE ROYAL ACADEMY OF URBAN PLANNING" \
  --confirm-copy \
  --output poster.png
```
（默认即保留彩色线稿暖金阴影；仅当要走旧的黑白重描时才加 `--reline`。）

多人合一张（姓名严格按给定顺序渲染，如 `Wang De · Zhu Wei · Yan Longxu`）：

```bash
python scripts/compose_poster.py ... --awardee "Wang De" \
  --awardees "Wang De,Zhu Wei,Yan Longxu" --confirm-copy --output trio.png
```

> **多人契约（务必诚实，勿夸大）**：`--awardees` 只负责把多名按给定顺序拼成
> 一行姓名；`--lineart` 仍然只接收**一个已预合成好的多人图**（三人并排的一张
> 线稿）。脚本**不会**自动把 N 张人像排布成 N 个站位，也**不会**自动做"头像↔
> 姓名"匹配。站位顺序与姓名顺序是否一致、照片是否对应本人，必须在送入前由
> Agent/人工逐张核对。需要每人独立站位时，先在外部合成多人线稿再作为单个
> `--lineart` 输入。多人姓名必须作为独立等宽列排布，列间留出安全空隙；
> 如果采用 AI 出图修字，要逐列放大确认 `g/y/p/q/j` 等下延字符完整可读。

常用参数（缺省即母版标准）：

| 参数 | 说明 | 缺省 |
|------|------|------|
| `--confirm-copy` | **文案确认门禁**：用户逐字确认完整中英文案后才传；缺省只打印文案并中止 | 关闭 |
| `--wordcloud` | 铺研究关键词词云（opt-in）；默认关闭=纯净纸底官方风 | 关闭 |
| `--no-wordcloud` | `--wordcloud` 的反向别名（两者等价，都关闭词云） | — |
| `--palette` | 母版配色名：`zhuwei_original`（默认原版）/ `legacy_beige_blue`（旧版兼容） | zhuwei_original |
| `--awardees` | 多人有序全名列表，逗号分隔，严格按给定顺序渲染；缺省退化为单人 `--awardee` | 空 |
| `--awardee-en` | 获奖者英文姓名（可选）：渲染为中文姓名下方的西文小字行 | 空 |
| `--institution-en` | 机构英文名（可选）：渲染为中文机构行下方的西文小字行 | 空 |
| `--width` / `--height` | 画布尺寸 | **1773 / 2364**（母版实测） |
| `--hi-res` | 显式输出高清 4320x5760（默认关闭，不替代母版尺寸） | 关闭 |
| `--reline` | 显式走旧的黑白重描（灰度+硬阈值黑线）；默认关闭=保留彩色线稿暖金阴影 | 关闭 |
| `--bg-color` | 画布背景 | 母版纸底 `#ece6e5` |
| `--band-color` | 底栏色块 | 母版暗酒红 `#522d32` |
| `--fictional-label` | 独立固定的虚构奖项/致敬标注（底栏居中可读，中文用简体字体） | `虚构奖项 · 学术致敬 / Fictional Award · Academic Tribute` |
| `--illustration-credit` | 可选额外小署名（默认空；虚构标注见上一行） | 空 |
| `--top-band-ratio` | 顶部奖项条高度比例 | 0.16 |
| `--bottom-band-ratio` | 底栏颁奖词区高度比例 | 0.24 |
| `--word-color`/`--accent-color` | 词云墨黑 / 核心词哑金（仅词云模式） | 墨黑 / 哑金 |
| `--max-words`/`--min-font`/`--margin` | 词云排版（仅词云模式） | 110/20/20 |

- **默认无词云**：纯净纸底 + 线稿人像为主体（官方海报风）；`--corpus/--theme-words`
  仅在 `--wordcloud` 时需要。
- **底栏自动换行**：英文颁奖词按词、中文颁奖词按字自动换行居中，不再把整段压成
  一行缩到极小；长文案（约百字中文/数十词英文）也不溢出左右页界。姓名含中文时
  自动用中文字体渲染（不落到西文字体）。
- `--bottom-band-ratio` 改大时，`make_mask.py` 的 `--bottom-offset` 同步增大。
- 人像落在顶部/底部文字条内的部分自动裁掉，不盖文字；文字自适应字号。

### Step 6: 校验

```bash
python scripts/verify_output.py \
  --image poster.png --mask mask_portrait.png --bg-color 米白
```

- 三项检查：背景色渗入人像 / 人像线条清晰度（亮底>45%、墨线>2%）/
  词云留白充足度（>42%）；字形必须为简体中文（SC）
- 再按 4×6 网格裁切放大，逐块检查：颁奖词完整无截断、姓名居中、
  奖项名无折行、无碎词混入；多人海报还必须逐列放大检查相邻姓名西文行，
  确认列间无字符裁切、压叠或下延字母被遮挡。
- 发现短词反复折行且非核心概念时，加入 `EXTRA_BAN`（见词表清洗）

### Step 7: 交付

- 每张海报生成后**立即单独** `present_files` 交付，不批量合并
- 交付说明中附：颁奖词全文（中英）、资料来源、配色与版式参数
- **中间过程也要交付/写入 Canvas**：选定的原始照片或多人拼版、线稿、mask、最终海报
  都要保留；最终回复应至少说明“原始参考照片 → 线稿 → 最终海报”这条链路，不要只交付最终图。
- 如果用户上传了配色/画风参考图，只作为当次参考，不复制其中人物、文字、年份、署名；
  若该参考图会成为后续所有使用者的固定默认视觉标准，才把它保存到 `assets/` 并随 ZIP 打包。
  临时参考、用户一次性上传的海报样例或某个人的专属母版，不需要打包进通用 Skill。

## 词表清洗（换人必须重做）

继承 paper-wordcloud-portrait 的三件事：

1. **`KEEP_WORDS` 白名单**（`scripts/clean_words.py`）：把真正代表其学术
   主张的术语填入，让低频专业词不因频次低而落选
2. **复合术语注入 jieba**（`cn_paper_wordcloud.ACADEMIC_TERMS` 或调用前
   `jieba.add_word(term, freq=100000)`）：避免"注意力机制"被切成
   "注意力"+"机制"
3. **`GENERIC_FRAGMENTS` 解禁**：它把"社会""技术""经验"等当泛词剔除——
   对社科/人文是核心词，需要时 `STOPWORDS_ZH -= 待解禁词集合`

**推荐做法**：不要改 skill 里的文件，在项目目录写词典层（如 `mydict.py`），
`import cn_paper_wordcloud` 后注入与解禁，换人互不干扰。标题切碎产生的
句子残词（"联结""兴起"等）补进黑名单。

`assets/theme_words.txt`：主题词加权文件（每行一个词，**不能含 `#` 注释行**，
会被当词加权），换人必须重写，选出 5~10 个核心研究方向词。

## 硬约束（继承 paper-wordcloud-portrait，勿违反）

1. **默认彩色线稿原样嵌入**：母版人像为暖金阴影+纯黑细线的彩色线稿，脚本默认
   保留其原色彩（`natural=not --reline`），不做灰度硬阈值重描。旧的"白底黑线"
   规则只在显式 `--reline`（词云/旧预设）时适用：那一路人像底色恒白、线色恒黑，
   底色跟随深背景会糊成 X 光片，代码有防护自动回退。
2. **简体中文必须抽 SC 子字体**：`.ttc` 默认加载 index=0（日文版），
   中日分歧字（与/骨/决/净）会渲染成日文写法。`find_font()` 已内置
   `_extract_sc_font()`，不要改回直接返回 ttc 路径
3. 人像剪影 mask 白=不放词、黑=放词；`make_mask.py` 三个调参坑
   （只填行内空洞修不掉 / 参考窗口比缺口矮修不掉 / 包络扩到整个躯干
   人像变方块）勿重蹈
4. **指定基线硬门禁**：用户修改已有海报时，必须以用户明确给出的链接或画布选中项为
   唯一基线；未确认前不得使用旧稿、误改稿或任意历史版本。多人海报修文字时，
   除文案和姓名间距外不得重画人物。
5. **非学术资料边界**：讲座、访谈、博客和新闻可作为致敬主题来源，但不把单一观点
   夸大为确定成果；没有公开肖像时先向用户索图，不用无法确认身份的网图替代。

## 依赖

- Python：`wordcloud` `Pillow` `numpy` `scipy` `jieba` `rembg` `fonttools`
- 字体：`Hiragino Sans GB`（词云 SC，macOS）/ `NotoSansCJK-*.ttc`（Linux，
  自动抽 SC）；英文衬线 `Times New Roman`/`Georgia`（macOS 自动探测）
- rembg 首次运行会下载 u2netp 模型，需联网

## 资源

- `references/source-collection.md`：学术与企业/非学术人物资料采集、肖像选择、颁奖词提炼清单
- `scripts/compose_poster.py`：海报合成主脚本（词云+人像+奖项条+颁奖词区）
- `scripts/make_mask.py`：剪影 mask（海报版式支持 `--bottom-offset`/`--v-align`）
- `scripts/verify_output.py`：交付前自动校验
- `scripts/palettes.py`：配色引擎（色名表、自动分阶、预设）
- `scripts/clean_words.py`：词表清洗（换人重建 KEEP_WORDS/STOPWORDS）
- `scripts/paper-wordcloud/`：中文分词与词频模块（YinkaiYu/paper-wordcloud）
- `assets/theme_words.txt`：主题词加权文件（换人必须重写）
