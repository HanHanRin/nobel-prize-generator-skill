#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诺贝尔奖致敬海报合成器
======================
在 paper-wordcloud-portrait 的 compose_gift.py 基础上扩展：

  - 词云（研究关键词）+ 线稿人像（白底黑线，硬约束继承）
  - 顶部奖项条：英文大奖名 + 中文奖项名（官方风格）
  - 底部颁奖词区：获奖者姓名（多人按给定顺序）+ 英文颁奖词（for ...）+
    中文颁奖词 + 颁奖机构名，落在暗酒红色块上
  - 默认母版配色 zhuwei_original：暖灰白纸底 #ece6e5 + 哑金标题 #957b5e +
    暗酒红底栏 #522d32（已认可原版海报实测取色）
  - 默认无词云；需要词云时显式 --wordcloud
  - 默认输出 1773x2364（母版实测尺寸）；--hi-res 才出 4320x5760

版式：
  - 顶部条 16% 高度：奖项名
  - 底部条 24% 高度：颁奖词区（暗酒红色块）
  - 中部 60%：线稿人像（默认无词云）

用法示例：
  python scripts/compose_poster.py \
    --corpus papers.json --theme-words theme_words.txt \
    --mask mask_portrait.png --lineart line_art.png \
    --prize-en "THE NOBEL PRIZE IN PHYSICS 2025" \
    --prize-zh "诺贝尔物理学奖 2025" \
    --awardee "Albert Einstein" \
    --citation-en "for his pioneering contributions to theoretical physics" \
    --citation-zh "为表彰他在理论物理学领域的开创性贡献" \
    --institution "THE ROYAL SWEDISH ACADEMY OF SCIENCES" \
    --output poster.png
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "paper-wordcloud"))

from palettes import (build_color_func, resolve_color, _hex_to_rgb,  # noqa: E402
                      _is_dark, resolve_nobel_palette)

# ---------------- 字体探测 ----------------
_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]

# 简体中文子字体在 ttc 里的 name 关键字，按优先级排列
_SC_KEYWORDS = ("CJK SC", "CJK HK", "CJK TC")

# 英文衬线字体（官方海报用衬线大写）
_LATIN_SERIF_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
]

# 中文衬线（宋体）——颁奖词更典雅；找不到回退黑体
_CJK_SERIF_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
]


def _extract_sc_font(ttc_path: str) -> str:
    """从 .ttc 集合中抽出简体中文(SC)子字体，存为独立 .otf

    【这一步必须做，否则会渲染出日文字形】PIL 与 wordcloud 加载 .ttc
    时默认取 index=0（日文版），简体中文会被画成日文写法。
    """
    from fontTools import ttLib

    cache_dir = os.path.join(SCRIPT_DIR, ".font_cache")
    os.makedirs(cache_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(ttc_path))[0]
    out = os.path.join(cache_dir, f"{base}-SC.otf")
    if os.path.exists(out):
        return out

    coll = ttLib.TTCollection(ttc_path)
    picked = None
    for kw in _SC_KEYWORDS:
        for f in coll.fonts:
            if kw in (f["name"].getDebugName(1) or ""):
                picked = f
                break
        if picked:
            break
    if picked is None:
        return ttc_path          # 找不到 SC 就退回原 ttc

    picked.save(out)
    return out


def find_font():
    """返回可用的简体中文字体路径（词云用，必须 SC）"""
    for p in _FONT_CANDIDATES:
        if not os.path.exists(p):
            continue
        if p.lower().endswith(".ttc"):
            try:
                return _extract_sc_font(p)
            except Exception as e:
                print(f"⚠️  抽取 SC 子字体失败（{e}），回退整个 ttc")
                return p
        return p
    return None


def find_serif_latin():
    """返回英文衬线字体路径（奖项名/颁奖词/机构名）"""
    for p in _LATIN_SERIF_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def find_serif_cjk():
    """返回中文宋体路径；不可用时回退黑体"""
    for p in _CJK_SERIF_CANDIDATES:
        if os.path.exists(p):
            return p
    return find_font()


SCALE = 4   # 高清放大倍数


def build_masked_wordcloud(corpus_path, theme_words_path, mask_path,
                           word_color, bg_color,
                           accent=None, accent_words=None,
                           max_words=110, min_font=20, margin=20,
                           font_step=3, prefer_horizontal=0.88,
                           extra_stop=None, custom_words=None):
    """用人物剪影 mask 生成词云——词只在人物之外的区域生长

    mask 由调用方组合好（人像剪影 + 顶部条 + 底部条均为白色不放词区）。

    extra_stop: 额外停用词集合（碎词/残词黑名单），clean 后剔除
    custom_words: 需注入 jieba 词典的复合术语集合，避免被切碎
    """
    from cn_paper_wordcloud import load_corpus, get_word_frequencies
    from clean_words import clean_frequencies

    import jieba
    for w in (custom_words or set()):
        jieba.add_word(w, freq=100000)

    texts, papers = load_corpus(corpus_path)
    freq = get_word_frequencies(texts, theme_words_file=theme_words_path)
    freq = clean_frequencies(freq, verbose=True)
    if extra_stop:
        for w in list(freq):
            if w in extra_stop:
                del freq[w]

    from wordcloud import WordCloud
    max_font = 100 * SCALE
    font = find_font()
    bg_hex = resolve_color(bg_color)

    mask_img = Image.open(mask_path).convert("L")
    w, h = mask_img.size
    hq_w, hq_h = w * SCALE, h * SCALE
    mask_hq = mask_img.resize((hq_w, hq_h), Image.LANCZOS)
    mask_arr = np.where(np.array(mask_hq) < 128, 0, 255).astype(np.uint8)

    color_func = build_color_func(word_color, bg_color, max_font,
                                  accent, accent_words)

    wc = WordCloud(
        width=hq_w, height=hq_h,
        background_color=bg_hex,
        max_words=max_words,
        relative_scaling=0.42,
        min_font_size=min_font * SCALE,
        max_font_size=max_font,
        prefer_horizontal=prefer_horizontal,
        mask=mask_arr,
        color_func=color_func,
        collocations=False,
        random_state=42,
        font_step=font_step,
        margin=margin * SCALE,
        font_path=font,
    )
    wc.generate_from_frequencies(freq)
    return wc.to_image().convert("RGB")


def overlay_lineart(bg, lineart_path, mask_path,
                    line_bg_color="白", line_color="黑",
                    top_band_ratio=0.0, bottom_band_ratio=0.0,
                    natural=False):
    """把线稿嵌进词云留出的人物空位（继承 compose_gift 的硬约束）

    top_band_ratio / bottom_band_ratio：人像落在顶部奖项条/底部颁奖词区
    内的部分会被裁掉，避免人像覆盖奖项名或颁奖词文字（海报版式必需）。

    natural=True：直接嵌入**彩色线稿**（保留线稿自身的浅棕背景与黄色
    阴影暗部，不做灰度重上色），用于官方海报风格线稿（浅棕底+黑线+
    金色晕染，如 Niklas Elmehed 风格）。此时 line_bg_color/line_color
    无效，海报背景色应与线稿背景色一致以保证无痕融合。
    """
    W, H = bg.size
    mask_img = Image.open(mask_path).convert("L").resize((W, H), Image.LANCZOS)
    m = np.array(mask_img) > 128

    # 裁掉落在文字条内的人像部分
    if top_band_ratio > 0 or bottom_band_ratio > 0:
        top_h = int(H * top_band_ratio)
        bottom_h = int(H * bottom_band_ratio)
        m[:top_h, :] = False
        m[H - bottom_h:, :] = False

    ys, xs = np.where(m)
    top, bottom = ys.min(), ys.max()
    left, right = xs.min(), xs.max()
    box_w, box_h = right - left + 1, bottom - top + 1

    art = Image.open(lineart_path).convert("L")
    a = np.array(art)
    iys, ixs = np.where(a < 240)
    art = art.crop((ixs.min(), iys.min(), ixs.max() + 1, iys.max() + 1))
    art = art.resize((box_w, box_h), Image.LANCZOS)

    sil_crop = Image.fromarray(
        (m[top:bottom + 1, left:right + 1] * 255).astype(np.uint8), "L")

    if natural:
        # 彩色线稿整图嵌入：加载已抠好的 RGBA 线稿（rembg 去背），
        # 按中部区域高度缩放后水平居中贴上——人物以外的线稿背景透明，
        # 露出海报 bg，完全无痕。
        art_n = Image.open(lineart_path).convert("RGBA")
        mid_top = int(H * top_band_ratio)
        mid_bottom = int(H * (1 - bottom_band_ratio))
        mid_h = mid_bottom - mid_top
        scale = mid_h / art_n.height
        new_w = int(art_n.width * scale)
        art_n = art_n.resize((new_w, mid_h), Image.LANCZOS)
        x = (W - new_w) // 2
        result = bg.copy()
        result.paste(art_n, (x, mid_top), art_n)
        return result

    bg_rgb = np.array(_hex_to_rgb(resolve_color(line_bg_color)),
                      dtype=np.float32)
    ln_rgb = np.array(_hex_to_rgb(resolve_color(line_color)),
                      dtype=np.float32)

    def _lum(rgb):
        return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

    # 对比度不足会让人像糊掉，强制回退到白底黑线
    if abs(_lum(bg_rgb) - _lum(ln_rgb)) < 120:
        print("   ⚠️  人像底色与线色对比不足，已回退为白底黑线以保证清晰度")
        bg_rgb = np.array([255.0, 255.0, 255.0], dtype=np.float32)
        ln_rgb = np.array([20.0, 20.0, 20.0], dtype=np.float32)

    # 底比线亮才是正常的"白底黑线"；反之说明传反了，交换回来
    if _lum(bg_rgb) < _lum(ln_rgb):
        bg_rgb, ln_rgb = ln_rgb, bg_rgb

    # 压实墨线、提净底色，保证五官线条清晰可辨
    arr = np.array(art).astype(np.float32)
    arr = np.clip((arr - 145) * 2.6 + 200, 0, 255)
    ink = 1.0 - (arr / 255.0)

    comp = (bg_rgb[None, None, :] * (1.0 - ink[:, :, None])
            + ln_rgb[None, None, :] * ink[:, :, None])
    art_rgb = Image.fromarray(comp.astype(np.uint8), "RGB")

    sil_crop = Image.fromarray(
        (m[top:bottom + 1, left:right + 1] * 255).astype(np.uint8), "L")

    result = bg.copy()
    result.paste(art_rgb, (int(left), int(top)), sil_crop)
    return result


def combine_bands_mask(mask_path, top_band_ratio, bottom_band_ratio,
                       out_path=None):
    """把人像 mask 与顶部条/底部条组合成词云 mask

    返回组合后的 mask（白色=不放词：人像剪影 + 顶部条 + 底部条）。
    顶部条/底部条必须留给奖项名与颁奖词文字，不能让词云侵入。
    """
    mask = Image.open(mask_path).convert("L")
    arr = np.array(mask)
    h = arr.shape[0]
    top_h = int(h * top_band_ratio)
    bottom_h = int(h * bottom_band_ratio)
    arr[:top_h, :] = 255          # 顶部条不放词
    arr[h - bottom_h:, :] = 255   # 底部条不放词
    out = Image.fromarray(arr, "L")
    if out_path:
        out.save(out_path)
        print(f"✅ 组合 mask 已保存：{out_path}  "
              f"顶部条 {top_h}px / 底部条 {bottom_h}px")
    return out


def _load_font(font_path, size, index=0):
    try:
        return ImageFont.truetype(font_path, size, index=index)
    except Exception:
        return ImageFont.truetype(font_path, size)


def _fit_font(draw, text, font_path, max_w, max_h,
              start, min_size=20, index=0):
    """二分缩小字号，使文本宽度与行高都不超限"""
    size = start
    while size >= min_size:
        f = _load_font(font_path, size, index)
        w = draw.textlength(text, font=f)
        if w <= max_w and size <= max_h:
            return f, w
        size -= 2
    f = _load_font(font_path, min_size, index)
    return f, draw.textlength(text, font=f)


def _has_cjk(s):
    """文本是否含中日韩字符（含全角标点）"""
    return any(('\u4e00' <= ch <= '\u9fff')
               or ('\u3000' <= ch <= '\u303f')
               or ('\uff00' <= ch <= '\uffef') for ch in s)


def _wrap_text(draw, text, font, max_w, lang):
    """按单位贪婪换行：英文按词、中文按字；每行不超过 max_w"""
    if lang == "zh":
        units = list(text)
    else:
        words = text.split(" ")
        units = [w + " " for w in words[:-1]] + ([words[-1]] if words else [])
    lines, cur = [], ""
    for u in units:
        trial = cur + u
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur.rstrip())
            cur = u
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def _fit_draw_centered_block(draw, text, font_path, lang, max_w, cx, y,
                             color, start, min_size, line_ratio=1.4):
    """选最大可读字号并按行居中绘制（英文按词换行/中文按字换行）。
    返回 (新 y, 所用字体)。保证每行不超 max_w，不依赖单行缩到极小。"""
    size, chosen = start, None
    while size >= min_size:
        f = _load_font(font_path, size)
        lines = _wrap_text(draw, text, f, max_w, lang)
        chosen = (f, lines)
        break
    f, lines = chosen
    lh = int(f.size * line_ratio)
    for ln in lines:
        w = draw.textlength(ln, font=f)
        draw.text((cx - w / 2, y), ln, font=f, fill=color)
        y += lh
    return y, f


def _hex_rgb(h):
    """色名/HEX → RGB 元组（先解析色名）"""
    return tuple(int(v) for v in _hex_to_rgb(resolve_color(h)))


def draw_top_band(draw, W, top_h, prize_en, prize_zh,
                  text_color, accent_color, latin_font, cjk_font, S=1.0):
    """顶部奖项条：英文大奖名 + 中文奖项名 + 金色细线（S=相对5760稿的缩放）"""
    max_w = int(W * 0.92)
    # 英文大奖名（大字号，参考官方海报）
    f1, _ = _fit_font(draw, prize_en, latin_font,
                      max_w, int(260 * S), start=int(150 * S),
                      min_size=max(12, int(44 * S)))
    x = (W - draw.textlength(prize_en, font=f1)) / 2
    y = int(top_h * 0.16)
    draw.text((x, y), prize_en, font=f1, fill=_hex_rgb(text_color))

    # 中文奖项名
    f2, _ = _fit_font(draw, prize_zh, cjk_font,
                      max_w, int(170 * S), start=int(84 * S),
                      min_size=max(10, int(32 * S)))
    x = (W - draw.textlength(prize_zh, font=f2)) / 2
    y = int(top_h * 0.52)
    draw.text((x, y), prize_zh, font=f2, fill=_hex_rgb(text_color))

    # 金色细线（奖项名下方）
    line_y = int(top_h * 0.90)
    lw = int(W * 0.30)
    t = max(2, int(3 * S))
    draw.rectangle(((W - lw) // 2, line_y, (W + lw) // 2, line_y + t),
                   fill=_hex_rgb(accent_color))


def draw_bottom_band(draw, W, H, bottom_h, band_color,
                     awardee, citation_en, citation_zh, institution,
                     name_color, en_color, zh_color, inst_color,
                     latin_font, cjk_font, S=1.0,
                     fictional_label="", label_color="#faebe8",
                     awardee_en="", institution_en=""):
    """底部颁奖词区：色块 + 姓名 + 英文颁奖词 + 中文颁奖词 + 机构 + 虚构标注"""
    bottom_y = H - bottom_h
    # 深色色块
    draw.rectangle((0, bottom_y, W, H), fill=_hex_rgb(band_color))
    # 色块顶部金色分隔线
    draw.rectangle((0, bottom_y, W, bottom_y + max(2, int(4 * S))),
                   fill=_hex_rgb(en_color))

    max_w = int(W * 0.88)
    cx = W / 2

    # 姓名（最大最醒目；含中文时用中文字体，避免中文姓名落到西文字体上）
    name_font = cjk_font if _has_cjk(awardee) else latin_font
    name_lang = "zh" if name_font == cjk_font else "en"
    y = bottom_y + int(bottom_h * 0.07)
    y, f_name = _fit_draw_centered_block(
        draw, awardee, name_font, name_lang, max_w, cx, y,
        _hex_rgb(name_color), start=int(120 * S), min_size=max(18, int(52 * S)),
        line_ratio=1.35)
    y += int(f_name.size * 0.35)

    # 英文姓名（可选；西文小字，居中，紧跟中文姓名下方）
    if awardee_en:
        y, f_nen = _fit_draw_centered_block(
            draw, awardee_en, latin_font, "en", max_w, cx, y,
            _hex_rgb(name_color), start=int(52 * S),
            min_size=max(12, int(24 * S)), line_ratio=1.3)
        y += int(f_nen.size * 0.45)

    # 英文颁奖词（for ...，官方引号包裹，金色；按词换行）
    en_text = f'"{citation_en}"' if not citation_en.startswith('"') \
        else citation_en
    y, f_en = _fit_draw_centered_block(
        draw, en_text, latin_font, "en", max_w, cx, y,
        _hex_rgb(en_color), start=int(44 * S), min_size=max(12, int(26 * S)),
        line_ratio=1.45)
    y += int(f_en.size * 0.30)

    # 中文颁奖词（按字换行）
    y, f_zh = _fit_draw_centered_block(
        draw, citation_zh, cjk_font, "zh", max_w, cx, y,
        _hex_rgb(zh_color), start=int(44 * S), min_size=max(12, int(26 * S)),
        line_ratio=1.45)
    y += int(f_zh.size * 0.35)

    # 机构名（金色；含中文用中文字体；可中英双行，均自动换行）
    inst_font = cjk_font if _has_cjk(institution) else latin_font
    inst_lang = "zh" if inst_font == cjk_font else "en"
    y, f_inst = _fit_draw_centered_block(
        draw, institution, inst_font, inst_lang, max_w, cx, y,
        _hex_rgb(inst_color), start=int(40 * S),
        min_size=max(10, int(20 * S)), line_ratio=1.35)
    if institution_en:
        y += int(f_inst.size * 0.15)
        y, f_ien = _fit_draw_centered_block(
            draw, institution_en, latin_font, "en", max_w, cx, y,
            _hex_rgb(inst_color), start=int(32 * S),
            min_size=max(9, int(16 * S)), line_ratio=1.3)
        y += int(f_ien.size * 1.1)

    # 独立固定的虚构奖项/致敬标注（可读、居中；中文用简体字体）
    if fictional_label:
        parts = [p.strip() for p in fictional_label.split("|")]
        zh_part = parts[0] if parts else ""
        en_part = parts[1] if len(parts) > 1 else ""
        fz, _ = _fit_font(draw, zh_part, cjk_font, max_w,
                          int(90 * S), start=int(46 * S),
                          min_size=max(14, int(20 * S)))
        fe, _ = _fit_font(draw, en_part, latin_font, max_w,
                          int(90 * S), start=int(46 * S),
                          min_size=max(12, int(18 * S)))
        w_zh = draw.textlength(zh_part, font=fz) if zh_part else 0
        w_en = draw.textlength(en_part, font=fe) if en_part else 0
        gap = int(18 * S)
        total = w_zh + (gap if (w_zh and w_en) else 0) + w_en
        lx = cx - total / 2
        # 以真实字形底为锚：保证字形底 = H - safe（≥24px，1773x2364 下），
        # 而非凭 y 估值。用中文行 bbox 作基准（中文下降部最大）。
        safe = max(24, int(round(24 * H / 2364)))
        bz = draw.textbbox((0, 0), zh_part, font=fz) if zh_part else (0, 0, 0, int(46 * S))
        ly = (H - safe) - bz[3]
        if zh_part:
            draw.text((lx, ly), zh_part, font=fz,
                      fill=_hex_rgb(label_color))
            lx += w_zh + gap
        if en_part:
            draw.text((lx, ly), en_part, font=fe,
                      fill=_hex_rgb(label_color))


def main():
    parser = argparse.ArgumentParser(
        description="合成诺贝尔奖致敬海报（词云+线稿人像+颁奖词）",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # ---- 语料与素材 ----
    parser.add_argument("--corpus", help="papers.json 语料文件路径（词云模式必需）")
    parser.add_argument("--theme-words",
                        help="主题词加权文件路径（词云模式必需）")
    parser.add_argument("--mask", required=True,
                        help="人物剪影 mask（黑底白剪影，1080x1440）")
    parser.add_argument("--lineart", required=True,
                        help="线稿人像图片路径")
    parser.add_argument("--output", default="poster.png",
                        help="输出文件路径")
    # 默认即「无词云」纯净背景（已认可母版官方海报风格）；需要词云时显式 --wordcloud。
    # --no-wordcloud 保留为向后兼容别名（两者等价，都关闭词云）。
    parser.add_argument("--wordcloud", action="store_true",
                        help="铺研究关键词词云（默认关闭；官方海报母版为无词云）")
    parser.add_argument("--no-wordcloud", action="store_true",
                        help="（别名）纯净背景模式：不铺词云，仅线稿人像+奖项/颁奖词")
    parser.add_argument("--palette", default="zhuwei_original",
                        help="母版配色名（默认 zhuwei_original=已认可原版海报；"
                             "legacy_beige_blue=旧版米色深蓝字）")
    parser.add_argument("--reline", action="store_true",
                        help="显式走旧的黑白重描路径（灰度+硬阈值黑线）。"
                             "默认关闭：默认即保留彩色线稿原画风（暖金阴影+黑线），"
                             "海报背景色与线稿底色一致以无痕融合")

    # ---- 海报文案 ----
    parser.add_argument("--prize-en", required=True,
                        help="英文奖项全称，如 THE NOBEL PRIZE IN PHYSICS 2025")
    parser.add_argument("--prize-zh", required=True,
                        help="中文奖项名，如 诺贝尔物理学奖 2025")
    parser.add_argument("--awardee", required=True,
                        help="获奖者姓名（单人；多人时作为首名主名）")
    parser.add_argument("--awardees", default=None,
                        help="多人合一张时的有序全名列表，逗号分隔，"
                             "严格按给定顺序从左到右渲染（如 'Wang De,Zhu Wei,"
                             "Yan Longxu'）。缺省时退化为单人 --awardee。")
    parser.add_argument("--citation-en", required=True,
                        help="英文颁奖词（for ...），渲染时会加引号")
    parser.add_argument("--citation-zh", required=True,
                        help="中文颁奖词（为表彰……的杰出贡献）")
    parser.add_argument("--institution", required=True,
                        help="颁奖机构全称（中文；中英混排时中文行用中文字体）")
    parser.add_argument("--institution-en", default="",
                        help="机构英文名（可选；渲染为机构中文行下方的西文小字行）")
    parser.add_argument("--awardee-en", default="",
                        help="获奖者英文姓名（可选；渲染为中文姓名下方的西文小字行）")
    parser.add_argument("--fictional-label",
                        default="虚构奖项 · 学术致敬 | Fictional Award · Academic Tribute",
                        help="独立固定的虚构奖项/致敬标注（默认开启，底栏居中可读；"
                             "中文用简体字体渲染）。传空串可关闭")
    parser.add_argument("--illustration-credit",
                        default="",
                        help="可选的额外小署名（默认空；虚构奖项标注见 --fictional-label）")
    parser.add_argument("--confirm-copy", action="store_true",
                        help="【文案确认门禁】仅当用户已逐字确认完整中英文案"
                             "（奖项/姓名/双语颁奖词/机构/虚构标注）后才传入；"
                             "缺省时脚本只打印待确认文案并中止，不生成海报")

    # ---- 配色（默认母版：暖灰白纸底 + 哑金 + 暗酒红底栏；由 --palette 驱动）----
    parser.add_argument("--bg-color", default=None,
                        help="画布背景色（缺省取母版纸底 #ece6e5）")
    parser.add_argument("--band-color", default=None,
                        help="底部颁奖词区色块（缺省取母版暗酒红 #522d32）")
    parser.add_argument("--word-color", default="墨黑",
                        help="词云颜色（默认无词云，仅词云模式用）")
    parser.add_argument("--accent-color", default=None,
                        help="核心词点缀色（缺省取母版哑金）")
    parser.add_argument("--accent-words", default=None,
                        help="点缀色作用的词，逗号分隔；缺省取 theme_words 全部")

    # ---- 版式 ----
    parser.add_argument("--top-band-ratio", type=float, default=0.16,
                        help="顶部奖项条占画布高度比例")
    parser.add_argument("--bottom-band-ratio", type=float, default=0.24,
                        help="底部颁奖词区占画布高度比例")
    # ---- 输出尺寸（默认锁定已认可母版 1773x2364；高分辨率须显式 --hi-res）----
    parser.add_argument("--width", type=int, default=1773,
                        help="默认画布宽（母版实测 1773）")
    parser.add_argument("--height", type=int, default=2364,
                        help="默认画布高（母版实测 2364，3:4）")
    parser.add_argument("--hi-res", action="store_true",
                        help="显式输出高分辨率 4320x5760（默认关闭；"
                             "不替换母版 1773x2364 标准尺寸）")

    # ---- 排版参数 ----
    parser.add_argument("--max-words", type=int, default=110)
    parser.add_argument("--min-font", type=int, default=20)
    parser.add_argument("--margin", type=int, default=20)
    parser.add_argument("--font-step", type=int, default=3)
    parser.add_argument("--prefer-horizontal", type=float, default=0.88)

    # ---- 词表控制 ----
    parser.add_argument("--custom-words",
                        help="复合术语文件（每行一个，注入 jieba 防止切碎）")
    parser.add_argument("--extra-stopwords",
                        help="额外停用词文件（每行一个，碎词/残词黑名单）")

    args = parser.parse_args()

    # ---- 0. 母版配色解析（默认即已认可原版海报配色）----
    pal = resolve_nobel_palette(args.palette)
    if args.bg_color is None:
        args.bg_color = pal["bg"]
    if args.band_color is None:
        args.band_color = pal["band"]
    if args.accent_color is None:
        args.accent_color = pal["accent"]

    # ---- 0b. 有序姓名：多人合一张严格按给定顺序从左到右渲染 ----
    if args.awardees:
        ordered = [n.strip() for n in args.awardees.split(",") if n.strip()]
        # 保证 --awardee（主名）在列表中，且顺序以 --awardees 为准
        display_name = "   ·   ".join(ordered)
    else:
        display_name = args.awardee

    # ---- 0c. 文案确认门禁：未逐字确认完整中英文案前禁止生成 ----
    if not args.confirm_copy:
        print("⛔ 文案确认门禁拦截：用户尚未逐字确认完整中英文案，未生成海报。")
        print("── 待确认文案 ──────────────────────────────")
        print(f"  奖项(EN) : {args.prize_en}")
        print(f"  奖项(ZH) : {args.prize_zh}")
        print(f"  姓名     : {display_name}")
        print(f"  颁奖词(EN): {args.citation_en}")
        print(f"  颁奖词(ZH): {args.citation_zh}")
        print(f"  机构     : {args.institution}")
        print(f"  虚构标注 : {args.fictional_label}")
        if args.illustration_credit:
            print(f"  额外署名 : {args.illustration_credit}")
        print("──────────────────────────────────────────")
        print("请把以上文案逐字发给用户确认；确认无误后加 --confirm-copy 重跑。")
        raise SystemExit(2)

    # ---- 1. 画布尺寸：默认锁定母版 1773x2364；--hi-res 才出 4320x5760 ----
    if args.hi_res:
        CW, CH = 4320, 5760
    else:
        CW, CH = args.width, args.height
    S = CH / 5760.0     # 字体/线宽相对原 5760 设计稿的等比缩放
    top_h = int(CH * args.top_band_ratio)
    bottom_h = int(CH * args.bottom_band_ratio)
    combined_path = os.path.join(
        os.path.dirname(args.output) or ".",
        os.path.splitext(os.path.basename(args.output))[0] + "_wc_mask.png")

    bg_hex = resolve_color(args.bg_color)

    # ---- 2. 底图：词云（opt-in）或 纯净背景（默认母版）----
    use_wordcloud = args.wordcloud and not args.no_wordcloud
    if not use_wordcloud:
        print(f"🎨 纯净背景模式（默认母版，无词云）：背景={args.bg_color}  "
              f"颁奖词区={args.band_color}  配色={args.palette}  画布={CW}x{CH}")
        poster = Image.new("RGB", (CW, CH), _hex_rgb(args.bg_color))
    else:
        combined = combine_bands_mask(args.mask, args.top_band_ratio,
                                      args.bottom_band_ratio)
        combined.save(combined_path)

        accent_words = None
        if args.accent_words:
            accent_words = {w.strip() for w in args.accent_words.split(",")
                            if w.strip()}
        elif os.path.exists(args.theme_words):
            accent_words = {w.strip() for w in open(
                args.theme_words, encoding="utf-8")
                if w.strip() and not w.startswith("#")}

        def _read_word_lines(p):
            if not p or not os.path.exists(p):
                return set()
            return {ln.strip() for ln in open(p, encoding="utf-8")
                    if ln.strip() and not ln.startswith("#")}

        custom_words = _read_word_lines(args.custom_words)
        extra_stop = _read_word_lines(args.extra_stopwords)

        print(f"🎨 海报配色：背景={args.bg_color}  词云={args.word_color}"
              f"  点缀={args.accent_color}  颁奖词区={args.band_color}")
        print(f"   背景判定：{'深色' if _is_dark(bg_hex) else '浅色'}")

        poster = build_masked_wordcloud(
            args.corpus, args.theme_words, combined_path,
            args.word_color, args.bg_color,
            args.accent_color, accent_words,
            max_words=args.max_words, min_font=args.min_font,
            margin=args.margin, font_step=args.font_step,
            prefer_horizontal=args.prefer_horizontal,
            extra_stop=extra_stop, custom_words=custom_words)

    # ---- 3. 顶部与底部文字区 ----
    W, H = poster.size
    draw = ImageDraw.Draw(poster)
    latin_font = find_serif_latin() or find_font()
    cjk_font = find_serif_cjk() or find_font()
    text_color = pal["title"]       # 哑金：顶部奖项名
    name_color = pal["name_color"]  # 哑金浅：底栏姓名
    en_color = pal["en_citation"]   # 斜体浅金：英文颁奖词
    zh_color = pal["zh_citation"]   # 近白：中文颁奖词
    inst_color = pal["institution"]  # 哑金：机构
    credit_color = pal["credit"]    # 哑金：致敬署名

    draw_top_band(draw, W, top_h, args.prize_en, args.prize_zh,
                  text_color, pal["divider"], latin_font, cjk_font, S)
    draw_bottom_band(draw, W, H, bottom_h, args.band_color,
                     display_name, args.citation_en, args.citation_zh,
                     args.institution, name_color, en_color, zh_color,
                     inst_color, latin_font, cjk_font, S,
                     fictional_label=args.fictional_label,
                     label_color=zh_color,
                     awardee_en=args.awardee_en,
                     institution_en=args.institution_en)

    # 左下角额外小署名（可选；默认空）
    if args.illustration_credit:
        f_c, _ = _fit_font(draw, args.illustration_credit, latin_font,
                           int(W * 0.4), int(40 * S), start=int(30 * S),
                           min_size=max(8, int(16 * S)))
        draw.text((int(W * 0.035), int(H * 0.965)),
                  args.illustration_credit, font=f_c,
                  fill=_hex_rgb(credit_color))

    # ---- 4. 嵌入人像（默认保留彩色线稿；仅 --reline 走旧黑白重描）----
    poster = overlay_lineart(poster, args.lineart, args.mask,
                             "白", "黑",
                             args.top_band_ratio, args.bottom_band_ratio,
                             natural=not args.reline)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    poster.save(args.output, dpi=(300, 300))
    print(f"✅ 已保存：{args.output}  {poster.size}")


if __name__ == "__main__":
    main()
