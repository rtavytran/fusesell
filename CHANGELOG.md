# Changelog

All notable changes to FuseSell Local will be documented in this file.

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
 fusesell_data/             # Local data storage
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
