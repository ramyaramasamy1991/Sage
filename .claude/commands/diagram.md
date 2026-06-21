---
description: Regenerate the architecture PNG from the Pillow render script
---

Regenerate `docs/architecture.png` after editing the diagram layout in
`docs/render_png.py` (or `docs/architecture.svg`).

Command (uses the venv interpreter; needs `pillow`, which is in
`requirements-dev.txt`):

```
.\.venv\Scripts\python.exe docs/render_png.py
```

Then read `docs/architecture.png` to visually confirm it rendered correctly, and
note its dimensions. If you changed the diagram's structure, also update
`docs/architecture.svg` and the Mermaid diagrams in `ARCHITECTURE.md` to match.
