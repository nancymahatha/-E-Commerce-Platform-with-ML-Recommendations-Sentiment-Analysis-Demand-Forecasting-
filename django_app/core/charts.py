"""Self-contained SVG chart generators for the admin ML dashboard.

No external JS/CDN is required, so the charts render offline (useful for a viva
demo). Each function returns an SVG/HTML string that templates render with |safe.
"""
import math


def line_chart(daily, labels=None, width=660, height=240,
               stroke="#9c6f52", fill="#ecd9cb", grid="#ece3d8", text="#7a6a5d"):
    if not daily:
        return ""
    n = len(daily)
    pad_l, pad_r, pad_t, pad_b = 46, 14, 16, 28
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    raw_max = max(daily) or 1
    nice_max = math.ceil(raw_max / 5.0) * 5 if raw_max > 5 else raw_max
    if nice_max <= 0:
        nice_max = 1
    maxv = float(nice_max)

    def x(i):
        return pad_l + (i / (n - 1)) * plot_w if n > 1 else pad_l + plot_w / 2

    def y(v):
        return pad_t + plot_h - (v / maxv) * plot_h

    parts = []
    for g in range(5):
        gv = maxv * g / 4
        gy = y(gv)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width-pad_r}" y2="{gy:.1f}" stroke="{grid}" stroke-width="0.5"/>')
        parts.append(f'<text x="{pad_l-6}" y="{gy+3:.1f}" text-anchor="end" font-size="10" fill="{text}">{gv:.0f}</text>')
    area = (f"M{x(0):.1f},{y(daily[0]):.1f} "
            + " ".join(f"L{x(i):.1f},{y(v):.1f}" for i, v in enumerate(daily))
            + f" L{x(n-1):.1f},{y(0):.1f} L{x(0):.1f},{y(0):.1f} Z")
    parts.append(f'<path d="{area}" fill="{fill}" opacity="0.5"/>')
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(daily))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linejoin="round"/>')
    for i, v in enumerate(daily):
        parts.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="2" fill="{stroke}"/>')
    step = max(1, n // 6)
    for i in range(0, n, step):
        lab = labels[i] if labels and i < len(labels) else str(i + 1)
        parts.append(f'<text x="{x(i):.1f}" y="{height-10}" text-anchor="middle" font-size="10" fill="{text}">{lab}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
            f'aria-label="daily demand forecast line chart">' + "".join(parts) + '</svg>')


def bar_chart(pairs, width=660, height=240,
              fill="#c9a78f", grid="#ece3d8", text="#7a6a5d"):
    if not pairs:
        return ""
    n = len(pairs)
    pad_l, pad_r, pad_t, pad_b = 46, 14, 16, 42
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    raw_max = max(float(p[1]) for p in pairs) or 1
    nice_max = math.ceil(raw_max / 5.0) * 5 if raw_max > 5 else raw_max
    if nice_max <= 0:
        nice_max = 1
    maxv = float(nice_max)

    def y(v):
        return pad_t + plot_h - (v / maxv) * plot_h

    parts = []
    for g in range(5):
        gv = maxv * g / 4
        gy = y(gv)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width-pad_r}" y2="{gy:.1f}" stroke="{grid}" stroke-width="0.5"/>')
        parts.append(f'<text x="{pad_l-6}" y="{gy+3:.1f}" text-anchor="end" font-size="10" fill="{text}">{gv:.0f}</text>')
    slot = plot_w / n
    bw = slot * 0.55
    for i, (lab, v) in enumerate(pairs):
        bx = pad_l + slot * i + (slot - bw) / 2
        by = y(v)
        bh = pad_t + plot_h - by
        parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3" fill="{fill}"/>')
        parts.append(f'<text x="{bx+bw/2:.1f}" y="{by-4:.1f}" text-anchor="middle" font-size="10" fill="{text}">{v:.0f}</text>')
        labtxt = lab if len(str(lab)) <= 11 else str(lab)[:10] + "…"
        parts.append(f'<text x="{bx+bw/2:.1f}" y="{height-24}" text-anchor="middle" font-size="9" fill="{text}">{labtxt}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
            f'aria-label="forecast comparison bar chart">' + "".join(parts) + '</svg>')


def donut_chart(counts, size=170, text="#7a6a5d"):
    palette = {
        "positive": "#639922", "neutral": "#BA7517", "negative": "#A32D2D",
        "Positive": "#639922", "Neutral": "#BA7517", "Negative": "#A32D2D",
    }
    items = [(k, v) for k, v in counts.items() if v and v > 0]
    total = sum(v for _, v in items)
    if total == 0:
        return ""
    cx = size / 2
    cy = size / 2
    r_outer = size / 2 - 4
    r_inner = r_outer * 0.6
    r_mid = (r_outer + r_inner) / 2
    circ = 2 * math.pi * r_mid
    offset = 0.0
    segs = []
    legend = []
    for k, v in items:
        frac = v / total
        seg_len = frac * circ
        color = palette.get(k, "#999999")
        segs.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r_mid:.1f}" fill="none" '
            f'stroke="{color}" stroke-width="{r_outer-r_inner:.1f}" '
            f'stroke-dasharray="{seg_len:.2f} {circ-seg_len:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx:.1f} {cy:.1f})"/>'
        )
        pct = frac * 100
        legend.append(
            f'<span style="display:inline-block;margin:3px 10px;font-size:12px;color:{text}">'
            f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
            f'background:{color};margin-right:6px;vertical-align:middle;"></span>'
            f'{k}: {v} ({pct:.0f}%)</span>'
        )
        offset += seg_len
    svg = (f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
           f'role="img" aria-label="sentiment distribution">' + "".join(segs)
           + f'<text x="{cx:.1f}" y="{cy-1:.1f}" text-anchor="middle" font-size="13" fill="{text}">{total}</text>'
           + f'<text x="{cx:.1f}" y="{cy+13:.1f}" text-anchor="middle" font-size="10" fill="{text}">reviews</text>'
           + '</svg>')
    return svg + '<div style="margin-top:8px;">' + "".join(legend) + '</div>'
