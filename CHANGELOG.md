# Changelog

All notable changes to FuseSell Local will be documented in this file.

# [1.3.21] - 2025-12-15

### Changed
- Agent context lists are capped (5 items with “… more”), active products show names only, and recent activity replaces product-only changes.
- Product readiness now depends on linked team products (`gs_team_product`), matching workspace settings completion.
- Auto-interaction section now shows the sending email/tool when configured.
- Removed the agent editable section from agent.md outputs to keep files concise.

# [1.3.20] - 2025-12-15

### Changed
- Agent context markdown now mirrors the original RealtimeX flow layout (workspace/team identity, active/inactive products with recent changes, settings sections, readiness summary, quick reference) while staying text-only.
- Readiness calculation uses required settings (org profile, reps, product catalog, automation) even when teams are absent, so no-team flows still render meaningful context.

# [1.3.19] - 2025-12-15

### Fixed
- Agent context generation no longer bails out when no team is present (single-team/no-team flows); falls back to workspace/org metadata while still rendering product catalog and stats.
- Team names now read from the correct `name` column, preventing blank team titles in agent.md.

# [1.3.13] - 2025-12-15

### Fixed
- Agent context generation now includes all products (not just active), so product sections render correctly in agent.md even when products are not marked active.

# [1.3.14] - 2025-12-15

### Fixed
- Agent context uses `search_products(..., status="all")` to avoid filtering to active-only products inside `generate_agent_context`, ensuring product listings render even when status is not set to active.

# [1.3.15] - 2025-12-15

### Fixed
- Agent context writer now resolves `workspace_slug` from flow variables when provided and tolerates toolkit lookup failures, preventing agent.md from writing to the wrong path for non-default workspaces.

# [1.3.16] - 2025-12-15

### Changed
- Refined `agent_context` markdown output to include richer sections (summary, product catalog with totals, active processes with counts, settings completion, team settings snapshot, statistics) to better mirror the original RealtimeX flow structure.

# [1.3.17] - 2025-12-15

### Changed
- Simplified agent.md rendering to a condensed, text-first layout (no JSON dumps), mirroring the original RealtimeX flow structure while retaining product/process counts and settings completion summaries.

# [1.3.18] - 2025-12-15

### Fixed
- Agent context now includes workspace/team identity (workspace slug, org_id, team id/name/created), active/inactive product counts, and uses concise sections matching the original RealtimeX layout. Ensures injected metadata from the writer is preserved in the rendered output.

# [1.3.12] - 2025-12-15

### Added
- Added `fusesell_local.utils.agent_context` with `notify_action_completed` and `write_agent_md` so downstream flows can refresh agent context without importing local scripts; functions gracefully fall back when `realtimex_toolkit` is unavailable.

# [1.3.10] - 2025-12-11

### Added
- Introduced a shared `write_full_output_html` helper in `fusesell_local.utils` so flows can render consistent HTML output and raw JSON without duplicating fallback implementations. The helper is exported via `fusesell_local.utils` for downstream reuse.

# [1.3.3] - 2025-10-25

### Changed
- Added a shared `normalize_llm_base_url` helper so every entry point (CLI, programmatic API, birthday scheduler, etc.) consistently appends `/v1` to OpenAI-style endpoints while leaving Azure deployment URLs untouched.
- Exported the helper for downstream consumers, enabling RealTimeX flows to import the canonical logic instead of maintaining their own copy.

### Fixed
- Resolved repeated `APIConnectionError` retries when custom LLM base URLs were missing `/v1`, restoring successful chat completion calls across all pipeline stages.
- Added regression coverage to ensure Azure endpoints remain unchanged while standard endpoints are normalized, guarding against future regressions.

# [1.3.2] - 2025-10-24

### Changed
- Removed the deterministic fallback template so every initial-outreach draft now originates from the LLM path; when the model call fails the stage reports an error instead of emitting canned copy.

### Fixed
- Normalized draft persistence so only HTML content is stored; duplicate plain-text rows are no longer generated when the prompt pipeline encounters failures.

# [1.3.1] - 2025-10-24

### Changed
- Fallback draft generation now produces approach-specific HTML emails, ensuring usable output even when the LLM call fails.
- Deterministic template emails and mock drafts reuse the resolved recipient data and signatures so every record stays HTML-compliant.

### Fixed
- Normalized draft creation to wrap plain-text results in <html><body> and removed duplicate drafts that previously occurred when the template path was used.

# [1.3.0] - 2025-10-24

### Added
- Bundled prompt seeding now copies packaged defaults into fusesell_data/config automatically, guaranteeing the initial outreach stage always finds the shipped templates on first run.

### Changed
- Updated the default initial-outreach and follow-up prompts to require fully wrapped <html><body> content, enforce first-name greetings, and eliminate placeholder signatures so LLM drafts arrive production-ready.
- Sanitization logic normalizes generated emails into HTML (including fallback/mock drafts), injects recipient metadata, and reuses the calculated first name across prompt, rewrite, and reminder flows.
- Reminder scheduling now records Unix timestamps (cron_ts) for every new entry, simplifying downstream polling in RealTimeX orchestration.

### Fixed
- Draft generation once again prioritises the LLM prompt path; fallback templates only trigger when the prompt fails to load, preventing duplicate plain-text emails.
- Rewrites, dry-run mocks, and fallback drafts no longer emit duplicate greetings or unresolved [Your ...] placeholders, and they retain HTML formatting for downstream mailers.

# [1.2.9] - 2025-10-24

### Changed
- Primary sales rep metadata from gs_team_rep now flows into draft prompts, reminders, and signatures so outreach reflects the configured sender.
- Reminder scheduling stores the Unix timestamp (cron_ts) alongside the ISO string for easier downstream filtering.
- Greeting sanitizer standardises the first paragraph and removes duplicate salutations while keeping HTML formatting intact.

### Fixed
- Removed [Your ...] placeholder leftovers inside LLM responses and ensured drafts remain valid HTML even when the model mixes plain text and bullet lists.
- Reminder creation no longer fails when the data acquisition stage supplies the email address, and follow-up reminders inherit the same customer metadata.

# [1.2.8] - 2025-10-24

### Changed
- Initial outreach resolves the primary sales rep from `gs_team_rep` and injects their identity into prompts, reminders, and draft metadata so outreach reflects real team settings.

### Fixed
- Sanitizes generated email bodies to replace or remove `[Your …]` placeholders, ensuring signatures contain actual values even when optional rep fields are missing.
- Reminder scheduling now preserves merged contact emails so follow-up records always carry `customer_email` for downstream automations.

# [1.2.7] - 2025-10-24

### Changed
- RealTimeX sales-process normalization now forwards `recipient_address`, `recipient_name`, and `customer_email` into the FuseSell pipeline so prompt generation and scheduling have complete context.
- Default outreach prompt replacements enrich customer metadata with toolkit-derived contact details and enforce first-name greetings to match server quality.

### Fixed
- Initial outreach stage now records generated drafts in the pipeline summary, seeds reminder_task rows with toolkit credentials, and schedules follow-up events when `send_immediately` is false.
- Prompt-based draft generation no longer skips scheduling due to missing email fields and guarantees outputs without unresolved placeholders.

# [1.2.6] - 2025-10-24

### Added
- Automatically seed packaged prompt, scoring, and template JSON files into the writable `ffusesell_data/config` directory so fresh installs immediately pick up the default initial outreach draft prompt.
- Draft generation now records the scheduled reminder metadata in stage output while mirroring the server’s `schedule_auto_run` behaviour locally.

### Fixed
- Bundled configuration files are used as a fallback when the data directory is missing overrides, preventing empty prompt loads that previously produced low-quality duplicate drafts.

# [1.2.5] - 2025-10-24

### Added
- Local `reminder_task` table and scheduler plumbing so scheduled outreach mirrors the server flow and can be consumed by RealTimeX orchestration.
- Initial outreach and follow-up stages now emit reminder metadata whenever emails are scheduled, including team/customer context.

### Changed
- Event scheduler returns reminder IDs alongside scheduled events while preserving immutable default prompts when layering team overrides.

# [1.2.3] - 2025-10-21

### Added
- `LocalDataManager.search_products()` for server-compatible product filtering (status, keyword, limit, sort).
- CLI `product list` flags and `list_products.py` filters wired to the new search helper.
- Regression tests covering keyword search, sorting, and limiting behavior.

### Changed
- `get_products_by_org` now delegates to the filtered search path to avoid loading inactive results.
- Product management documentation updated for RealTimeX flows and CLI filter usage.

# [1.2.2] - 2025-10-21

### Added
- LocalDataManager regression tests covering product/team CRUD flows and sales process tracking helpers.

### Fixed
- Default team settings seeding now targets the `gs_team_*` columns, preventing initialization failures on fresh databases.

# [1.2.1] - 2025-10-21

### Changed
- Expose `__version__`, `__author__`, and `__description__` at the top-level `fusesell` module for easier runtime inspection.

### Fixed
- `import fusesell; fusesell.__version__` now reports the installed version instead of `unknown`.

## [1.2.0] - 2025-10-20

### Added
- Packaged CLI access via `FuseSellCLI` export to support embedded runtimes and automated tests.
- pytest coverage (`fusesell_local/tests/test_cli.py`) ensuring the CLI dry-run path remains stable.

### Changed
- Distribution renamed to `fusesell` to align with upcoming PyPI publication; console entry point now resolves to `fusesell_local.cli:main`.
- CLI implementation moved into `fusesell_local/cli.py`, with top-level `fusesell.py` delegating for backward compatibility.
- Documentation refreshed to instruct `pip install fusesell` and demonstrate programmatic CLI reuse.
- Published version `1.2.0` to PyPI under the `fusesell` distribution name.

### Fixed
- Ensured package metadata includes the CLI module so installations via pip expose the `fusesell` console script.

## [1.1.0] - 2025-10-20

### Added
- Library-first API (`fusesell_local.api`) exposing `build_config`, `execute_pipeline`, and supporting helpers for embedding FuseSell in external runtimes.
- Public exports in `fusesell_local.__init__` so consumers can import `FuseSellPipeline` and the new helpers directly.
- Programmatic configuration validation error (`ConfigValidationError`) for clearer failures in host applications.

### Changed
- CLI now delegates configuration/build/validation/logging to the shared library utilities, ensuring consistent behaviour across CLI and embedded usage.
- Pipeline context now forwards scheduling preferences (timezone, send_immediately, business hour fields) from configuration to stages.

### Fixed
- Continuation validation correctly requires `selected_draft_id` when performing `draft_rewrite` or `send` actions.

## [1.0.0] - 2025-01-07

### Added - Core Infrastructure Complete

#### CLI Interface
- Complete command-line interface with 25+ configuration options
- Comprehensive argument validation and error handling
- Multiple output formats (JSON, YAML, text)
- Dry-run mode for safe testing
- Process continuation support for resuming executions

#### Pipeline Engine
- Full pipeline orchestration with stage control
- Business logic validation extracted from original YAML workflows
- Sequential stage execution with data flow management
- Human-in-the-loop controls and approval points
- Comprehensive error handling and recovery mechanisms
- Execution tracking and detailed logging

#### Data Management
- SQLite database with complete schema for all data entities
- CRUD operations for executions, customers, lead scores, and email drafts
- Data export/import functionality for backup and migration
- Local data storage ensuring complete data ownership

#### Configuration System
- Team-specific configuration management
- Customizable LLM prompts for all stages
- Configurable scoring criteria and email templates
- JSON-based configuration files with validation

#### LLM Integration
- OpenAI GPT-4o-mini client with error handling
- Structured response parsing and validation
- Token usage tracking and optimization
- Response caching and retry mechanisms

#### Documentation
- Comprehensive README with installation and usage instructions
- Technical documentation covering architecture and APIs
- Business logic documentation extracted from original system
- Troubleshooting guide and development workflow

### Technical Details

#### Project Structure
```
fusesell-local/
 fusesell.py                 # Main CLI entry point
 requirements.txt            # Python dependencies
 setup.py                   # Package installation
 README.md                  # User documentation
 TECHNICAL.md               # Technical documentation
 CHANGELOG.md               # This file
 business_logic.md          # Business logic documentation
 fusesell_local/            # Main package
    pipeline.py            # Pipeline orchestrator
    stages/                # Pipeline stages (base implementation)
    utils/                 # Utilities (data, LLM, validation, logging)
    config/                # Configuration management
 ffusesell_data/             # Local data storage
     config/                # Configuration files
     drafts/                # Generated email drafts
     logs/                  # Execution logs
```

#### Key Features Implemented
- **Local Execution**: Complete data ownership with no external dependencies except LLM API
- **Business Logic Preservation**: All orchestration intelligence from original YAML workflows
- **Flexible Data Sources**: Support for websites, business cards, social media, and manual input
- **Stage Control**: Skip stages, stop after specific stages, save intermediate results
- **Process Continuation**: Resume executions from any point with specific actions
- **Comprehensive Validation**: Input validation, configuration validation, and error handling
- **Extensible Architecture**: Modular design for easy customization and extension

#### Database Schema
- `executions`: Execution tracking and metadata
- `stage_results`: Individual stage outputs and status
- `customers`: Customer profiles and contact information
- `lead_scores`: Scoring results and recommendations
- `email_drafts`: Generated email content and variations

#### Configuration Files
- `prompts.json`: LLM prompts for all stages
- `scoring_criteria.json`: Lead scoring rules and weights
- `email_templates.json`: Email template variations
- `team_settings.json`: Team-specific configurations

### Next Phase - Stage Implementations

The core infrastructure is complete and ready for individual stage implementations:

#### Planned Stage Development
1. **Data Acquisition**: Website scraping, business card OCR, social media extraction
2. **Data Preparation**: AI-powered data structuring and pain point identification
3. **Lead Scoring**: Product-customer fit evaluation with detailed breakdowns
4. **Initial Outreach**: Personalized email generation with multiple approaches
5. **Follow-up**: Context-aware follow-up sequences and timing optimization

#### Development Status
-  Core infrastructure (CLI, pipeline, database, configuration)
-  Business logic validation and orchestration rules
-  Process continuation and human-in-the-loop controls
-  Comprehensive documentation and user guides
-  Individual stage implementations (next development phase)

### Migration from Server-Based System

This release represents a complete conversion of the server-based FuseSell system to a local implementation:

#### Preserved Features
- All business logic and orchestration intelligence
- Team-specific prompts and configuration
- Human approval workflows and controls
- Comprehensive logging and execution tracking
- Multi-stage pipeline with flexible control

#### Enhanced Features
- Complete local data ownership and privacy
- Command-line interface with extensive options
- Process continuation and recovery capabilities
- Flexible data source handling
- Enhanced error handling and validation

#### Architectural Improvements
- Modular, extensible design
- Comprehensive input validation
- Local SQLite database for performance
- Configuration-driven customization
- Detailed technical documentation

### Installation and Usage

#### Requirements
- Python 3.8+
- OpenAI API key
- 50MB disk space for installation
- Additional space for data storage (varies by usage)

#### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run basic execution
python fusesell.py --openai-api-key YOUR_API_KEY \
                   --org-id your_org \
                   --org-name "Your Company" \
                   --customer-website "https://example.com"
```

#### Advanced Usage
```bash
# Full pipeline with custom settings
python fusesell.py --openai-api-key sk-xxx \
                   --org-id rta \
                   --org-name "RTA Corp" \
                   --customer-website "https://example.com" \
                   --customer-name "Acme Inc" \
                   --contact-name "John Doe" \
                   --team-id sales_team_1 \
                   --language english \
                   --output-format json \
                   --data-dir ./custom_data
```

### Support and Development

For technical support, feature requests, or contributions:
- Review the technical documentation in `TECHNICAL.md`
- Check the troubleshooting guide for common issues
- Refer to the business logic documentation for workflow details
- Contact the development team for advanced customization needs

---

## Future Releases

### [1.1.0] - Planned
- Complete data acquisition stage implementation
- Website scraping with content extraction
- Business card OCR processing
- Social media profile data extraction

### [1.2.0] - Planned  
- Complete data preparation stage implementation
- AI-powered customer profiling
- Pain point identification and analysis
- Financial and technology stack analysis

### [1.3.0] - Planned
- Complete lead scoring stage implementation
- Product-customer fit evaluation
- Detailed scoring breakdowns and recommendations
- Multi-product scoring capabilities

### [1.4.0] - Planned
- Complete initial outreach stage implementation
- Personalized email generation
- Multiple draft variations and approaches
- Human review workflow integration

### [1.5.0] - Planned
- Complete follow-up stage implementation
- Context-aware follow-up sequences
- Interaction history analysis
- Automated timing optimization
