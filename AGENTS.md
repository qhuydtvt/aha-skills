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
   - Slide element manipulation scripts [`scripts/list_slide_elements.py`](scripts/list_slide_elements.py), [`scripts/insert_slide_element.py`](scripts/insert_slide_element.py), and [`scripts/update_slide_element.py`](scripts/update_slide_element.py) allow listing, inserting, and updating `:::text`, `:::image`, `:::shape`, and `:::icon` directive blocks in slide v2 DSL attributes with automatic CDN image upload via [`scripts/upload_image.py`](scripts/upload_image.py). Includes `parse_adsl_to_elements` for offline `.adsl` file parsing directly without calling AhaSlides APIs.
   - Slide content scaffolding script [`scripts/scaffold_slides_content.py`](scripts/scaffold_slides_content.py) scaffolds and generates the vendor-independent `slides_content.json` specification file from source material (e.g. `artifacts/inputs/manual_of_me.md` or a slide plan).
   - Slide content linter script [`scripts/lint_slide_content.py`](scripts/lint_slide_content.py) lints and validates the `slides_content.json` specification file itself (checking JSON pretty-print & formatting uniformity with 2-space indentation and single trailing newline, root schema, vendor independence verification with zero platform-specific internal keys, slide schema & field key order uniformity, value whitespace & type uniformity, sequential slide numbering, unique `slide_id_key`s, and non-empty titles (if present)/keywords).
   - Live presentation verification script [`scripts/verify_presentation_content.py`](scripts/verify_presentation_content.py) verifies live presentation content against vendor-independent `slides_content.json` slide-by-slide (checking total slide count matching, slide title matching (if title present), required keywords presence, and key content completeness).
   - Slide layout inspector script [`scripts/list_slide_layouts.py`](scripts/list_slide_layouts.py) lists built-in v2 DSL layout presets (`content-v2`) and fetches/browses the full freestyle-v2 public templates library (128 layouts) grouped by category. Supports alias-aware `--type` filtering (`freestyle-v2` ↔ `freestyle`), `--fetch-dsl TEMPLATE_ID` to download raw canvas-blocks DSL from any freestyle-v2 template, `--limit N` to cap list output, and compact `--sub-categories` grouping (add `--all` to expand every item).
   - Slide layout application script [`scripts/apply_slide_layout.py`](scripts/apply_slide_layout.py) applies vendor-independent layout presets or layout DSL templates to live slides with layout source resolution (`-l`, `-s`, `-t`, `-f`), element ID scoping (`--prefix` or auto slide order), placeholder mapping (`-m`), content preservation (`--preserve-content`), dry-run preview (`--dry-run`), and post-update visual linting (`--lint`).
   - Slide template manager [`scripts/manage_slide_template.py`](scripts/manage_slide_template.py) handles lifecycle operations for public templates and custom DSL templates stored in `artifacts/dsl-templates/`, including creation/saving from active slides (`save-from-slide`) or presentations (`save-from-presentation` / `dump-presentation`) with title-aware default filename pattern `{title}_{presentation_id}_{slide_id}.adsl`, public catalog browsing, template application, export, background stamping, and template metadata linting (`lint-templates` / `lint`).
   - ADSL metadata annotation script [`scripts/annotate_adsl_metadata.py`](scripts/annotate_adsl_metadata.py) bakes structured header metadata comments (`# @presentation_id`, `# @slide_id`, `# @purpose`, `# @category`, `# @description`, `# @keywords`) into `.adsl` files in `artifacts/dsl-templates/` or specified single files/directories with `--dir`, `--file`, `--purpose`, `--category`, `--description`, `--keywords`, `--lint`, `--dry-run`, and `--json`.
   - Shared ADSL metadata library [`scripts/shared/lib/adsl_metadata.py`](scripts/shared/lib/adsl_metadata.py) provides helper functions for embedding/parsing structured ADSL header metadata comments (`embed_adsl_metadata`, `parse_adsl_metadata`), formatting/parsing ADSL template filenames (`format_adsl_filename`, `parse_adsl_filename`), and linting template metadata (`lint_adsl_metadata`, `lint_adsl_file`).
   - Slide linter script [`scripts/lint_slide.py`](scripts/lint_slide.py) supports cheap offline pre-flight validation of `.adsl` files before applying to live slides (`python3 scripts/lint_slide.py artifacts/dsl-dumps/temp_file.adsl` or `--file path/to/file.adsl`), with live slide verification (`--live` or numeric `slide_id`) demoted to final verification. Enforces **Content Length & Density Validation** (alert if single element > 8 lines or > 350 chars, or total slide > 750 chars or > 8 bullet points with split-slide recommendation), element bounding boxes, layout overlaps (with spatial container shape enclosure filtering), canvas overflows (1280x720 canvas), raw DSL syntax leaks, and WCAG 2.1 color contrast (AA/AAA) using `scripts/shared/lib/contrast.py`.
   - Shared contrast library [`scripts/shared/lib/contrast.py`](scripts/shared/lib/contrast.py) provides WCAG 2.1 contrast evaluation, relative luminance, alpha composite blending, and CSS color parsing.

   - Image upload tool [`scripts/upload_image.py`](scripts/upload_image.py) uploads local files or external URLs to `POST /api/upload/image/` and returns official signed AhaSlides CDN URLs (`https://assets-cdn.ahaslides.com/...`).
   - HAR exploration script [`scripts/explore_har_request.py`](scripts/explore_har_request.py) supports HTTP method matching (`POST`, `GET`, etc.), method filtering (`-m/--method`), listing requests sequentially (`-l/--list`), and payload inspection (`--json`).
   - Live presentation watcher [`scripts/watch_presentation.py`](scripts/watch_presentation.py) polls all slide DSLs and slide properties in real-time, printing coloured unified diffs on any change. Primary dev utility for reverse-engineering new element types without HAR recording — run it, interact with the UI, read the diff.

2. **Mandatory Script Documentation Rule**:
   - **SYNCHRONIZATION REQUIREMENT**: Each time a script in `scripts/` is added, edited, or removed, both [`scripts/AGENTS.md`](scripts/AGENTS.md) and [`AGENTS.md`](AGENTS.md) **MUST** be updated to accurately reflect the scripts reality.

## Slide Layout Workflow

1. **Recommended DSL Approach (`.adsl`)**:
   - The primary and most efficient method to apply complex layouts with customized content to a slide is to use atomic DSL manipulation.
   - Use `python3 scripts/dump_slide_dsl.py <slide_id>` to export an existing layout to an `.adsl` (AhaSlides DSL) file stored in `artifacts/dsl-dumps/` (e.g. `artifacts/dsl-dumps/<slide_id>.adsl`).
   - Modify the `.adsl` file's `:::text`, `:::image`, etc., blocks manually or programmatically.
   - Use `python3 scripts/apply_slide_dsl.py <slide_id> <file.adsl>` (e.g. `artifacts/dsl-dumps/<file.adsl>` or `artifacts/dsl-templates/<file.adsl>`) to apply the complete layout back, cleanly resolving content positioning and styles in one atomic request.
   - **Inline Annotations & Documentation**: Future agents **MUST** annotate slide DSL files (`.adsl`) directly using inline `#` comments for any developer notes or documentation, without needing to maintain separate records or workflow files of any kind.

2. **Native Vector Icons (`:::icon`)**:
   - Native vector icons can be used in slide DSLs via the `:::icon` directive with the `name` attribute (using standard Lucide icon names, e.g., `name="check"`).
   - **Recommended Approach**: Using the native `:::icon` directive is the recommended approach for adding or updating icons to slides. Unlike uploading custom raster images (e.g., via `scripts/upload_image.py`), native vector icons maintain high resolution, support vector scaling, and allow direct CSS/DSL color control (e.g., using a custom `color` attribute) directly within the DSL.

3. **Metadata-Driven Template Discovery & Selection**:
   - **DO NOT rely solely on filenames** when selecting templates from `artifacts/dsl-templates/`. While filenames (e.g., `hero_header_minimal_cover_9840079_157080836.adsl`) provide high-level intent, full template selection MUST leverage the structured header metadata embedded inside `.adsl` files.
   - **Header Metadata Structure**: Header comments `# @purpose`, `# @category`, `# @description`, and `# @keywords` provide rich structural intent definitions.
   - **Querying & Browsing**: Use `scripts/shared/lib/adsl_metadata.py` (`parse_adsl_metadata(file_path)`), `python3 scripts/annotate_adsl_metadata.py --dir artifacts/dsl-templates --json`, or `python3 scripts/manage_slide_template.py list-templates` to programmatically search and filter templates by category, purpose, and keyword tags (e.g. `cover`, `hero`, `cards`, `grid`, `matrix`, `comparison`).
   - **Search Methodology**: Match target content requirements against template metadata fields (`# @purpose`, `# @category`, `# @keywords`) to find optimal structural matches rather than guessing based on file basenames alone.

4. **Slide 1 Cover Initialization Rule**:
   - Creating a new presentation via `create_presentation.py` initializes Slide 1 as a default interactive slide type (e.g. `imageChoice`).
   - To make Slide 1 a `content-v2` Cover slide, agents **MUST** delete the default non-`content-v2` Slide 1 (`python3 scripts/delete_slide.py <pres_id> <default_slide1_id>`) and create a new `content-v2` slide at order 1 (`python3 scripts/create_slide.py <pres_id> content-v2 1`) before applying the cover ADSL layout.


