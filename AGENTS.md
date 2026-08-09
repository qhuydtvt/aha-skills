# Agent Instructions & Guidelines

## Authentication & Token Management

All AI agents and scripts in this workspace **MUST** adhere to the following rules regarding authentication tokens:

1. **Exclusive Token Retriever**:
   - Always retrieve the AhaSlides authentication token through `TokenManager` in [`scripts/token_manager.py`](scripts/token_manager.py) (e.g., `manager = TokenManager(); token = manager.get_token()`).
   - `TokenManager` is the **only** authorized token retriever in this codebase.

2. **Strict Security & No Exposure**:
   - **STRICT PROHIBITION**: Authentication token values must **NEVER** be printed, logged, echoed to `stdout`/`stderr`, or exposed in output responses.
   - Check token validity safely using `manager.is_token_available()` without inspecting or outputting the raw string.

## Shared API Client Architecture

All scripts performing HTTP requests to AhaSlides APIs **MUST** use the shared API client module:

1. **Shared Client Usage**:
   - Use `AhaApiClient` from [`scripts/shared/api/aha_client.py`](scripts/shared/api/aha_client.py) (e.g., `from scripts.shared.api import AhaApiClient; client = AhaApiClient()`).
   - Do not manually attach authorization headers or write raw `requests` calls in individual script files.
   - `AhaApiClient` automatically attaches headers retrieved from `TokenManager` and handles standard HTTP operations (`get`, `post`, `put`, `patch`, `delete`).

## Scripts Directory Guide & Maintenance Rule

1. **Scripts Guide**:
   - Refer to [`scripts/AGENTS.md`](scripts/AGENTS.md) for the complete registry of scripts, usage examples, and argument details.
   - Slide management scripts [`scripts/read_slide.py`](scripts/read_slide.py) and [`scripts/update_slide.py`](scripts/update_slide.py) allow reading slide-level properties (`baseColour`, `textColour`, `backgroundImage`, `visibility`, `elements_count`) and updating slide properties with optional auto-resolution of presentation ID and global application (`--apply-to-all`).
   - Slide element manipulation scripts [`scripts/list_slide_elements.py`](scripts/list_slide_elements.py), [`scripts/insert_slide_element.py`](scripts/insert_slide_element.py), and [`scripts/update_slide_element.py`](scripts/update_slide_element.py) allow listing, inserting, and updating `:::text`, `:::image`, and `:::shape` directive blocks in slide v2 DSL attributes with automatic CDN image upload via [`scripts/upload_image.py`](scripts/upload_image.py).
   - Image upload tool [`scripts/upload_image.py`](scripts/upload_image.py) uploads local files or external URLs to `POST /api/upload/image/` and returns official signed AhaSlides CDN URLs (`https://assets-cdn.ahaslides.com/...`).
   - HAR exploration script [`scripts/explore_har_request.py`](scripts/explore_har_request.py) supports HTTP method matching (`POST`, `GET`, etc.), method filtering (`-m/--method`), listing requests sequentially (`-l/--list`), and payload inspection (`--json`).

2. **Mandatory Script Documentation Rule**:
   - **SYNCHRONIZATION REQUIREMENT**: Each time a script in `scripts/` is added, edited, or removed, both [`scripts/AGENTS.md`](scripts/AGENTS.md) and [`AGENTS.md`](AGENTS.md) **MUST** be updated to accurately reflect the scripts reality.
