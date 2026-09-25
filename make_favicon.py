#!/usr/bin/env python3
"""
生成甜瓜 (Melon) favicon。
在 4096px 画布上矢量绘制后 LANCZOS 降采样，保证 16px 下依然清晰。
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

W = 4096          # 绘制尺寸
LOGIC = 1024      # 逻辑坐标基准


def build_melon(size=W):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    k = size / LOGIC

    def u(v):
        return v * k

    # 放大瓜体填满画布（去掉底板后更有存在感），但四周须留出均衡余量：
    # 顶部要给瓜蒂让位，避免小尺寸缩放下贴边或被裁。
    cx, cy = u(512), u(528)
    rx, ry = u(392), u(414)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)

    def clip(layer):
        layer.putalpha(Image.composite(layer.getchannel("A"),
                                       Image.new("L", (size, size), 0), mask))
        return layer

    # 说明：不放投影阴影、不加白底圆角底板。
    # 去掉底板后瓜体会显得小，故整体放大以填满画布。

    # ---------- 1. 瓜体（球面渐变）----------
    d = ImageDraw.Draw(img)
    steps = 150
    for i in range(steps, 0, -1):
        t = i / steps
        light = (1.0 - t) ** 1.30
        base, hi = (104, 162, 74), (200, 230, 132)
        col = [base[j] + (hi[j] - base[j]) * light for j in range(3)]
        shade = t ** 2.0 * 0.52
        col = [c * (1 - shade) for c in col]
        ox = u(-56) * (1 - t)
        oy = u(-62) * (1 - t)
        d.ellipse([cx + ox - rx * t, cy + oy - ry * t,
                   cx + ox + rx * t, cy + oy + ry * t],
                  fill=tuple(int(c) for c in col) + (255,))

    # ---------- 3. 网纹（正确球面投影）----------
    # 关键：以经度角均匀分布纵纹，横向位置 = sin(经度) * 半径 * cos(纬度)，
    # 用 cos(经度) 控制透视压缩，而不是让线条在两端塌缩。
    net = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    nd = ImageDraw.Draw(net)
    random.seed(7)

    # 真实网纹甜瓜的裂纹是「细碎、断续、不规则交叉」的网格，
    # 不是从顶到底的通长条。这里用两层正弦叠加生成有机的网状场，
    # 沿等值线画短线段，得到自然龟裂感。
    rng = random.Random(7)

    def crack_field(nx, ny):
        """有机噪声场，值域大致 -1..1"""
        v = 0.0
        v += 1.00 * math.sin(nx * 3.1 + 0.7) * math.cos(ny * 2.6 - 0.4)
        v += 0.62 * math.sin(nx * 5.7 - 1.3) * math.cos(ny * 4.9 + 0.9)
        v += 0.34 * math.sin(nx * 9.3 + 2.1) * math.cos(ny * 8.2 - 1.7)
        v += 0.20 * math.sin((nx + ny) * 7.1 + 0.3)
        return v

    N_LON = 9                        # 纵向裂纹组数
    for band in range(N_LON):
        lon = -math.pi / 2 + math.pi * (band + 0.5) / N_LON
        depth = math.cos(lon)                              # 1=正对，0=边缘
        # 沿纬度方向逐段绘制，段间少量断开 —— 连贯为主、断续点缀
        s = 0
        while s < 57:
            seg_len = rng.randint(11, 20)
            pts = []
            for j in range(seg_len):
                ss = min(s + j, 57)
                lat = -math.pi / 2 * 0.93 + (math.pi * 0.93) * (ss / 57.0)
                y = cy + math.sin(lat) * ry
                x = cx + math.sin(lon) * rx * math.cos(lat)
                # 有机抖动用噪声场驱动，比纯正弦自然
                nx_, ny_ = math.sin(lon) * 2.2 + 3.0, lat * 3.4 + band * 0.8
                x += u(22) * crack_field(nx_, ny_) * depth
                pts.append((x, y))
            if len(pts) >= 2:
                alpha = int(104 + 68 * depth)
                wdt = max(1, int(u(4.6 + 3.6 * depth)))
                nd.line(pts, fill=(245, 250, 220, alpha), width=wdt, joint="curve")
            s += seg_len + rng.randint(0, 2)               # 轻微缺口感

    # 横向裂纹：与纵向交织成网格，比纵向稍短稍淡
    for row in range(8):
        lat0 = -math.pi / 2 * 0.86 + (math.pi * 0.86) * (row + 0.5) / 8.0
        f = -1.0
        while f < 0.94:
            span = rng.uniform(0.34, 0.62)
            pts = []
            steps = max(4, int(span * 26))
            for j in range(steps + 1):
                ff = max(-1.0, min(1.0, f + span * (j / steps)))
                lat = lat0 + 0.09 * crack_field(ff * 3.0 + row * 0.9, lat0 * 2.2)
                y = cy + math.sin(lat) * ry
                x = cx + ff * rx * math.cos(lat)
                pts.append((x, y))
            if len(pts) >= 2:
                nd.line(pts, fill=(236, 245, 204, 118),
                        width=max(1, int(u(4.0))), joint="curve")
            f += span + rng.uniform(0.02, 0.09)

    img.alpha_composite(clip(net))

    # ---------- 4. 左上高光 ----------
    hl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hx, hy = cx - rx * 0.42, cy - ry * 0.46
    for i in range(36, 0, -1):
        t = i / 36.0
        hd.ellipse([hx - u(152) * t, hy - u(112) * t,
                    hx + u(152) * t, hy + u(112) * t],
                   fill=(255, 255, 238, int(92 * (1 - t) ** 1.7)))
    img.alpha_composite(clip(hl.filter(ImageFilter.GaussianBlur(u(22)))))

    # ---------- 5. 右下轮廓反光 ----------
    rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    for i in range(28, 0, -1):
        t = i / 28.0
        rr = 0.90 + 0.10 * (1 - t)
        rd.ellipse([cx + u(34) - rx * rr, cy + u(44) - ry * rr,
                    cx + u(34) + rx * rr, cy + u(44) + ry * rr],
                   outline=(255, 250, 198, int(66 * (1 - t) ** 2.0)),
                   width=int(u(15)))
    img.alpha_composite(clip(rim.filter(ImageFilter.GaussianBlur(u(14)))))

    # ---------- 6. 瓜蒂 ----------
    stem = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stem)
    sx, sy = cx + u(4), cy - ry + u(6)
    sd.line([(sx, sy + u(50)), (sx + u(14), sy - u(36))],
            fill=(114, 94, 54, 255), width=int(u(33)))
    sd.ellipse([sx + u(14) - u(32), sy - u(44) - u(21),
                sx + u(14) + u(32), sy - u(44) + u(21)], fill=(128, 106, 60, 255))
    img.alpha_composite(stem.filter(ImageFilter.GaussianBlur(u(3))))

    return img


def main():
    out = os.path.dirname(os.path.abspath(__file__))
    static = os.path.join(out, "static")
    os.makedirs(static, exist_ok=True)

    print("绘制甜瓜（超采样 4096px）…")
    big = build_melon()

    def rs(px):
        return big.resize((px, px), Image.LANCZOS)

    # 不再叠加白底圆角底板，直接输出带透明通道的瓜体本身。
    # ICO 打包要点：基准图必须是最大尺寸，Pillow 才会据此生成全部尺寸；
    # 若拿 16px 当基准，最终只会存下 16x16 一档。
    ico_sizes = [16, 32, 48, 64]
    rs(ico_sizes[-1]).save(
        os.path.join(static, "favicon.ico"), format="ICO",
        sizes=[(s, s) for s in ico_sizes])
    print(f"✅ favicon.ico          {ico_sizes}")

    rs(16).save(os.path.join(static, "favicon-16x16.png"))
    rs(32).save(os.path.join(static, "favicon-32x32.png"))
    print("✅ favicon-16x16.png / favicon-32x32.png")

    rs(180).save(os.path.join(static, "apple-touch-icon.png"))
    print("✅ apple-touch-icon.png [180]")

    rs(192).save(os.path.join(static, "android-chrome-192x192.png"))
    rs(512).save(os.path.join(static, "android-chrome-512x512.png"))
    print("✅ android-chrome-*.png  [192, 512]")

    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
  <path d="M8 1.1c3 0 5.5 2.6 5.5 5.8S11 14.9 8 14.9 2.5 10.1 2.5 6.9 5 1.1 8 1.1z"/>
  <path d="M8.9 1.6l1.4.6-1 2.2-1.3-.5z" fill="#fff" opacity=".8"/>
</svg>
'''
    with open(os.path.join(static, "safari-pinned-tab.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    print("✅ safari-pinned-tab.svg")

    og = Image.new("RGBA", (1200, 630), (252, 253, 248, 255))
    mel = rs(470)
    og.alpha_composite(mel, ((1200 - 470) // 2, (630 - 470) // 2 - 24))
    og.convert("RGB").save(os.path.join(static, "og-cover.png"), quality=92)
    print("✅ og-cover.png         [1200x630]")

    big.resize((512, 512), Image.LANCZOS).save(os.path.join(out, "_melon-preview.png"))

    # 小尺寸真实性检查：拼一张对比图（浅灰底，便于观察透明边缘）
    strip = Image.new("RGBA", (16 + 32 + 48 + 64 + 3 * 20, 64), (240, 240, 240, 255))
    x = 0
    for s in (16, 32, 48, 64):
        strip.alpha_composite(rs(s), (x, 64 - s))
        x += s + 20
    strip.save(os.path.join(out, "_favicon-sizes.png"))
    print("\n预览: _melon-preview.png / _favicon-sizes.png")


if __name__ == "__main__":
    main()
