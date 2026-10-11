#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配色引擎 —— 自由选色版
======================
支持三种指定方式，优先级从高到低：

1. 预设名：--scheme ink_red / full_color / all_black / blue_bg_black ...
2. 自定义色：--word-color "#1a4a76" --bg-color white --line-color black
3. 多色词云：--word-color "彩虹" 或 --word-color "#c0392b,#2980b9,#27ae60"

核心设计：
- 单色相输入会自动派生深浅三阶（核心词最深、长尾词最浅），
  保证字号主次仍然清晰，不必手工写三组色。
- 多色输入按字号分配，大字用饱和色、小字用低饱和色，避免花。
- 背景色与线稿底色/线色独立可控，支持深色背景 + 亮色线稿。
"""

import colorsys
import numpy as np

# ---------------------------------------------------------------------------
# 1. 中文/英文色名 → HEX
# ---------------------------------------------------------------------------
COLOR_NAMES = {
    # 中性
    "白": "#ffffff", "白色": "#ffffff", "white": "#ffffff",
    "黑": "#1c1c1c", "黑色": "#1c1c1c", "black": "#1c1c1c",
    "纯黑": "#000000", "墨黑": "#1c1c1c", "ink": "#1c1c1c",
    "灰": "#7a7a7a", "灰色": "#7a7a7a", "gray": "#7a7a7a",
    "米白": "#f7f3ea", "象牙": "#fffff0", "宣纸": "#f5efe0",
    "浅棕": "#d2bd8e", "米棕": "#dac1a4", "牛皮纸": "#dac1a4",
    "卡其": "#c9b37e",
    # 诺奖致敬海报·母版配色（已认可原版海报实测取色，勿改）
    "纸底": "#ece6e5", "灰白纸": "#ece6e5", "warmpaper": "#ece6e5",
    "哑金": "#957b5e", "古铜金": "#957b5e", "mattegold": "#957b5e",
    "暗酒红": "#522d32", "deepwine": "#522d32",
    # 蓝
    "蓝": "#1a4a76", "蓝色": "#1a4a76", "blue": "#1a4a76",
    "藏蓝": "#123a5f", "navy": "#123a5f", "深蓝": "#0d2b47",
    "天蓝": "#4a90c2", "青": "#1a7a7a", "青色": "#1a7a7a",
    "湖蓝": "#2e6da4", "靛蓝": "#28527a",
    # 红
    "红": "#b3311f", "红色": "#b3311f", "red": "#b3311f",
    "朱红": "#a82c1a", "vermilion": "#a82c1a",
    "绛红": "#8c2318", "酒红": "#722f37", "胭脂": "#9b2226",
    # 绿
    "绿": "#2d6a4f", "绿色": "#2d6a4f", "green": "#2d6a4f",
    "墨绿": "#1b4332", "青绿": "#38726c", "橄榄": "#5f6f52",
    # 黄橙棕
    "黄": "#c9971c", "黄色": "#c9971c", "yellow": "#c9971c",
    "金": "#b8860b", "gold": "#b8860b", "赭石": "#8c5523",
    "橙": "#c1622b", "橙色": "#c1622b", "orange": "#c1622b",
    "棕": "#6f4e37", "咖啡": "#4b3621",
    # 紫
    "紫": "#5b3a70", "紫色": "#5b3a70", "purple": "#5b3a70",
    "藕紫": "#7d6b91", "深紫": "#3f2b56",
}

# 多色词云关键词
MULTI_COLOR_KEYWORDS = {
    "全彩", "彩色", "多彩", "彩虹", "full_color", "colorful", "rainbow",
}

# 全彩色板：饱和度、明度经过统一压制，避免刺眼
FULL_COLOR_PALETTE = [
    "#c0392b",  # 砖红
    "#1f6f8b",  # 靛青
    "#2d6a4f",  # 松绿
    "#b8860b",  # 暗金
    "#5b3a70",  # 葡萄紫
    "#c1622b",  # 陶橙
    "#28527a",  # 藏青
    "#8c5523",  # 赭石
]


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def resolve_color(s: str) -> str:
    """把色名或 HEX 归一化成 HEX"""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    low = s.lower()
    if low in COLOR_NAMES:
        return COLOR_NAMES[low]
    if s in COLOR_NAMES:
        return COLOR_NAMES[s]
    if s.startswith("#"):
        return s if len(s) == 7 else _rgb_to_hex(_hex_to_rgb(s))
    raise ValueError(
        f"无法识别的颜色：{s!r}。可用色名示例：黑/白/蓝/藏蓝/朱红/墨绿，"
        f"或直接给 HEX 如 #1a4a76")


def _shift(hex_color: str, dl: float = 0.0, ds: float = 0.0) -> str:
    """在 HLS 空间调整明度(dl)和饱和度(ds)，用于派生深浅阶"""
    r, g, b = [v / 255.0 for v in _hex_to_rgb(hex_color)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(1.0, l + dl))
    s = max(0.0, min(1.0, s + ds))
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return _rgb_to_hex((r2 * 255, g2 * 255, b2 * 255))


def derive_tiers(base_hex: str, on_dark: bool = False):
    """从单个基色派生三阶配色

    on_dark=False（浅背景）：核心词最深，长尾词浅化退到背景
    on_dark=True （深背景）：核心词最亮，长尾词暗化退到背景
    """
    if on_dark:
        major = [_shift(base_hex, +0.18, -0.05), _shift(base_hex, +0.12, -0.02)]
        mid = [_shift(base_hex, +0.02), _shift(base_hex, -0.04)]
        minor = [_shift(base_hex, -0.16, -0.10),
                 _shift(base_hex, -0.22, -0.14),
                 _shift(base_hex, -0.19, -0.12)]
    else:
        major = [_shift(base_hex, -0.10, +0.05), _shift(base_hex, -0.04, +0.02)]
        mid = [_shift(base_hex, +0.10), _shift(base_hex, +0.16)]
        minor = [_shift(base_hex, +0.30, -0.12),
                 _shift(base_hex, +0.38, -0.18),
                 _shift(base_hex, +0.34, -0.15)]
    return major, mid, minor


def _is_dark(hex_color: str) -> bool:
    r, g, b = _hex_to_rgb(hex_color)
    # 相对亮度
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


# ---------------------------------------------------------------------------
# 2. 分阶配色函数
# ---------------------------------------------------------------------------
class TieredColorFunc:
    """按字号分三阶配色：核心词 / 中层词 / 长尾词"""

    def __init__(self, tier_major, tier_mid, tier_minor,
                 max_font, accent=None, accent_words=None):
        self.major = tier_major
        self.mid = tier_mid
        self.minor = tier_minor
        self.max_font = max_font
        self.accent = accent
        self.accent_words = accent_words or set()

    def __call__(self, word, font_size, position, orientation,
                 random_state=None, **kwargs):
        if self.accent and word in self.accent_words:
            return self.accent

        ratio = font_size / self.max_font
        if ratio >= 0.55:
            pool = self.major
        elif ratio >= 0.28:
            pool = self.mid
        else:
            pool = self.minor

        if random_state is not None and hasattr(random_state, "randrange"):
            idx = random_state.randrange(len(pool))
        else:
            idx = np.random.randint(0, len(pool))
        return pool[idx]


class MultiColorFunc:
    """多色词云：按字号控制饱和度，大字饱和、小字淡化，避免整体花"""

    def __init__(self, palette, max_font, on_dark=False,
                 accent=None, accent_words=None):
        self.palette = [resolve_color(c) for c in palette]
        self.max_font = max_font
        self.on_dark = on_dark
        self.accent = accent
        self.accent_words = accent_words or set()

    def __call__(self, word, font_size, position, orientation,
                 random_state=None, **kwargs):
        if self.accent and word in self.accent_words:
            return self.accent

        if random_state is not None and hasattr(random_state, "randrange"):
            idx = random_state.randrange(len(self.palette))
        else:
            idx = np.random.randint(0, len(self.palette))
        base = self.palette[idx]

        ratio = font_size / self.max_font
        if ratio >= 0.55:
            return base
        if ratio >= 0.28:
            return _shift(base, +0.08 if not self.on_dark else -0.06, -0.08)
        # 长尾词淡化退到背景
        return _shift(base,
                      +0.24 if not self.on_dark else -0.18,
                      -0.20)


# ---------------------------------------------------------------------------
# 3. 预设方案库
# ---------------------------------------------------------------------------
# 每个预设声明：词色 / 背景 / 线稿底色 / 线稿线色 / 点缀色
#
# 【硬约束】所有预设的人像一律 line_bg=白 + line=黑。
# 人像必须是清晰的黑白线条图，不跟随画布背景色。深色背景时
# 白底黑线人像会形成一块亮区，人物更突出；若让人像底色跟随
# 深背景，线稿会糊进背景变成 X 光片，五官不可辨。
PRESETS = {
    # ---- 浅背景系 ----
    "mono_navy": dict(
        name="单色藏蓝", word="藏蓝", bg="白", line_bg="白", line="黑",
        accent=None),
    "navy_red": dict(
        name="藏蓝配朱红", word="藏蓝", bg="白", line_bg="白", line="黑",
        accent="朱红"),
    "ink_red": dict(
        name="墨黑配朱红", word="墨黑", bg="白", line_bg="白", line="黑",
        accent="朱红"),
    "all_black": dict(
        name="全黑（纯黑白）", word="墨黑", bg="白", line_bg="白", line="黑",
        accent=None),
    "full_color": dict(
        name="全彩", word="全彩", bg="白", line_bg="白", line="黑",
        accent=None),
    "ink_green": dict(
        name="墨绿书卷", word="墨绿", bg="宣纸", line_bg="白", line="黑",
        accent="赭石"),
    "sepia": dict(
        name="复古棕调", word="棕", bg="米白", line_bg="白", line="咖啡",
        accent="赭石"),
    "purple_gold": dict(
        name="紫金", word="紫", bg="白", line_bg="白", line="黑",
        accent="金"),

    # ---- 深背景系：背景深、词云亮，但人像仍是白底黑线 ----
    "blue_bg_black": dict(
        name="蓝底黑人物", word="白", bg="藏蓝", line_bg="白", line="黑",
        accent="金"),
    "dark_navy": dict(
        name="深蓝底白字", word="天蓝", bg="深蓝", line_bg="白", line="黑",
        accent="金"),
    "black_bg_white": dict(
        name="黑底白字", word="白", bg="纯黑", line_bg="白", line="黑",
        accent="朱红"),
    "dark_full_color": dict(
        name="深底全彩", word="全彩", bg="#141821", line_bg="白",
        line="黑", accent=None),
}


def build_color_func(word_color, bg_color, max_font,
                     accent=None, accent_words=None):
    """根据词色与背景色构造 wordcloud 的 color_func

    word_color 可以是：
      - 单个色名/HEX  → 自动派生深浅三阶
      - "全彩"等关键词 → 使用内置全彩色板
      - 逗号分隔的多色 → 使用自定义多色板
    """
    bg_hex = resolve_color(bg_color)
    on_dark = _is_dark(bg_hex)
    accent_hex = resolve_color(accent) if accent else None

    wc_raw = str(word_color).strip()

    # 多色：关键词或逗号分隔
    if wc_raw.lower() in MULTI_COLOR_KEYWORDS or wc_raw in MULTI_COLOR_KEYWORDS:
        return MultiColorFunc(FULL_COLOR_PALETTE, max_font, on_dark,
                              accent_hex, accent_words)
    if "," in wc_raw:
        palette = [p for p in (x.strip() for x in wc_raw.split(",")) if p]
        return MultiColorFunc(palette, max_font, on_dark,
                              accent_hex, accent_words)

    # 单色：派生三阶
    base = resolve_color(wc_raw)
    major, mid, minor = derive_tiers(base, on_dark)
    return TieredColorFunc(major, mid, minor, max_font,
                           accent_hex, accent_words)


def resolve_preset(name: str) -> dict:
    """取出预设并把其中的色名解析成 HEX"""
    if name not in PRESETS:
        raise ValueError(
            f"未知预设 {name!r}。可用预设：{', '.join(sorted(PRESETS))}")
    p = dict(PRESETS[name])
    return p


def list_presets() -> str:
    lines = []
    for k, v in PRESETS.items():
        lines.append(f"  {k:<18} {v['name']:<12} "
                     f"词={v['word']} 背景={v['bg']} 线={v['line']}"
                     + (f" 点缀={v['accent']}" if v['accent'] else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. 诺奖致敬海报·母版配色（已认可原版海报实测取色，作为默认标准固化）
# ---------------------------------------------------------------------------
# 来源：zhuwei_nobel_original_palette.png（1773x2364，3:4）实测取色。
# 视觉特征：暖灰白纸底 + 纯黑细线 + 低饱和暖金阴影 + 哑金标题姓名 +
# 暗酒红底栏 + 双语颁奖词（英文斜体浅金 / 中文近白）+ 哑金机构 +
# 左下致敬署名。默认无词云。
NOBEL_PALETTES = {
    "zhuwei_original": {
        "name": "原版配色（默认母版）",
        "bg": "#ece6e5",          # 暖灰白纸底
        "band": "#522d32",        # 暗酒红底栏
        "title": "#957b5e",       # 古铜哑金：顶部奖项名 EN/ZH + 分隔线
        "divider": "#957b5e",     # 哑金分隔细线
        "name_color": "#eac5a4",  # 哑金浅：底栏姓名
        "en_citation": "#fbdacc",  # 斜体浅金：英文颁奖词
        "zh_citation": "#faebe8",  # 近白：中文颁奖词
        "institution": "#c9a876",  # 哑金：机构名
        "credit": "#af887e",      # 哑金：左下致敬署名
        "word_color": "#1c1c1c",  # 词云墨黑（默认无词云，仅词云模式用）
        "accent": "#957b5e",      # 词云核心词哑金
    },
    "legacy_beige_blue": {
        "name": "旧版米色深蓝字（保留兼容，非默认）",
        "bg": "#f2ead8", "band": "#722f37",
        "title": "#0d2b47", "divider": "#b8860b",
        "name_color": "#f7f3ea", "en_citation": "#e8c15a",
        "zh_citation": "#f7f3ea", "institution": "#d9c08a",
        "credit": "#0d2b47",
        "word_color": "#1c1c1c", "accent": "#b8860b",
    },
}


def resolve_nobel_palette(name: str = "zhuwei_original") -> dict:
    """取出母版配色并解析为 HEX；默认即已认可的原版海报配色"""
    if name not in NOBEL_PALETTES:
        raise ValueError(
            f"未知诺奖配色 {name!r}。可用：{', '.join(sorted(NOBEL_PALETTES))}")
    return dict(NOBEL_PALETTES[name])
