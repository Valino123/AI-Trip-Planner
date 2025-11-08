import os

# Load role template from prompts/role.txt for easier editing/versioning
_DEF = (
    "You are a helpful travel planner. Use tools when needed. "
    "Keep answers concise and actionable."
)

try:
    _DIR = os.path.dirname(os.path.abspath(__file__))
    _PROMPT_PATH = os.path.join(_DIR, "prompts", "role.txt")
    if os.path.exists(_PROMPT_PATH):
        with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
            role_template = f.read().strip() or _DEF
    else:
        role_template = _DEF
except Exception:
    role_template = _DEF
