# Scripts Directory Guide & Maintenance Rules

## Mandatory Maintenance Rule

> [!IMPORTANT]
> **SYNCHRONIZATION RULE**: Every time a script in `scripts/` is added, modified, or removed, **`scripts/AGENTS.md` MUST be updated immediately** to reflect the exact current reality of all scripts, arguments, and usage patterns.

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
  - **Purpose**: Lists directive elements (`:::text` or `:::shape` blocks) from a slide's v2 DSL content, parsing attributes (`id`, `preset`, `at`, `width`, `offset_x`, `offset_y`, etc.) and text snippets. Supports filtering by element ID (`-e`/`--element-id`).
  - **Usage**: `python3 scripts/list_slide_elements.py <slide_id> [-e ELEMENT_ID] [--json]`
  - **Examples**:
    - `python3 scripts/list_slide_elements.py 156929519 --json`
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

---

### 4. Core Shared Infrastructure
- **[`scripts/token_manager.py`](token_manager.py)**:
  - **Purpose**: `TokenManager` class for safely retrieving authentication tokens.
- **[`scripts/shared/api/aha_client.py`](shared/api/aha_client.py)**:
  - **Purpose**: `AhaApiClient` shared HTTP API client wrapper.
