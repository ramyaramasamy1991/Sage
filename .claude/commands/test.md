---
description: Run the Sage test suite (mocked Bedrock; no AWS needed)
argument-hint: "[optional pytest node id, e.g. tests/test_chat.py::test_error_is_reported]"
---

Run the project's pytest suite using the venv interpreter
(`.venv\Scripts\python.exe`, since the bare `python.exe` on PATH is the Windows
Store stub).

- If `$ARGUMENTS` is provided, run only that test/node id.
- Otherwise run the whole suite.

Command to run:

```
.\.venv\Scripts\python.exe -m pytest $ARGUMENTS
```

Report pass/fail counts and surface any failures with their output.
