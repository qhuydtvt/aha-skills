# Scripts Directory Guide & Maintenance Rules

## Mandatory Maintenance Rule

> [!IMPORTANT]
> **SYNCHRONIZATION RULE**: Every time a script in `scripts/` is added, modified, or removed, **`scripts/AGENTS.md` MUST be updated immediately** to reflect the exact current reality of all scripts, arguments, and usage patterns.

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

---

## Shared Architecture & Security Guidelines

1. **Authentication Token Management**:
   - **MUST** use `TokenManager` in [`scripts/token_manager.py`](token_manager.py).
   - **STRICT PROHIBITION**: Authentication token values must **NEVER** be printed, logged, or exposed to `stdout`/`stderr`.

2. **HTTP API Requests**:
   - **MUST** use `AhaApiClient` from [`scripts/shared/api/aha_client.py`](shared/api/aha_client.py).
   - `AhaApiClient` handles standard headers, automatic bearer token attachment, and HTTP methods (`get`, `post`, `put`, `patch`, `delete`).

---

## Available Scripts Registry

### 1. Presentation Management Scripts
- **[`scripts/create_presentation.py`](create_presentation.py)**:
  - **Purpose**: Creates a new presentation on AhaSlides.
  - **Usage**: `python3 scripts/create_presentation.py [name]`
  - **Example**: `python3 scripts/create_presentation.py "My New Presentation"`

- **[`scripts/list_presentations.py`](list_presentations.py)**:
  - **Purpose**: Fetches and lists all user presentations in a formatted table.
  - **Usage**: `python3 scripts/list_presentations.py [-p PAGE] [-l LIMIT] [--json]`
  - **Example**: `python3 scripts/list_presentations.py --limit 10`

- **[`scripts/read_presentation.py`](read_presentation.py)**:
  - **Purpose**: Reads presentation details, slide-by-slide content, canvas blocks, and v2 DSL attributes.
  - **Usage**: `python3 scripts/read_presentation.py <presentation_id> [-s SLIDE] [--slide-id SLIDE_ID] [--meta] [--json]`
  - **Example**: `python3 scripts/read_presentation.py 9787397 --slide 1-3`

- **[`scripts/delete_presentation.py`](delete_presentation.py)**:
  - **Purpose**: Deletes one or more presentations on AhaSlides by ID.
  - **Usage**: `python3 scripts/delete_presentation.py <presentation_id ...>`
  - **Example**: `python3 scripts/delete_presentation.py 9826055`

---

### 2. Slide & Slide Type Scripts
- **[`scripts/create_slide.py`](create_slide.py)**:
  - **Purpose**: Creates a new slide of a specified type in an AhaSlides presentation. Supports appending at the end of presentation via `--at-end` / `--end` / `-e` flag.
  - **Usage**: `python3 scripts/create_slide.py <presentation_id> [type] [order] [-t TYPE] [-o ORDER] [--at-end] [--json]`
  - **Examples**:
    - `python3 scripts/create_slide.py 9826054 wordCloud -o 2`
    - `python3 scripts/create_slide.py 9826054 content-v2 --at-end`

- **[`scripts/read_slide.py`](read_slide.py)**:
  - **Purpose**: Reads slide details, properties (`id`, `type`, `order`, `baseColour`, `textColour`, `backgroundImage`, `visibility`, `elements_count`), and modifiable slide-level attributes. Auto-resolves presentation ID if omitted.
  - **Usage**: `python3 scripts/read_slide.py <slide_id> [-p PRESENTATION_ID] [--json]`
  - **Examples**:
    - `python3 scripts/read_slide.py 156934061`
    - `python3 scripts/read_slide.py 156934061 -p 9826054 --json`

- **[`scripts/update_slide.py`](update_slide.py)**:
  - **Purpose**: Updates slide-level properties (`baseColour`, `textColour`, `backgroundImage`, `visibility`) via `PATCH /api/slide/`. Supports auto-resolving presentation ID and applying changes to all slides (`--apply-to-all`).
  - **Usage**: `python3 scripts/update_slide.py <slide_id> [-p PRESENTATION_ID] [--base-color BASE_COLOR] [--text-color TEXT_COLOR] [--background-image IMAGE_URL] [--visibility VISIBILITY] [--apply-to-all] [--json]`
  - **Examples**:
    - `python3 scripts/update_slide.py 156934061 --base-color "#1e293b" --text-color "#ffffff"`
    - `python3 scripts/update_slide.py 156934061 -p 9826054 --base-color "#0f172a" --apply-to-all`

- **[`scripts/delete_slide.py`](delete_slide.py)**:
  - **Purpose**: Deletes one or more slides from an AhaSlides presentation.
  - **Usage**: `python3 scripts/delete_slide.py <presentation_id> <slide_id ...> [--json]`
  - **Example**: `python3 scripts/delete_slide.py 9826054 156929519`

- **[`scripts/list_slide_types.py`](list_slide_types.py)**:
  - **Purpose**: Lists and searches available slide types from the AhaSlides Marketplace API.
  - **Usage**: `python3 scripts/list_slide_types.py [query] [-c CATEGORY] [-q QUERY] [--json]`
  - **Example**: `python3 scripts/list_slide_types.py "word cloud"`

- **[`scripts/list_slide_elements.py`](list_slide_elements.py)**:
  - **Purpose**: Lists directive elements (`:::text`, `:::shape`, `:::image`, `:::icon`, etc.) from a slide's v2 DSL content or offline `.adsl` file, parsing attributes (`id`, `preset`, `at`, `width`, `offset_x`, `offset_y`, etc.) and text snippets. Includes `parse_adsl_to_elements(dsl_text_or_path, target_element_id=None)` to parse directive blocks offline directly without calling AhaSlides APIs. Auto-detects `.adsl` file paths for offline parsing.
  - **Usage**: `python3 scripts/list_slide_elements.py <slide_id_or_adsl_file> [-e ELEMENT_ID] [--json]`
  - **Examples**:
    - `python3 scripts/list_slide_elements.py 156929519 --json`
    - `python3 scripts/list_slide_elements.py artifacts/dsl-templates/feature_cards_4col_9840079_157066192.adsl`
    - `python3 scripts/list_slide_elements.py 156929519 -e A5kqSFkqgR`

- **[`scripts/insert_slide_element.py`](insert_slide_element.py)**:
  - **Purpose**: Inserts a new directive element (`:::text` block) into a slide's v2 DSL content with optional preset positioning, custom styling, or raw DSL.
  - **Usage**: `python3 scripts/insert_slide_element.py <slide_id> [text] [-p PRESET] [--at AT] [-w WIDTH] [-x OFFSET_X] [-y OFFSET_Y] [--color COLOR] [--bg BG] [-r RADIUS] [--padding PADDING] [--raw-dsl RAW_DSL] [--json]`
  - **Examples**:
    - `python3 scripts/insert_slide_element.py 156929519 "Hello World" -p title`
    - `python3 scripts/insert_slide_element.py 156929519 "Custom Body Text" -p body -x 0 -y 20 --color "#ffffff"`

- **[`scripts/update_slide_element.py`](update_slide_element.py)**:
  - **Purpose**: Updates an existing directive element (`:::text`, `:::image`, or `:::shape` block) in a slide's v2 DSL content by modifying header attributes (`x`, `y`, `w`, `h`, `at`, `width`, `offset_x`, `offset_y`, `color`, `background`, `border_radius`, `padding`, `src`, `extra_attrs`) and/or body text content. Auto-uploads external or local images to AhaSlides CDN if needed.
  - **Usage**: `python3 scripts/update_slide_element.py <slide_id> <element_id> [-t TEXT] [--x X] [--y Y] [--w W] [--h H] [--at AT] [-w WIDTH] [-x OFFSET_X] [-y OFFSET_Y] [--color COLOR] [--bg BG] [-r RADIUS] [--padding PADDING] [--src SRC] [--extra-attrs EXTRA_ATTRS] [--json]`
  - **Examples**:
    - `python3 scripts/update_slide_element.py 156929519 elem123456 -t "Updated Title" --color "#ff0000"`
    - `python3 scripts/update_slide_element.py 156929519 elem123456 --src "https://images.unsplash.com/photo-bg.jpg"`

- **[`scripts/lint_slide.py`](lint_slide.py)**:
  - **Purpose**: Lints a live slide or offline `.adsl` file (`python3 scripts/lint_slide.py artifacts/dsl-dumps/temp_file.adsl` or `--file path/to/file.adsl`). Supports cheap offline pre-flight validation of `.adsl` files before applying to live slides (with live slide verification `--live` or numeric `slide_id` demoted to final verification). Performs **Content Length & Density Validation** (single element line count <= 8 lines, single element character length <= 350 chars, total slide character count <= 750 chars, total bullet points / list items <= 8 items with recommendation to split slide when limits are exceeded), element bounding box calculation, layout overlap detection (with spatial container shape suppression), canvas overflow checking (1280x720 canvas), raw DSL syntax leak auditing, and WCAG 2.1 color contrast evaluation (AA/AAA) with theme color alias resolution (`text`, `muted`, `surface`, `bg`).
  - **Usage**: `python3 scripts/lint_slide.py [target] [-f FILE_PATH] [--live] [--contrast-level AA|AAA] [--strict-contrast]`
  - **Examples**:
    - `python3 scripts/lint_slide.py artifacts/dsl-dumps/temp_fixed_slide4.adsl` (cheap offline pre-flight validation)
    - `python3 scripts/lint_slide.py --file artifacts/dsl-templates/feature_cards_4col_9840079_157066192.adsl`
    - `python3 scripts/lint_slide.py 156929519 --live` (final live verification)

- **[`scripts/scaffold_slides_content.py`](scaffold_slides_content.py)**:
  - **Purpose**: Scaffolds and generates the vendor-independent `slides_content.json` specification file from source material (e.g. `artifacts/inputs/manual_of_me.md` or a slide plan).
  - **Usage**: `python3 scripts/scaffold_slides_content.py <input_file> [-o OUTPUT_JSON_PATH]`
  - **Examples**:
    - `python3 scripts/scaffold_slides_content.py artifacts/inputs/manual_of_me.md`
    - `python3 scripts/scaffold_slides_content.py artifacts/inputs/manual_of_me.md -o artifacts/slide-plans/manual_of_me/slides_content.json`

- **[`scripts/lint_slide_content.py`](lint_slide_content.py)**:
  - **Purpose**: Lints and validates a vendor-independent `slides_content.json` specification file itself. Verifies JSON pretty-print & formatting uniformity (2-space indentation with a trailing newline), root schema, vendor independence (zero platform-specific internal keys), slide schema & field key order uniformity (`slide_number`, `slide_id_key`, `title`, `subtitle` (if present), `slide_type`, `required_keywords`, `key_content`, `expected_elements_count`), value whitespace & type uniformity (no un-trimmed string values), sequential slide numbering, unique `slide_id_key`s, non-empty titles/keywords, and valid `expected_elements_count` bounds (`min > 0`, `max >= min`). Returns exit code 0 on PASS, 1 on FAIL.
  - **Usage**: `python3 scripts/lint_slide_content.py <json_path> [--json]`
  - **Examples**:
    - `python3 scripts/lint_slide_content.py artifacts/slide-plans/manual_of_me/slides_content.json`
    - `python3 scripts/lint_slide_content.py artifacts/slide-plans/manual_of_me/slides_content.json --json`

- **[`scripts/verify_presentation_content.py`](verify_presentation_content.py)**:
  - **Purpose**: Verifies live AhaSlides presentation content against a vendor-independent `slides_content.json` specification file slide-by-slide. Checks slide count matching, slide title matching, all `required_keywords` presence, `expected_elements_count` bounds (`min`..`max`), and `key_content` completeness. Outputs a clean colorized report or JSON payload (`--json`). Returns exit code 0 on PASS, 1 on FAIL.
  - **Usage**: `python3 scripts/verify_presentation_content.py <presentation_id> [json_spec_path] [--json]`
  - **Examples**:
    - `python3 scripts/verify_presentation_content.py 9828288 artifacts/slide-plans/manual_of_me/slides_content.json`
    - `python3 scripts/verify_presentation_content.py 9828288 artifacts/slide-plans/manual_of_me/slides_content.json --json`

- **[`scripts/list_slide_layouts.py`](list_slide_layouts.py)**:
  - **Purpose**: Lists pre-built v2 DSL layout presets (`content-v2`) and fetches/browses the full freestyle-v2 public templates library (128 layouts) grouped by category (Fun, Work, School, Holidays, …). Supports DSL inspection from live presentations and fetching raw canvas-blocks DSL from any freestyle-v2 template via its `canvasBlocksUrl`. Includes alias-aware `--type` filtering (`freestyle-v2` ↔ `freestyle`) and `--limit` to cap output.
  - **Usage**: `python3 scripts/list_slide_layouts.py [--all] [--categories] [-c CATEGORY] [-t TYPE] [--sub-categories] [--fetch-dsl TEMPLATE_ID] [-n LIMIT] [-p PRESENTATION_ID] [-l LAYOUT_KEY] [--json]`
  - **Flags**:
    - `--all` / `-a`: Fetch all layout templates (128 freestyle-v2 + 8 built-in content-v2 + marketplace interactive)
    - `--sub-categories`: Grouped view — content-v2 items listed individually; large types (e.g. freestyle-v2) show compact category previews; add `--all` to expand everything
    - `--fetch-dsl TEMPLATE_ID`: Download and print raw DSL from a freestyle-v2 public template's `canvasBlocksUrl`
    - `--type` / `-t TYPE`: Filter by slide type; `freestyle-v2` and `freestyle` are treated as aliases
    - `--limit` / `-n N`: Cap list output to N items
    - `--categories`: Dynamically list all unique categories with counts
    - `-c CATEGORY`: Filter by category substring (e.g. `Fun`, `Work`, `Content`)
    - `-p PRESENTATION_ID`: Extract layout DSLs from a live presentation
    - `-l LAYOUT_KEY`: Inspect a specific built-in preset and print its DSL template
  - **Examples**:
    - `python3 scripts/list_slide_layouts.py` — lists built-in content-v2 presets
    - `python3 scripts/list_slide_layouts.py --sub-categories` — grouped view with compact freestyle-v2 category previews
    - `python3 scripts/list_slide_layouts.py --all --sub-categories` — full grouped view with every item listed
    - `python3 scripts/list_slide_layouts.py --categories` — dynamically extracts and lists all layout categories from the API
    - `python3 scripts/list_slide_layouts.py --all` — fetches all layout templates from AhaSlides API
    - `python3 scripts/list_slide_layouts.py --type content-v2` — filters to built-in content-v2 presets
    - `python3 scripts/list_slide_layouts.py --type freestyle-v2 --limit 20` — first 20 freestyle-v2 templates
    - `python3 scripts/list_slide_layouts.py --fetch-dsl 12345` — fetch raw DSL for freestyle-v2 template #12345
    - `python3 scripts/list_slide_layouts.py -p 9828288` — extracts layout DSLs from live presentation

- **[`scripts/apply_slide_layout.py`](apply_slide_layout.py)**:
  - **Purpose**: Applies vendor-independent layout presets or layout DSL templates to live slides on AhaSlides. Supports 4 layout sources (built-in preset `-l`, live slide `-s`, public template ID `-t`, local DSL file `-f`), automatic element ID scoping using target slide order or custom prefix, placeholder content mapping (`-m KEY=VALUE`), content preservation from existing target slides (`--preserve-content`), dry-run preview (`--dry-run`), and post-update visual linting (`--lint`).
  - **Usage**: `python3 scripts/apply_slide_layout.py <slide_id> [-l LAYOUT_KEY] [-s SOURCE_SLIDE_ID] [-t TEMPLATE_ID] [-f DSL_FILE] [-m KEY=VALUE ...] [--preserve-content] [--prefix PREFIX] [--keep-orig-ids] [--lint] [--force] [--dry-run] [--json]`
  - **Examples**:
    - `python3 scripts/apply_slide_layout.py 157015776 -l intro_caption_hero --dry-run`
    - `python3 scripts/apply_slide_layout.py 157015776 -l intro_caption_hero --preserve-content -m caption_text="01 · HISTORY" --lint`
    - `python3 scripts/apply_slide_layout.py 157015776 -s 156934061 --prefix custom_ --dry-run`
    - `python3 scripts/apply_slide_layout.py 157015776 -f templates/custom.dsl -m title_text="New Title" --json`

- **[`scripts/manage_slide_template.py`](manage_slide_template.py)**:
  - **Purpose**: Manages freestyle-v2 public slide templates and custom DSL templates. Supports browsing public templates (`list`), listing categories (`categories`), inspecting single templates (`get`), substring search (`search`), exporting canvas blocks (`export`), applying templates (`apply`), applying background images (`stamp`), creating new slides from templates (`create-from-template`), saving live slide DSL templates to `artifacts/dsl-templates/` (`save-from-slide`), saving all presentation slides as DSL templates (`save-from-presentation` / `dump-presentation`) using title-aware default filename pattern `{title}_{presentation_id}_{slide_id}.adsl`, and linting ADSL metadata header comments & filename consistency (`lint-templates` / `lint`).
  - **Usage**: `python3 scripts/manage_slide_template.py <verb> [args] [--json]`
  - **Examples**:
    - `python3 scripts/manage_slide_template.py list --category Fun --limit 10`
    - `python3 scripts/manage_slide_template.py get 135119967 --canvas-blocks`
    - `python3 scripts/manage_slide_template.py export 135119967 -o artifacts/dsl-templates/template_135119967.json`
    - `python3 scripts/manage_slide_template.py apply 135119967 --slide 157058435`
    - `python3 scripts/manage_slide_template.py stamp 135119967 --slide 157058435`
    - `python3 scripts/manage_slide_template.py create-from-template 135119967 --presentation 9840079`
    - `python3 scripts/manage_slide_template.py save-from-slide 157060425 --name slide9_cover.adsl`
    - `python3 scripts/manage_slide_template.py save-from-presentation 9840079 --slides 1-3 --dry-run`
    - `python3 scripts/manage_slide_template.py lint-templates`

- **[`scripts/annotate_adsl_metadata.py`](annotate_adsl_metadata.py)**:
  - **Purpose**: Bakes or updates structured header metadata comments (`# @presentation_id`, `# @slide_id`, `# @purpose`, `# @category`, `# @description`, `# @keywords`) into `.adsl` files in `artifacts/dsl-templates/` or a specified directory/file. Extracts presentation ID, slide ID, and purpose from filename patterns or explicit CLI parameters (`--purpose`, `--category`, `--description`, `--keywords`), and supports non-mutating metadata linting via `--lint`.
  - **Usage**: `python3 scripts/annotate_adsl_metadata.py [--dir DIR] [--file FILE] [-p PRES_ID] [-s SLIDE_ID] [--purpose PURPOSE] [--category CATEGORY] [--description DESC] [--keywords KW] [--lint] [--dry-run] [--json]`
  - **Examples**:
    - `python3 scripts/annotate_adsl_metadata.py`
    - `python3 scripts/annotate_adsl_metadata.py --dir artifacts/dsl-templates/`
    - `python3 scripts/annotate_adsl_metadata.py --file artifacts/dsl-templates/pricing_table_3tier_9840079_157065856.adsl`
    - `python3 scripts/annotate_adsl_metadata.py --lint`
    - `python3 scripts/annotate_adsl_metadata.py --dry-run`

- **[`scripts/dump_slide_dsl.py`](dump_slide_dsl.py)**:
  - **Purpose**: Dumps the raw `.adsl` (AhaSlides Domain-Specific Language) format of a slide's content to a local file in `artifacts/dsl-dumps/` by default (`artifacts/dsl-dumps/{slide_id}.adsl`).
  - **Usage**: `python3 scripts/dump_slide_dsl.py <slide_id> [-o OUTPUT]`
  - **Examples**:
    - `python3 scripts/dump_slide_dsl.py 157015776` (saves to `artifacts/dsl-dumps/157015776.adsl`)
    - `python3 scripts/dump_slide_dsl.py 157015776 -o artifacts/dsl-templates/my_layout.adsl`

- **[`scripts/apply_slide_dsl.py`](apply_slide_dsl.py)**:
  - **Purpose**: Applies a raw `.adsl` file (typically from `artifacts/dsl-templates/`) directly to a slide's DSL attribute.
  - **Usage**: `python3 scripts/apply_slide_dsl.py <slide_id> <file>`
  - **Example**: `python3 scripts/apply_slide_dsl.py 157015776 artifacts/dsl-templates/157015776.adsl`

- **[`scripts/upload_image.py`](upload_image.py)**:
  - **Purpose**: Uploads a local image file or HTTP/HTTPS image URL to AhaSlides CDN via `POST /api/upload/image/` and returns the official signed CDN URL (`https://assets-cdn.ahaslides.com/...`).
  - **Usage**: `python3 scripts/upload_image.py <image_source> [-a ACCESS_CODE] [--json]`
  - **Example**: `python3 scripts/upload_image.py "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80"`

---

### 3. HAR Analysis & Debugging Tools
- **[`scripts/parse_har_urls.py`](parse_har_urls.py)**:
  - **Purpose**: Parses and lists request URLs from HAR files, applying exclusion patterns from `configs/config.json`.
  - **Usage**: `python3 scripts/parse_har_urls.py [har_file] [-u] [-m] [-o OUTPUT] [--ignore-exclusions]`
  - **Example**: `python3 scripts/parse_har_urls.py artifacts/list.presenter.ahaslides.com.har -u -m`

- **[`scripts/explore_har_request.py`](explore_har_request.py)**:
  - **Purpose**: Explores and displays request shapes, parameters, headers (sanitizing tokens), and body payloads from HAR files safely. Supports querying by HTTP method or URL substring, filtering by method, and listing all requests with index numbers.
  - **Usage**: `python3 scripts/explore_har_request.py [query] [har_file] [-m METHOD] [-l] [-n INDEX] [--json] [--include-excluded]`
  - **Examples**:
    - `python3 scripts/explore_har_request.py POST artifacts/insert-slide-element.presenter.ahaslides.com.har --json`
    - `python3 scripts/explore_har_request.py artifacts/insert-slide-element.presenter.ahaslides.com.har -m POST -l`
    - `python3 scripts/explore_har_request.py slide/create artifacts/create-slide.presenter.ahaslides.com.har`

- **[`scripts/check_token.py`](check_token.py)**:
  - **Purpose**: Safely checks whether the token environment variable is set without printing its value.
  - **Usage**: `python3 scripts/check_token.py`

- **[`scripts/watch_presentation.py`](watch_presentation.py)**:
  - **Purpose**: Live-watches an AhaSlides presentation for any state changes (slide DSL elements, slide properties, slide additions/removals), printing coloured unified diffs in real-time. Primary dev tool for reverse-engineering new element types — run it, make a change in the UI, read the exact DSL diff.
  - **Usage**: `python3 scripts/watch_presentation.py <presentation_id> [-s SLIDE_IDS] [-i INTERVAL]`
  - **Flags**:
    - `-s / --slides`: Comma-separated slide IDs to watch (default: all slides)
    - `-i / --interval`: Poll interval in seconds (default: 2)
    - **Stop**: `Ctrl+C` — exits cleanly.
  - **Examples**:
    - `python3 scripts/watch_presentation.py 9826054` — watch all slides
    - `python3 scripts/watch_presentation.py 9826054 -s 156938195,156938333` — watch specific slides
    - `python3 scripts/watch_presentation.py 9826054 -i 1` — poll every second

---

### 4. Shared Libraries
- **[`scripts/token_manager.py`](token_manager.py)**:
  - **Purpose**: `TokenManager` class for safely retrieving authentication tokens.
- **[`scripts/shared/api/aha_client.py`](shared/api/aha_client.py)**:
  - **Purpose**: `AhaApiClient` shared HTTP API client wrapper.
- **[`scripts/shared/lib/adsl_metadata.py`](shared/lib/adsl_metadata.py)**:
  - **Purpose**: `embed_adsl_metadata`, `parse_adsl_metadata`, `format_adsl_filename`, `parse_adsl_filename`, `lint_adsl_metadata`, and `lint_adsl_file` helper functions for embedding/parsing structured metadata header comments (`# @presentation_id`, `# @slide_id`, `# @purpose`, `# @category`, `# @description`, `# @keywords`), template filename parsing, and template metadata linting.
- **[`scripts/shared/lib/contrast.py`](shared/lib/contrast.py)**:
  - **Purpose**: `parse_color`, `blend_colors`, `relative_luminance`, `contrast_ratio`, and `evaluate_contrast` functions for WCAG 2.1 color contrast calculation and evaluation.

