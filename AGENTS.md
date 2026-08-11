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
   - Slide content scaffolding script [`scripts/scaffold_slides_content.py`](scripts/scaffold_slides_content.py) scaffolds and generates the vendor-independent `slides_content.json` specification file from source material (e.g. `artifacts/inputs/manual_of_me.md` or a slide plan).
   - Slide content linter script [`scripts/lint_slide_content.py`](scripts/lint_slide_content.py) lints and validates the `slides_content.json` specification file itself (checking JSON pretty-print & formatting uniformity with 2-space indentation and single trailing newline, root schema, vendor independence verification with zero platform-specific internal keys, slide schema & field key order uniformity, value whitespace & type uniformity, sequential slide numbering, unique `slide_id_key`s, non-empty titles/keywords, and valid `expected_elements_count` bounds).
   - Live presentation verification script [`scripts/verify_presentation_content.py`](scripts/verify_presentation_content.py) verifies live presentation content against vendor-independent `slides_content.json` slide-by-slide (checking total slide count matching, slide title matching, required keywords presence, element count boundaries, and key content completeness).
   - Slide layout inspector script [`scripts/list_slide_layouts.py`](scripts/list_slide_layouts.py) lists built-in v2 DSL layout presets and extracts layout DSL templates directly from any live presentation ID. It supports filtering by type (`--type`) and displaying unified sub-categories (`--sub-categories`).
   - Slide layout application script [`scripts/apply_slide_layout.py`](scripts/apply_slide_layout.py) applies vendor-independent layout presets or layout DSL templates to live slides with layout source resolution (`-l`, `-s`, `-t`, `-f`), element ID scoping (`--prefix` or auto slide order), placeholder mapping (`-m`), content preservation (`--preserve-content`), dry-run preview (`--dry-run`), and post-update visual linting (`--lint`).
   - Slide linter script [`scripts/lint_slide.py`](scripts/lint_slide.py) calculates element bounding boxes, detects overlaps, checks for canvas overflows (elements bleeding off 1280x720 canvas), audits raw DSL text for malformed directive boundaries (`::::::text`) or leaked syntax, and evaluates WCAG 2.1 color contrast (AA/AAA) between text and container/canvas background using `scripts/shared/lib/contrast.py`.
   - Shared contrast library [`scripts/shared/lib/contrast.py`](scripts/shared/lib/contrast.py) provides WCAG 2.1 contrast evaluation, relative luminance, alpha composite blending, and CSS color parsing.

   - Image upload tool [`scripts/upload_image.py`](scripts/upload_image.py) uploads local files or external URLs to `POST /api/upload/image/` and returns official signed AhaSlides CDN URLs (`https://assets-cdn.ahaslides.com/...`).
   - HAR exploration script [`scripts/explore_har_request.py`](scripts/explore_har_request.py) supports HTTP method matching (`POST`, `GET`, etc.), method filtering (`-m/--method`), listing requests sequentially (`-l/--list`), and payload inspection (`--json`).
   - Live presentation watcher [`scripts/watch_presentation.py`](scripts/watch_presentation.py) polls all slide DSLs and slide properties in real-time, printing coloured unified diffs on any change. Primary dev utility for reverse-engineering new element types without HAR recording — run it, interact with the UI, read the diff.

2. **Mandatory Script Documentation Rule**:
   - **SYNCHRONIZATION REQUIREMENT**: Each time a script in `scripts/` is added, edited, or removed, both [`scripts/AGENTS.md`](scripts/AGENTS.md) and [`AGENTS.md`](AGENTS.md) **MUST** be updated to accurately reflect the scripts reality.

## Workflow Documentation Rule

1. **Mandatory Workflow Recording**:
   - **WORKFLOW RECORD REQUIREMENT**: Upon finishing a slide creation workflow (from source material to slide planning, fixture creation, live presentation creation, and linting verification), agents **MUST** record the whole end-to-end process in `workflows/<name>/<workflow-name>.md`.
   - The workflow document must record the input source reference, step-by-step agent and script execution log, presentation details (ID, Access Code, Presenter URL), slide mapping verification table, and linting audit results.

