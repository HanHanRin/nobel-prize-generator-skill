#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文期刊论文词云生成器
=====================
基于 https://github.com/YinkaiYu/paper-wordcloud 改造。

原仓库面向 arXiv 英文 PDF：按空格切词 + 英文停用词 + 4x 高分辨率蒙版渲染。
本脚本保留其核心渲染管线（mask 二值化 / 4x 放大 / LANCZOS / 800DPI /
relative_scaling / prefer_horizontal / theme words 加权），
替换掉不适用于中文的部分：

  1. 分词：jieba 精确模式 + 自定义学术词典（政治学/公共管理专名不被切碎）
  2. 停用词：中文虚词 + 学术套话 + 期刊体例词
  3. 字体：必须指定中文 TTF，否则 wordcloud 渲染成方框
  4. 语料：中文期刊论文多无公开全文 PDF，改用「题目 + 关键词 + 摘要」结构化语料
"""

import os
import json
import argparse
from collections import Counter
from typing import Dict, List

import numpy as np
import jieba
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from wordcloud import WordCloud

# ---------------------------------------------------------------------------
# 1. 自定义学术词典：保证专业术语不被 jieba 切碎
# ---------------------------------------------------------------------------
# 【默认为空，需按导师研究方向填写】
# 复合术语若不注入 jieba 会被切成无意义的碎片，例如
# "注意力机制"→"注意力"+"机制"、"知识蒸馏"→"知识"+"蒸馏"。
#
# 两种填法任选其一：
#   1. 直接写进下面的列表，例如
#        ACADEMIC_TERMS = ["注意力机制", "预训练", "多模态"]
#   2. 在自己项目里写一个词典层，import 本模块之后再调用
#        jieba.add_word(term, freq=100000)
#      （推荐：不同导师各自维护，互不干扰）
ACADEMIC_TERMS = []
for _t in ACADEMIC_TERMS:
    jieba.add_word(_t, freq=100000)

# ---------------------------------------------------------------------------
# 2. 中文停用词
# ---------------------------------------------------------------------------
STOPWORDS_ZH = set("""
的 了 和 与 及 或 是 在 有 为 对 从 到 把 被 就 而 也 都 又 但 并 则 以 之 其 此 该
这 那 这些 那些 一个 一种 一些 一定 我们 他们 它们 自身 本文 本研究 笔者
不 没 没有 不能 不是 很 更 最 越 非常 十分 较 比较 尤其 特别 主要 基本 基本上
可以 能够 需要 应该 应当 必须 可能 已经 正在 将要 仍然 依然 尚未 从而 因此
所以 由于 因为 如果 虽然 尽管 然而 但是 而且 并且 以及 等等 例如 比如 譬如
上 下 中 内 外 前 后 左 右 间 里 时 时候 过程 方面 层面 维度 角度 视角 意义
问题 研究 分析 讨论 探讨 考察 梳理 提出 认为 指出 发现 表明 显示 说明 阐释
解读 反思 检讨 归纳 构建 建构 形成 实现 推动 促进 提升 优化 完善 加强 强化
基于 通过 关于 针对 结合 围绕 立足 面对 作为 具有 存在 出现 呈现 体现 包括
文章 论文 摘要 关键词 引言 结论 参考文献 出处 作者 期刊 学报 第 期 页 年 月
一 二 三 四 五 六 七 八 九 十 第一 第二 第三 两种 三种 四个 多种 若干
情况 条件 因素 原因 结果 效果 影响 作用 关系 内容 形式 特征 特点 状况
不同 相关 有关 一样 同时 此外 另外 其中 其他 各种 整体 具体 相应 所谓
理论 实践 经验 案例 视野 背景 现实 现状 空间 路径 方式 方法 机制 逻辑
""".split())

# 单字与纯数字一律丢弃；这些高频"半词"也剔除
STOPWORDS_ZH |= {"一体", "两面", "三级", "台阶", "红线", "面孔", "调子", "定位"}

# 泛化碎片：语义过宽的单字/双字词，单独出现只会稀释画面。
# ⚠️ 这份表是**学科相关**的：某个方向的泛词往往是另一方向的核心术语
#    （"社会""技术""经验"对政治学是泛词，对人类学/STS 是核心概念；
#      "形式""存在""现实"对多数学科是泛词，对哲学是第一层范畴）。
#    需要保住其中某些词时，在自己的词典层里做
#        cn_paper_wordcloud.STOPWORDS_ZH -= {"社会", "技术"}
#    不要直接改这里，以免影响其他方向的使用。
GENERIC_FRAGMENTS = {
    "中国", "现代", "概念", "结构", "选择", "解释", "思想", "当代",
    "为例", "如何", "社会", "技术", "经验", "组织", "制度", "参与",
    "价值", "关键", "核心", "重要", "有效", "深入", "不断", "逐步",
    "有机", "统一", "传统", "西方", "学界", "学术", "学者", "议题",
    "任务", "目标", "整体", "多元", "模式", "框架", "进路", "阶段",
    "运行", "供给", "监督", "服务", "指标", "过程性",
}
STOPWORDS_ZH |= GENERIC_FRAGMENTS

# 连接词/虚指碎片（jieba 会把它们切成双字词，绕过了单字过滤）
STOPWORDS_ZH |= {
    "及其", "之间", "以来", "这一", "成为", "要求", "随着", "与非", "二者",
    "出发", "走向", "内在", "变化", "限度", "难以", "为何", "如果", "由于",
    "对话", "答对", "问答", "论述", "主张", "提炼", "界定", "区分", "梳理",
    "拓展", "超越", "面临", "呈现", "体现", "推进", "反思", "检讨", "分歧",
    "有限", "三个", "两种", "三种", "第一", "第二", "第三", "历程", "展望",
    "生产", "连接", "转换", "打造", "运转", "竞争", "差异", "经历", "关系",
    "支持", "支撑", "引入", "开放", "混合", "均衡性", "整体性", "过程",
    "科学", "历史", "世界", "文化", "知识", "能力", "资源", "战略", "方案",
    "建设", "发展", "改革", "实践", "理想", "理解", "探索", "回应", "评价",
    "格局", "体系", "体制", "运作", "整合", "基础", "基石", "桥梁", "道路",
    "主任", "任职", "教授",
}


def load_corpus(corpus_json: str, limit: int = None) -> (List[str], List[dict]):
    """读取结构化论文语料，返回 (文本列表, 论文元数据列表)

    中文期刊论文极少提供公开可下载全文 PDF，因此语料单元为：
        题目（权重 x3）+ 关键词（权重 x3）+ 摘要（权重 x1）
    题目与关键词加权是因为它们最能代表一篇论文的学术主张。
    """
    with open(corpus_json, "r", encoding="utf-8") as f:
        papers = json.load(f)

    if limit:
        papers = papers[:limit]

    texts = []
    for p in papers:
        parts = []
        parts += [p["title"]] * 3
        parts += [" ".join(p.get("keywords", []))] * 3
        parts += [p.get("abstract", "")]
        texts.append("\n".join(parts))
    return texts, papers


def get_word_frequencies(texts: List[str],
                         min_word_length: int = 2,
                         theme_words_file: str = None) -> Dict[str, int]:
    """jieba 分词 + 停用词过滤 + 主题词加权（对应原仓库同名函数）"""
    counts = Counter()

    for text in texts:
        for w in jieba.cut(text):
            w = w.strip()
            if not w:
                continue
            # 只保留中文（含少量英文专名如 res publica 由下方兜底）
            if len(w) < min_word_length:
                continue
            if w in STOPWORDS_ZH:
                continue
            if w.isdigit():
                continue
            # 过滤掉含标点/空白的碎片
            if not all("\u4e00" <= c <= "\u9fff" or c.isalpha() for c in w):
                continue
            counts[w] += 1

    freq = dict(counts)

    # 主题词加权：沿用原仓库 boost 逻辑（1.2, 1.15, 1.1 ...）
    if theme_words_file and os.path.exists(theme_words_file):
        with open(theme_words_file, "r", encoding="utf-8") as f:
            theme_words = [l.strip() for l in f if l.strip()]
        if theme_words:
            max_freq = max(freq.values()) if freq else 100
            for i, tw in enumerate(theme_words):
                boost = 1.35 - (i * 0.05)
                boosted = max_freq * max(boost, 1.05)
                freq[tw] = max(freq.get(tw, 0), boosted)
            print(f"📝 主题词加权 {len(theme_words)} 个：{'、'.join(theme_words[:6])}...")

    return freq


def create_masked_wordcloud(word_freq: Dict[str, int],
                            mask_path: str,
                            output_path: str,
                            font_path: str,
                            max_words: int = 400,
                            background_color: str = "black",
                            colormap: str = None) -> bool:
    """蒙版词云渲染（保留原仓库 4x 放大 + 800DPI 高清管线）"""
    mask_image = Image.open(mask_path)
    if mask_image.mode != "L":
        mask_image = mask_image.convert("L")

    original_size = mask_image.size
    hq_width = original_size[0] * 4
    hq_height = original_size[1] * 4

    mask_hq = mask_image.resize((hq_width, hq_height), Image.LANCZOS)
    mask_hq_array = np.array(mask_hq)
    # 白色(255)=不放词；深色(0)=放词
    processed_mask_hq = np.where(mask_hq_array < 128, 0, 255).astype(np.uint8)

    def white_color_func(word, font_size, position, orientation,
                         random_state=None, **kwargs):
        return "rgb(255, 255, 255)"

    kwargs = dict(
        width=hq_width,
        height=hq_height,
        background_color=background_color,
        max_words=max_words,
        relative_scaling=0.35,
        min_font_size=14,
        max_font_size=420,
        prefer_horizontal=0.75,
        mask=processed_mask_hq,
        collocations=False,
        random_state=42,
        font_step=1,
        margin=4,
        font_path=font_path,
    )
    if colormap:
        kwargs["colormap"] = colormap
    else:
        kwargs["color_func"] = white_color_func

    wc = WordCloud(**kwargs)
    wc.generate_from_frequencies(word_freq)

    outdir = os.path.dirname(output_path)
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    dpi = 800
    fig, ax = plt.subplots(figsize=(hq_width / dpi, hq_height / dpi), dpi=dpi)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])
    fig.patch.set_facecolor(background_color)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0,
                facecolor=background_color, edgecolor="none")
    plt.close()

    print(f"✅ 词云已保存：{output_path}  ({hq_width}x{hq_height} @ {dpi}DPI)")
    return True


def main():
    ap = argparse.ArgumentParser(description="中文期刊论文词云生成器")
    ap.add_argument("--corpus", required=True, help="论文语料 JSON")
    ap.add_argument("--mask", required=True, help="蒙版图片")
    ap.add_argument("--output", required=True, help="输出图片")
    ap.add_argument("--font", required=True, help="中文字体 TTF/OTF")
    ap.add_argument("--theme-words", default=None, help="主题词文件")
    ap.add_argument("--max-words", type=int, default=400)
    ap.add_argument("--limit", type=int, default=None, help="只用前 N 篇")
    ap.add_argument("--background", default="black")
    ap.add_argument("--colormap", default=None)
    ap.add_argument("--dump-freq", default=None, help="导出词频 TSV")
    args = ap.parse_args()

    texts, papers = load_corpus(args.corpus, args.limit)
    print(f"📚 载入论文 {len(papers)} 篇")

    freq = get_word_frequencies(texts, theme_words_file=args.theme_words)
    print(f"🔤 有效词条 {len(freq)} 个")

    top = sorted(freq.items(), key=lambda x: -x[1])[:30]
    print("🏆 Top30 高频词：")
    for w, c in top:
        print(f"   {w}\t{c:.0f}")

    if args.dump_freq:
        with open(args.dump_freq, "w", encoding="utf-8") as f:
            f.write("word\tfreq\n")
            for w, c in sorted(freq.items(), key=lambda x: -x[1]):
                f.write(f"{w}\t{c:.2f}\n")
        print(f"💾 词频已导出：{args.dump_freq}")

    create_masked_wordcloud(
        freq, args.mask, args.output,
        font_path=args.font,
        max_words=args.max_words,
        background_color=args.background,
        colormap=args.colormap,
    )


if __name__ == "__main__":
    main()
