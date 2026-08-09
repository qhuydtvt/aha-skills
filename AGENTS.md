# Agent Instructions & Guidelines

## Authentication & Token Management

All AI agents and scripts in this workspace **MUST** adhere to the following rules regarding authentication tokens:

1. **Exclusive Token Retriever**:
   - Always retrieve the AhaSlides authentication token through `TokenManager` in [`scripts/token_manager.py`](scripts/token_manager.py) (e.g., `manager = TokenManager(); token = manager.get_token()`).
   - `TokenManager` is the **only** authorized token retriever in this codebase.

2. **Strict Security & No Exposure**:
   - **STRICT PROHIBITION**: Authentication token values must **NEVER** be printed, logged, echoed to `stdout`/`stderr`, or exposed in output responses.
   - Check token validity safely using `manager.is_token_available()` without inspecting or outputting the raw string.
