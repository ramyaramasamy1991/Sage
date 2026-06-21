---
description: Start the Sage web app locally (uvicorn, port 8000)
---

Start the Sage FastAPI web app for local use, using the venv interpreter
(`.venv\Scripts\python.exe` — the bare `python.exe` on PATH is the Windows Store
stub).

- Run it in the background so the session isn't blocked.
- Then report the URL (http://127.0.0.1:8000) and confirm `/api/health` responds.

Command:

```
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Note: the app needs a configured `.env` (AWS_REGION, BEDROCK_MODEL_ID) and valid
AWS credentials to actually answer chats; it will still start and serve the UI
without them.
