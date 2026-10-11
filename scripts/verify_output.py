#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成品图交付前校验
================
把过去靠肉眼+临时脚本反复排查的问题固化成自动检查。
覆盖三类已经真实踩过的坑：

  1. 人像区域渗入背景色 —— 剪影轮廓被 rembg 啃缺，深色背景版会露出
     背景色三角。白背景版肉眼完全看不出来，必须量化检查。
  2. 人像糊成 X 光片 —— 人像底色跟随了深背景，五官不可辨。
     用人像区域的亮度分布判断：应当是"大面积亮底 + 少量暗线"。
  3. 词云过密 / 留白不足 —— 影响可读性。

用法：
  python verify_output.py --image gift.png --mask mask.png [--bg-color 藏蓝]

  # 同时校验多张
  python verify_output.py --image a.png b.png c.png --mask mask.png

退出码 0 = 全部通过，1 = 存在问题。
"""

import argparse
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palettes import resolve_color, _hex_to_rgb          # noqa: E402


def _load_pair(image_path, mask_path):
    img = Image.open(image_path).convert("RGB")
    mask = Image.open(mask_path).convert("L").resize(img.size, Image.LANCZOS)
    return np.array(img).astype(int), np.array(mask) > 128


def _bg_rgb(arr, bg_color):
    """取画布背景色；未指定时从四角采样推断"""
    if bg_color is not None:
        return np.array(_hex_to_rgb(resolve_color(bg_color)), dtype=float)
    h, w = arr.shape[:2]
    corners = np.array([arr[5, 5], arr[5, w - 6],
                        arr[h - 6, 5], arr[h - 6, w - 6]])
    return np.median(corners, axis=0)


def _ideal_envelope(sil, bottom_zone_ratio=0.25, notch_tol=18,
                    max_grow_ratio=0.12):
    """由剪影推出"本应如此"的理想轮廓包络

    【为什么必需】不能直接用传入的 mask 判断轮廓完整性 —— 如果 mask
    本身就带啃缺，缺口区域在 mask 里已被标成"非人像"，比对时自然
    检测不到渗入，检查会假阳性通过。必须先把 mask 修补成理想包络，
    再看包络内是否出现背景色。

    【必须限制外扩幅度】早期版本用底部区间的全局 95 分位数做包络，
    人像底部宽度不均匀时包络会被撑到远超真实轮廓，把大片词云区圈成
    "人像"，产生 16% 量级的假阳性。这里改为：
      - 逐行只与上下邻近行比较，补孤立凹陷
      - 单行外扩量不超过画布宽度的 max_grow_ratio（实测缺口深度可达
        画布宽度的 9%，上限不能设得比缺口还小，否则真实缺口会被当成
        "外扩过度"而挡掉）
      - 整体外扩面积超过原剪影 5% 时判定为包络失控，放弃修补
    """
    env = sil.copy()
    rows = np.where(sil.any(axis=1))[0]
    if rows.size == 0:
        return env
    top, bottom = rows.min(), rows.max()
    height = bottom - top
    width = sil.shape[1]
    max_grow = int(width * max_grow_ratio)

    zone_start = bottom - int(height * bottom_zone_ratio)

    lefts = np.full(bottom + 1, -1, dtype=int)
    rights = np.full(bottom + 1, -1, dtype=int)
    for y in range(zone_start, bottom + 1):
        xs = np.where(sil[y])[0]
        if xs.size:
            lefts[y], rights[y] = xs.min(), xs.max()

    valid = np.where(rights[zone_start:] >= 0)[0] + zone_start
    if valid.size < 12:
        return env

    # 【窗口必须高于缺口】缺口可达数百行；若参考窗口比缺口矮，窗口会
    # 整体落在缺口内部，取到的"正常边界"其实是缺口自己的边界，修补
    # 完全失效。这里直接用底部整段的分位数作基准，并靠外扩上限兜底。
    wr_all = rights[valid]
    wl_all = lefts[valid]
    tgt_r = int(np.percentile(wr_all, 88))
    tgt_l = int(np.percentile(wl_all, 12))

    for y in valid:
        if notch_tol < tgt_r - rights[y] <= max_grow:
            env[y, rights[y]:tgt_r + 1] = True
        if notch_tol < lefts[y] - tgt_l <= max_grow:
            env[y, tgt_l:lefts[y] + 1] = True

    # 外扩失控保护
    grown = int(env.sum() - sil.sum())
    if grown > sil.sum() * 0.05:
        return sil.copy()
    return env


def check_bg_intrusion(arr, sil, bg_color, tol=60):
    """理想轮廓包络内不应出现成片的画布背景色

    检查范围是修补后的包络而非原 mask，这样即使传入的 mask 自身带
    啃缺，也能把缺口暴露出来。

    【为什么不能按颜色判断】深色背景配黑墨线时（背景 #141821、墨线
    #1c1c1c），两者颜色距离极小，人像墨线会被整片误判成背景。试过
    形态学腐蚀去细线，但排线密集处会连成片，仍然误报 13%。

    【最终判据：亮底锚点 + 贴边 + 填充率】人像永远是"白底黑线"，所以
    人像内部必然存在大面积连通亮底，墨线被亮底四面包围、不接触轮廓
    边缘；而真正的缺口紧贴轮廓边缘、内部密实。三个条件同时满足才判为
    缺口：
      1. 非亮底且接近背景色
      2. 明显接触包络边缘（墨线内嵌，不贴边）
      3. bbox 填充率 >= 0.35（排线稀疏交织，填充率低）
    """
    bg_rgb = _bg_rgb(arr, bg_color)
    env = _ideal_envelope(sil)

    gray = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1]
            + 0.114 * arr[:, :, 2])
    bright = (gray > 200) & env          # 人像亮底

    d = np.abs(arr - bg_rgb).sum(axis=2)
    cand = env & (~bright) & (d < tol)

    edge = env & (~ndimage.binary_erosion(env, structure=np.ones((3, 3))))
    lab, k = ndimage.label(cand)

    total = int(env.sum())
    thresh = max(3000, total * 0.002)
    flagged = 0
    biggest = None

    for i in range(1, k + 1):
        blob = (lab == i)
        size = int(blob.sum())
        if size < thresh:
            continue
        if int((blob & edge).sum()) < 30:
            continue                     # 内嵌于人像 -> 墨线
        yy, xx = np.where(blob)
        bbox = (yy.max() - yy.min() + 1) * (xx.max() - xx.min() + 1)
        if bbox and size / bbox < 0.35:
            continue                     # 稀疏交织 -> 排线
        flagged += size
        if biggest is None or size > biggest[0]:
            biggest = (size, yy.min(), yy.max(), xx.min(), xx.max())

    msgs = []
    if biggest:
        s_, y0, y1, x0, x1 = biggest
        msgs.append(
            f"人像轮廓内有成片背景色 {flagged}px，"
            f"最大块 {s_}px 位于 x[{x0}-{x1}] y[{y0}-{y1}]，应为 mask 啃缺")

    ratio = flagged / total * 100 if total else 0.0
    detail = f"轮廓内成片背景色 {flagged}px ({ratio:.3f}%)"
    return not msgs, detail, msgs


def check_portrait_clarity(arr, sil):
    """人像应为『亮底 + 暗线』的线条图，不能是低对比糊块"""
    gray = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1]
            + 0.114 * arr[:, :, 2])
    vals = gray[sil]
    if vals.size == 0:
        return False, "人像区域为空", ["人像区域为空"]

    bright = float((vals > 200).mean())    # 底
    dark = float((vals < 100).mean())      # 墨线
    mid = float(((vals >= 100) & (vals <= 200)).mean())

    msgs = []
    if bright < 0.45:
        msgs.append(f"人像亮底仅 {bright*100:.0f}%（应 >45%），"
                    f"疑似底色跟随了深背景，会呈 X 光片效果")
    if dark < 0.02:
        msgs.append(f"人像墨线仅 {dark*100:.1f}%（应 >2%），线条过弱")
    if mid > 0.45:
        msgs.append(f"中间灰占 {mid*100:.0f}%（应 <45%），对比不足易糊")

    detail = f"亮底 {bright*100:.0f}% / 墨线 {dark*100:.0f}% / 中灰 {mid*100:.0f}%"
    return not msgs, detail, msgs


def check_wordcloud_density(arr, sil, bg_color):
    """词云区域留白应充足，过密影响可读性"""
    bg_rgb = _bg_rgb(arr, bg_color)
    word_zone = ~sil
    d = np.abs(arr - bg_rgb).sum(axis=2)
    blank = (d < 60) & word_zone
    ratio = float(blank.sum() / word_zone.sum()) if word_zone.sum() else 0.0

    msgs = []
    if ratio < 0.42:
        msgs.append(f"词云区留白仅 {ratio*100:.0f}%（建议 >42%），"
                    f"偏密，可降 --max-words 或提高 --margin")
    detail = f"词云区留白 {ratio*100:.0f}%"
    return not msgs, detail, msgs


CHECKS = [
    ("背景色渗入人像", check_bg_intrusion, True),
    ("人像线条清晰度", check_portrait_clarity, False),
    ("词云留白充足度", check_wordcloud_density, True),
]


# 中日字形分歧字（Han unification）：同一 Unicode 码位，
# 简体中文与日文的写法不同。若字体误用 JP 子字体，这些字会显示成日文写法。
_CJK_DIVERGENT = "与直值骨图关决净收压铁强练每画海"


def check_font_is_sc(verbose=True):
    """检查合成时实际使用的字体是简体中文(SC)而非日文(JP)子字体

    【为什么需要这项检查】
    NotoSansCJK-*.ttc 内部按 JP / KR / SC / TC / HK 装了五个子字体，
    加载 .ttc 默认取 index=0（日文）。中日共用 Unicode 码位但字形不同，
    于是「与」会被渲染成竖折斜穿的日式写法而非简体的横折折折钩。

    这个缺陷只在词表恰好包含分歧字时才显形，因此必须机器检查而非靠肉眼，
    否则会长期潜伏。做法是逐字比对 SC 与 JP 子字体的字形轮廓，
    确认当前字体的写法与 SC 一致、与 JP 不同。
    """
    msgs = []
    try:
        from fontTools import ttLib
        try:
            import compose_poster as compose_mod
        except ImportError:
            import compose_gift as compose_mod
    except Exception as e:
        return True, f"跳过（无法导入：{e}）", []

    font_path = compose_mod.find_font()
    if not font_path:
        return False, "未找到可用 CJK 字体", ["未找到可用 CJK 字体"]

    name = ""
    try:
        if font_path.lower().endswith(".ttc"):
            coll = ttLib.TTCollection(font_path)
            name = coll.fonts[0]["name"].getDebugName(1) or ""
        else:
            name = ttLib.TTFont(font_path)["name"].getDebugName(1) or ""
    except Exception as e:
        return True, f"跳过（字体读取失败：{e}）", []

    # 一票否决：名称里带 JP / KR 说明用的是日文或韩文子字体
    if " JP" in name or " KR" in name:
        msgs.append(
            f"当前字体为「{name}」，非简体中文子字体。"
            f"「{_CJK_DIVERGENT[:6]}」等中日分歧字会渲染成日文写法，"
            f"须抽取 CJK SC 子字体后再合成")
        return False, f"字体：{name}（❌ 非 SC）", msgs

    # 逐字校验：与同一 ttc 里的 JP 子字体比对轮廓
    diverge_ok, checked = 0, 0
    try:
        src_ttc = next((p for p in compose_mod._FONT_CANDIDATES
                        if os.path.exists(p) and p.lower().endswith(".ttc")),
                       None)
        if src_ttc:
            coll = ttLib.TTCollection(src_ttc)
            jp = next((f for f in coll.fonts
                       if " JP" in (f["name"].getDebugName(1) or "")), None)
            cur = ttLib.TTFont(font_path) if not font_path.endswith(".ttc") \
                else coll.fonts[0]
            if jp is not None:
                jg, cg_ = jp.getGlyphSet(), cur.getGlyphSet()
                jcmap, ccmap = jp.getBestCmap(), cur.getBestCmap()
                from fontTools.pens.boundsPen import BoundsPen
                for ch in _CJK_DIVERGENT:
                    cp = ord(ch)
                    if cp not in jcmap or cp not in ccmap:
                        continue
                    try:
                        bp1, bp2 = BoundsPen(jg), BoundsPen(cg_)
                        jg[jcmap[cp]].draw(bp1)
                        cg_[ccmap[cp]].draw(bp2)
                    except Exception:
                        continue
                    checked += 1
                    if bp1.bounds != bp2.bounds:
                        diverge_ok += 1
    except Exception:
        pass

    detail = f"字体：{name}"
    if checked:
        detail += f"（{diverge_ok}/{checked} 个分歧字与 JP 写法不同）"
        if diverge_ok == 0:
            msgs.append(
                f"检查的 {checked} 个中日分歧字与 JP 子字体轮廓完全相同，"
                f"当前字体可能仍是日文写法")
    return not msgs, detail, msgs


def verify(image_path, mask_path, bg_color=None):
    print(f"\n{'='*62}")
    print(f"🔍 {os.path.basename(image_path)}")
    arr, sil = _load_pair(image_path, mask_path)
    print(f"   尺寸 {arr.shape[1]}x{arr.shape[0]}，"
          f"人像占 {sil.mean()*100:.1f}%")
    print(f"{'-'*62}")

    all_msgs = []
    for name, fn, needs_bg in CHECKS:
        if needs_bg:
            ok, detail, msgs = fn(arr, sil, bg_color)
        else:
            ok, detail, msgs = fn(arr, sil)
        flag = "✅" if ok else "❌"
        print(f"   {flag} {name:<16} {detail}")
        for m in msgs:
            print(f"        → {m}")
        all_msgs.extend(msgs)

    ok, detail, msgs = check_font_is_sc()
    flag = "✅" if ok else "❌"
    print(f"   {flag} {'字形为简体中文':<16} {detail}")
    for m in msgs:
        print(f"        → {m}")
    all_msgs.extend(msgs)
    return all_msgs


def main():
    ap = argparse.ArgumentParser(description="成品图交付前自动校验")
    ap.add_argument("--image", required=True, nargs="+",
                    help="成品图路径，可传多张")
    ap.add_argument("--mask", required=True, help="生成时用的剪影 mask")
    ap.add_argument("--bg-color",
                    help="画布背景色（色名或 HEX）；不给则从四角推断")
    args = ap.parse_args()

    total = []
    for p in args.image:
        total.extend(verify(p, args.mask, args.bg_color))

    print(f"\n{'='*62}")
    if total:
        print(f"❌ 共发现 {len(total)} 个问题，需修复后再交付")
        raise SystemExit(1)
    print("✅ 全部检查通过，可以交付")


if __name__ == "__main__":
    main()
