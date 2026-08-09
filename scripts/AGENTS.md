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
  - **Purpose**: Creates a new slide of a specified type in an AhaSlides presentation.
  - **Usage**: `python3 scripts/create_slide.py <presentation_id> [type] [order] [-t TYPE] [-o ORDER] [--json]`
  - **Example**: `python3 scripts/create_slide.py 9826054 wordCloud -o 2`

- **[`scripts/delete_slide.py`](delete_slide.py)**:
  - **Purpose**: Deletes one or more slides from an AhaSlides presentation.
  - **Usage**: `python3 scripts/delete_slide.py <presentation_id> <slide_id ...> [--json]`
  - **Example**: `python3 scripts/delete_slide.py 9826054 156929519`

- **[`scripts/list_slide_types.py`](list_slide_types.py)**:
  - **Purpose**: Lists and searches available slide types from the AhaSlides Marketplace API.
  - **Usage**: `python3 scripts/list_slide_types.py [query] [-c CATEGORY] [-q QUERY] [--json]`
  - **Example**: `python3 scripts/list_slide_types.py "word cloud"`

---

### 3. HAR Analysis & Debugging Tools
- **[`scripts/parse_har_urls.py`](parse_har_urls.py)**:
  - **Purpose**: Parses and lists request URLs from HAR files, applying exclusion patterns from `configs/config.json`.
  - **Usage**: `python3 scripts/parse_har_urls.py [har_file] [-u] [-m] [-o OUTPUT] [--ignore-exclusions]`
  - **Example**: `python3 scripts/parse_har_urls.py artifacts/list.presenter.ahaslides.com.har -u -m`

- **[`scripts/explore_har_request.py`](explore_har_request.py)**:
  - **Purpose**: Explores and displays request shapes, parameters, headers (sanitizing tokens), and body payloads from HAR files.
  - **Usage**: `python3 scripts/explore_har_request.py <query> [har_file] [-n INDEX] [--json] [--include-excluded]`
  - **Example**: `python3 scripts/explore_har_request.py slide/create artifacts/create-slide.presenter.ahaslides.com.har`

- **[`scripts/check_token.py`](check_token.py)**:
  - **Purpose**: Safely checks whether the token environment variable is set without printing its value.
  - **Usage**: `python3 scripts/check_token.py`

---

### 4. Core Shared Infrastructure
- **[`scripts/token_manager.py`](token_manager.py)**:
  - **Purpose**: `TokenManager` class for safely retrieving authentication tokens.
- **[`scripts/shared/api/aha_client.py`](shared/api/aha_client.py)**:
  - **Purpose**: `AhaApiClient` shared HTTP API client wrapper.
