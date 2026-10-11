#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从人像线稿提取人物剪影，生成 wordcloud 用的 mask
=================================================
仓库约定（paper-wordcloud 模块第 207 行）：
    processed_mask = np.where(mask_array < 128, 0, 255)
    → mask 值 255（白）= 不放词
    → mask 值 0  （黑）= 放词

与 paper-wordcloud-portrait 的区别：
  - 支持 --bottom-offset：人物底边离画布底边的距离（海报需要在
    底部留出颁奖词区，人物不再贴齐底边）。
  - 支持 --v-align：'bottom'（贴底，默认，兼容原 skill）或
    'center'（人物垂直居中，适合多人/无底部文字区场景）。

mask 约定：黑色(0)=放词区域，白色(255)=不放词（人物剪影）。
"""

import numpy as np
from PIL import Image, ImageFilter
from rembg import remove, new_session
from scipy import ndimage

W, H = 1080, 1440          # 3:4，主脚本会按 4x 放大到 4320x5760


def _fill_rows(person: np.ndarray,
               skip_top_ratio: float = 0.28,
               notch_tol: int = 18,
               bottom_zone_ratio: float = 0.25) -> np.ndarray:
    """修补剪影的两类缺陷，保证深色背景下轮廓不露出背景色三角

    缺陷来源：线稿上衣服、肩部的排线很稀疏，接近纯白，rembg 会把这些
    淡色区域误判成背景。缺口在白背景版上看不出来（同为白色），但深色
    背景版会露出一块背景色三角，非常明显。

    修两类：
      1. 行内空洞 —— 每行最左与最右之间的空隙直接填实
      2. 底部边缘啃缺 —— 缺口从轮廓外缘往里啃，行内没有空隙，填洞修不掉。
         躯干最下段（贴画布底边那部分）左右轮廓基本垂直，不该有收窄，
         所以用该区间的边界包络做基准，把孤立凹陷补回来。

    skip_top_ratio:    顶部跳过比例。头发外缘有真实镂空缝隙，整体填实
                       会让发型变成实心块，只对肩部以下生效。
    notch_tol:         边界内缩超过该像素数才判定为异常。
    bottom_zone_ratio: 只在剪影最下这一比例的高度内做包络修补。**不要
                       扩大到整个躯干** —— 肩部到腰部本身是渐变收窄的，
                       全局包络会把正常轮廓一起填平，人像变成方块。
    """
    out = person.copy()
    rows = np.where(person.any(axis=1))[0]
    if rows.size == 0:
        return out

    top, bottom = rows.min(), rows.max()
    height = bottom - top
    start = top + int(height * skip_top_ratio)

    # ---- 第一步：填行内空洞 ----
    for y in range(start, bottom + 1):
        xs = np.where(person[y])[0]
        if xs.size >= 2:
            out[y, xs.min():xs.max() + 1] = True

    # ---- 第二步：底部区间用边界包络修啃缺 ----
    zone_start = bottom - int(height * bottom_zone_ratio)
    zone_start = max(zone_start, start)

    lefts, rights, ys = [], [], []
    for y in range(zone_start, bottom + 1):
        xs = np.where(out[y])[0]
        if xs.size:
            ys.append(y)
            lefts.append(xs.min())
            rights.append(xs.max())
    if len(ys) < 5:
        return out

    lefts = np.array(lefts)
    rights = np.array(rights)
    # 该区间轮廓应当垂直，用极值作包络基准
    env_r = int(np.percentile(rights, 95))
    env_l = int(np.percentile(lefts, 5))

    for i, y in enumerate(ys):
        if env_r - rights[i] > notch_tol:
            out[y, rights[i]:env_r + 1] = True
        if lefts[i] - env_l > notch_tol:
            out[y, env_l:lefts[i] + 1] = True

    return out


def audit_silhouette(mask_arr: np.ndarray,
                     bottom_zone_ratio: float = 0.25,
                     notch_tol: int = 18,
                     verbose: bool = True) -> list:
    """检查剪影轮廓是否残留啃缺，返回问题描述列表（空列表=通过）"""
    sil = mask_arr > 128
    problems = []

    rows = np.where(sil.any(axis=1))[0]
    if rows.size == 0:
        return ["剪影为空"]

    top, bottom = rows.min(), rows.max()
    height = bottom - top

    # 1) 闭合空洞
    filled = ndimage.binary_fill_holes(sil)
    holes = filled & (~sil)
    lab, n = ndimage.label(holes)
    if n:
        sizes = ndimage.sum(holes, lab, range(1, n + 1))
        big = [s for s in sizes if s > 40]
        if big:
            problems.append(f"存在 {len(big)} 处闭合空洞，"
                            f"最大 {int(max(big))}px")

    # 2) 底部区间的边界凹陷
    zone_start = bottom - int(height * bottom_zone_ratio)
    lefts, rights, ys = [], [], []
    for y in range(zone_start, bottom + 1):
        xs = np.where(sil[y])[0]
        if xs.size:
            ys.append(y)
            lefts.append(xs.min())
            rights.append(xs.max())

    if len(ys) >= 5:
        lefts, rights = np.array(lefts), np.array(rights)
        env_r = int(np.percentile(rights, 95))
        env_l = int(np.percentile(lefts, 5))
        nr = int((env_r - rights > notch_tol).sum())
        nl = int((lefts - env_l > notch_tol).sum())
        if nr:
            problems.append(f"底部右边界有 {nr} 行凹陷 "
                            f"(包络 x={env_r}, 最深 x={int(rights.min())})")
        if nl:
            problems.append(f"底部左边界有 {nl} 行凹陷 "
                            f"(包络 x={env_l}, 最深 x={int(lefts.max())})")

    if verbose:
        if problems:
            print("   ⚠️  轮廓自检发现问题：")
            for p in problems:
                print(f"      - {p}")
        else:
            print("   ✅ 轮廓自检通过：无空洞、无边界凹陷")
    return problems


def extract_silhouette(photo_path: str,
                       out_path: str,
                       portrait_height_ratio: float = 0.66,
                       dilate_px: int = 16,
                       bottom_offset: int = 0,
                       v_align: str = "bottom",
                       skip_top_ratio: float = 0.28,
                       bottom_zone_ratio: float = 0.25,
                       notch_tol: int = 18) -> None:
    """从线稿/照片抠出人物，生成黑底白剪影 mask

    portrait_height_ratio: 人像占画布高度比例
    dilate_px: 剪影向外扩张，给线稿留安全边距，词不会贴到线上
    bottom_offset: 人物底边距画布底边的距离（海报版式在底部留颁奖词区）
    v_align: 'bottom' 底边贴齐 bottom_offset；'center' 垂直居中
    skip_top_ratio / bottom_zone_ratio / notch_tol: 见 _fill_rows
    """
    src = Image.open(photo_path).convert("RGB")
    # 抠图前先放大，提高 alpha 边缘精度
    work = src.resize((900, int(900 * src.height / src.width)), Image.LANCZOS)
    cut = remove(work, session=new_session("u2netp"))

    alpha = np.array(cut)[:, :, 3]
    person = alpha > 128

    # 取最大连通域，去掉零散噪点
    labels, n = ndimage.label(person)
    if n > 0:
        sizes = ndimage.sum(person, labels, range(1, n + 1))
        person = (labels == (np.argmax(sizes) + 1))

    # 填充内部空洞
    person = ndimage.binary_fill_holes(person)

    # 修补 rembg 在淡色排线处啃出的轮廓缺口（详见 _fill_rows 文档）
    person = _fill_rows(person, skip_top_ratio,
                        notch_tol, bottom_zone_ratio)

    # 向外扩张，给线稿留安全边距
    if dilate_px > 0:
        person = ndimage.binary_dilation(
            person, structure=np.ones((dilate_px, dilate_px)))

    sil = Image.fromarray((person * 255).astype(np.uint8), "L")

    # 裁到紧贴人物的 bbox
    bbox = sil.getbbox()
    if bbox:
        sil = sil.crop(bbox)

    # 缩放并贴到画布
    target_h = int(H * portrait_height_ratio)
    target_w = int(target_h * sil.width / sil.height)
    if target_w > int(W * 0.92):
        target_w = int(W * 0.92)
        target_h = int(target_w * sil.height / sil.width)
    sil = sil.resize((target_w, target_h), Image.LANCZOS)

    canvas = Image.new("L", (W, H), 0)          # 黑底 = 放词区
    px = (W - target_w) // 2
    if v_align == "center":
        py = max(0, (H - target_h) // 2)
    else:
        py = max(0, H - target_h - bottom_offset)   # 底边锚定离底 bottom_offset
    canvas.paste(sil, (px, py))

    # 二值化收紧边缘
    canvas = canvas.filter(ImageFilter.GaussianBlur(2))
    canvas = Image.fromarray(
        np.where(np.array(canvas) > 100, 255, 0).astype(np.uint8), "L")

    canvas.save(out_path)
    arr = np.array(canvas)
    white_ratio = (arr > 128).mean()
    print(f"✅ mask 已保存：{out_path}  {canvas.size}")
    print(f"   人物剪影（不放词）占 {white_ratio*100:.1f}%，"
          f"放词区占 {100-white_ratio*100:.1f}%")
    if not 0.20 <= white_ratio <= 0.42:
        print(f"   ⚠️  剪影占比偏离常规区间 25-35%，"
              f"可调 --height-ratio")

    # 轮廓自检：白背景版看不出缺口，必须靠量化检查
    audit_silhouette(arr, bottom_zone_ratio, notch_tol)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="从线稿/人像照片提取剪影生成 wordcloud mask")
    parser.add_argument("--photo", required=True,
                        help="线稿或人像照片路径（推荐传线稿，与最终嵌入图对齐）")
    parser.add_argument("--output", default="mask_portrait.png",
                        help="输出 mask 路径")
    parser.add_argument("--height-ratio", type=float, default=0.60,
                        help="人像占画布高度比例（海报建议 0.5-0.6）")
    parser.add_argument("--dilate", type=int, default=16,
                        help="剪影向外扩张像素数")
    parser.add_argument("--bottom-offset", type=int, default=0,
                        help="人物底边距画布底边距离（海报版式用，默认贴底）")
    parser.add_argument("--v-align", choices=["bottom", "center"],
                        default="bottom",
                        help="垂直对齐：bottom 贴底（默认），center 居中")
    parser.add_argument("--skip-top-ratio", type=float, default=0.28,
                        help="顶部跳过比例，保护头发镂空缝隙")
    parser.add_argument("--bottom-zone-ratio", type=float, default=0.25,
                        help="底部包络修补区间比例，勿调大否则人像变方块")
    parser.add_argument("--notch-tol", type=int, default=18,
                        help="边界内缩判定阈值（像素）")
    parser.add_argument("--audit-only", metavar="MASK",
                        help="只对已有 mask 做轮廓自检，不重新生成")
    args = parser.parse_args()

    if args.audit_only:
        m = np.array(Image.open(args.audit_only).convert("L"))
        print(f"🔍 自检 {args.audit_only}  {m.shape[1]}x{m.shape[0]}")
        probs = audit_silhouette(m, args.bottom_zone_ratio, args.notch_tol)
        raise SystemExit(1 if probs else 0)

    extract_silhouette(args.photo, args.output,
                       args.height_ratio, args.dilate,
                       args.bottom_offset, args.v_align,
                       args.skip_top_ratio, args.bottom_zone_ratio,
                       args.notch_tol)
