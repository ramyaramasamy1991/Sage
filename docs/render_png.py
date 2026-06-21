"""Render docs/architecture.png with Pillow (no native SVG deps needed).

Mirrors the layout of docs/architecture.svg.  Run:  python docs/render_png.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

S = 2  # supersample factor for crisp text
W, H = 900 * S, 600 * S
OUT = Path(__file__).resolve().parent / "architecture.png"

# Colors
INK = "#0f172a"
MUTED = "#475569"
GRAY = "#475569"
BLUE = "#2563eb"
RED = "#dc2626"
BROWN = "#92400e"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (["arialbd.ttf", "seguisb.ttf"] if bold else ["arial.ttf", "segoeui.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size * S)
        except OSError:
            continue
    return ImageFont.load_default()


img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


def box(x, y, w, h, fill, stroke, radius=8, sw=1.5):
    d.rounded_rectangle(
        [x * S, y * S, (x + w) * S, (y + h) * S],
        radius=radius * S, fill=fill, outline=stroke, width=max(1, int(sw * S)),
    )


def text(x, y, s, size, color=INK, bold=False, anchor="mm"):
    d.text((x * S, y * S), s, font=font(size, bold), fill=color, anchor=anchor)


def line(p1, p2, color=GRAY, sw=1.5):
    d.line([p1[0] * S, p1[1] * S, p2[0] * S, p2[1] * S], fill=color, width=max(1, int(sw * S)))


def arrowhead(start, end, color=GRAY):
    dx, dy = end[0] - start[0], end[1] - start[1]
    dist = math.hypot(dx, dy) or 1
    ux, uy = dx / dist, dy / dist
    L, Wd = 9, 5
    bx, by = end[0] - ux * L, end[1] - uy * L
    px, py = -uy, ux
    p1 = ((bx + px * Wd) * S, (by + py * Wd) * S)
    p2 = ((bx - px * Wd) * S, (by - py * Wd) * S)
    d.polygon([(end[0] * S, end[1] * S), p1, p2], fill=color)


def arrow(p1, p2, color=GRAY, sw=1.5):
    line(p1, p2, color, sw)
    arrowhead(p1, p2, color)


def dashed(p1, p2, color, sw=1.5, dash=8, gap=5):
    x1, y1 = p1
    x2, y2 = p2
    total = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / total, (y2 - y1) / total
    pos = 0.0
    while pos < total:
        a = (x1 + ux * pos, y1 + uy * pos)
        b = (x1 + ux * min(pos + dash, total), y1 + uy * min(pos + dash, total))
        line(a, b, color, sw)
        pos += dash + gap


# Title
text(450, 26, "Sage — Architecture", 20, INK, bold=True)

# Clients
box(170, 50, 200, 56, "#dbeafe", BLUE)
text(270, 73, "Web UI", 14, INK, bold=True)
text(270, 91, "multi-chat · SSE client", 11, MUTED)
box(530, 50, 200, 56, "#dbeafe", BLUE)
text(630, 73, "Terminal CLI", 14, INK, bold=True)
text(630, 91, "app/cli.py · stdio", 11, MUTED)

# Server container
box(60, 140, 780, 320, "#f8fafc", "#94a3b8", radius=12)
text(76, 156, "FastAPI server (app/)", 13, "#334155", bold=True, anchor="lm")

box(84, 176, 180, 48, "#eef2f7", "#94a3b8", radius=6, sw=1)
text(174, 196, "config.py — settings/models", 11, MUTED)
text(174, 212, "errors.py — friendly errors", 11, MUTED)

box(350, 180, 200, 48, "white", MUTED, radius=6, sw=1.3)
text(450, 198, "main.py", 13, INK, bold=True)
text(450, 216, "routes · auth · SSE", 10.5, MUTED)

box(350, 262, 200, 48, "white", MUTED, radius=6, sw=1.3)
text(450, 280, "chat.py", 13, INK, bold=True)
text(450, 298, "orchestration · persona", 10.5, MUTED)

box(110, 372, 180, 50, "white", MUTED, radius=6, sw=1.3)
text(200, 390, "rag.py", 13, INK, bold=True)
text(200, 408, "KB retrieval (boto3)", 10.5, MUTED)

box(360, 372, 180, 50, "white", MUTED, radius=6, sw=1.3)
text(450, 390, "store.py", 13, INK, bold=True)
text(450, 408, "session memory", 10.5, MUTED)

box(610, 372, 180, 50, "white", MUTED, radius=6, sw=1.3)
text(700, 389, "bedrock_client.py", 13, INK, bold=True)
text(700, 407, "AnthropicBedrock", 10.5, MUTED)

# External
box(110, 510, 180, 58, "#fef3c7", "#d97706")
text(200, 532, "Bedrock Knowledge Base", 12.5, INK, bold=True)
text(200, 550, "Retrieve (vector search)", 10.5, BROWN)
box(360, 510, 180, 58, "#fee2e2", RED)
text(450, 532, "Redis", 13, INK, bold=True)
text(450, 550, "optional persistence", 10.5, "#991b1b")
box(610, 510, 180, 58, "#fef3c7", "#d97706")
text(700, 532, "Claude on Bedrock", 13, INK, bold=True)
text(700, 550, "streamed tokens (HTTPS)", 10.5, BROWN)

# Arrows
arrow((285, 106), (410, 178))
line((630, 106), (630, 286)); arrow((630, 286), (552, 286))
arrow((450, 228), (450, 260))
arrow((395, 310), (225, 370))
arrow((450, 310), (450, 370))
arrow((505, 310), (675, 370))
arrow((200, 422), (200, 508))
arrow((700, 422), (700, 508))
dashed((450, 422), (450, 504), RED)
arrowhead((450, 460), (450, 508), RED)

# Labels
text(300, 132, "POST /api/chat (SSE)", 10.5, BLUE, anchor="lm")
text(640, 176, "stdio", 10.5, BLUE, anchor="lm")
text(208, 468, "Retrieve", 10.5, BROWN, anchor="lm")
text(458, 468, "if REDIS_URL", 10.5, RED, anchor="lm")
text(708, 468, "stream", 10.5, BROWN, anchor="lm")
text(76, 586, "Dashed = optional · Amber = Amazon Bedrock · Red = Redis · Blue = clients",
     10.5, "#64748b", anchor="lm")

img.save(OUT)
print(f"Wrote {OUT} ({img.width}x{img.height})")
