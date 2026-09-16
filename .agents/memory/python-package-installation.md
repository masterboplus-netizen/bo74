---
name: Python package installation in Nix
description: Project Python packages must avoid the immutable Nix interpreter site-packages.
---

Use the project-local `.pythonlibs` site-packages for Python dependencies when the system interpreter is Nix-managed; `uv pip install --system` is blocked by the immutable Nix store even with the break-system-packages override.

**Why:** The workspace's Python interpreter is externally managed and its `/nix/store` site-packages directory is not writable.

**How to apply:** Install with `uv pip install --target .pythonlibs/lib/python3.13/site-packages ...` and include the dependency in `requirements.txt`; workflows need that path on `PYTHONPATH`.