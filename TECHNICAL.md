# FuseSell Local - Technical Documentation

## Architecture Overview

FuseSell Local is designed as a modular, pipeline-based system that processes leads through five sequential stages. The architecture emphasizes local data ownership, configurability, and extensibility.

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │────│ Pipeline Engine  │────│ Stage Modules   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Validators    │    │  Data Manager    │    │   LLM Client    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Configuration  │    │ SQLite Database  │    │  OpenAI API     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Module Documentation

### 1. CLI Interface (`fusesell.py`)

The main entry point provides a comprehensive command-line interface with 25+ configuration options.

**Key Features:**

- Argument parsing and validation
- Configuration object creation
- Output formatting (JSON, YAML, text)
- Dry-run mode for testing
- Process continuation support

**Usage Patterns:**

```bash
# Basic execution
python fusesell.py --openai-api-key sk-xxx --org-id rta --org-name "RTA Corp" --customer-website "https://example.com"

# Advanced control
python fusesell.py --openai-api-key sk-xxx --org-id rta --org-name "RTA Corp" --customer-website "https://example.com" --stop-after lead_scoring --skip-stages follow_up --output-format json --dry-run
```

### 2. Pipeline Engine (`fusesell_local/pipeline.py`)

The core orchestration engine that manages stage execution, data flow, and business logic validation.

**Key Features:**

- Sequential stage execution
- Business logic validation
- Process continuation support
- Human-in-the-loop controls
- Comprehensive error handling
- Execution tracking and logging

**Business Logic Rules:**

- Validates execution context and prerequisites
- Enforces stage dependencies and data requirements
- Manages execution state and recovery
- Implements original YAML workflow intelligence

### 3. Base Stage Interface (`fusesell_local/stages/base_stage.py`)

Abstract base class that defines the common interface for all pipeline stages.

**Key Methods:**

- `execute()`: Main stage execution logic
- `validate_input()`: Input data validation
- `get_stage_name()`: Stage identification
- `get_required_fields()`: Input requirements

**Common Functionality:**

- LLM client initialization
- Error handling and logging
- Input/output validation
- Configuration access

### 4. Data Manager (`fusesell_local/utils/data_manager.py`)

SQLite-based data persistence layer with comprehensive CRUD operations.

**Database Architecture:**

FuseSell Local uses a comprehensive SQLite database with 14 normalized tables covering all aspects of the sales automation pipeline:

- **Core Pipeline**: `executions`, `stage_results`, `customers`, `lead_scores`, `email_drafts`
- **Task Management**: `tasks`, `operations`, `customer_tasks`
- **Team Configuration**: `teams`, `team_settings`, `products`
- **Advanced Features**: `prompts`, `scheduler_rules`, `extracted_files`

**📋 For complete database schema, relationships, and query examples, see [DATABASE.md](DATABASE.md)**

**Key Database Features:**
- Single SQLite file (`fusesell_data/fusesell.db`) with complete data ownership
- Normalized schema with proper foreign key relationships
- Performance indexes for fast queries
- JSON storage for complex configuration data
- Full audit trail and execution tracking

### 5. LLM Client (`fusesell_local/utils/llm_client.py`)

OpenAI API integration with error handling and response parsing.

**Features:**

- Structured response parsing
- Error handling and retries
- Token usage tracking
- Response validation
- Multiple model support

### 6. Configuration System (`fusesell_local/config/`)

Team-specific configuration management with customizable prompts and settings.

**Configuration Files:**

- `prompts.json`: LLM prompts for each stage
- `scoring_criteria.json`: Lead scoring rules and weights
- `email_templates.json`: Email template variations
- `team_settings.json`: Team-specific configurations

## Data Flow

### 1. Initialization

```
CLI Arguments → Validation → Configuration Object → Pipeline Creation
```

### 2. Stage Execution

```
Input Data → Stage Validation → LLM Processing → Output Validation → Database Storage
```

### 3. Pipeline Flow

```
Data Acquisition → Data Preparation → Lead Scoring → Initial Outreach → Follow-up
```

### 4. Error Handling

```
Error Detection → Logging → Recovery Attempt → User Notification → Graceful Degradation
```

## Extension Points

### Adding New Stages

1. Create a new stage class inheriting from `BaseStage`
2. Implement required methods (`execute`, `validate_input`, etc.)
3. Add stage configuration to `prompts.json`
4. Update pipeline orchestrator to include the new stage

### Customizing Prompts

1. Edit `fusesell_data/config/prompts.json`
2. Modify team-specific prompt templates
3. Add new prompt variations for different approaches
4. Test with dry-run mode before production use

### Adding Data Sources

1. Extend input validation in `validators.py`
2. Add new CLI arguments for the data source
3. Implement data extraction logic in relevant stages
4. Update database schema if needed

## Performance Considerations

### Database Optimization

- SQLite with proper indexing for execution queries
- Batch operations for bulk data processing
- Connection pooling for concurrent access
- Regular database maintenance and cleanup

### LLM API Optimization

- Request batching where possible
- Response caching for repeated queries
- Token usage monitoring and optimization
- Error handling with exponential backoff

### Memory Management

- Streaming data processing for large datasets
- Garbage collection for long-running processes
- Memory-efficient data structures
- Resource cleanup after stage completion

## Security Considerations

### API Key Management

- Keys passed as command-line arguments (not stored)
- Environment variable support
- Secure key validation
- No key logging or persistence

### Data Privacy

- All customer data stored locally
- No external data transmission (except LLM API)
- Input sanitization and validation
- Secure database file permissions

### Input Validation

- Comprehensive argument validation
- SQL injection prevention
- XSS protection for web data
- File path traversal prevention

## Troubleshooting

### Common Issues

1. **API Key Errors**

   - Verify OpenAI API key validity
   - Check API quota and billing status
   - Ensure proper key format (starts with 'sk-')

2. **Database Errors**

   - Check file permissions for SQLite database
   - Verify disk space availability
   - Ensure database directory exists

3. **Stage Execution Failures**

   - Review execution logs for detailed error messages
   - Validate input data format and completeness
   - Check LLM response parsing logic

4. **Configuration Issues**
   - Verify configuration file syntax (valid JSON)
   - Check file paths and permissions
   - Validate prompt template formatting

### Debug Mode

Enable detailed logging with:

```bash
python fusesell.py --debug --log-level DEBUG [other arguments]
```

### Log Analysis

Logs are stored in `fusesell_data/logs/` with the following structure:

- `execution_YYYYMMDD_HHMMSS.log`: Detailed execution logs
- `error.log`: Error-specific logging
- `debug.log`: Debug-level information (when enabled)

## Development Workflow

### Testing Changes

1. Use dry-run mode for safe testing:

   ```bash
   python fusesell.py --dry-run [arguments]
   ```

2. Test individual stages:

   ```bash
   python fusesell.py --stop-after data_acquisition [arguments]
   ```

3. Validate configuration changes:
   ```bash
   python fusesell.py --validate-config [arguments]
   ```

### Code Quality

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Implement comprehensive error handling
- Add docstrings for all public methods
- Write unit tests for new functionality

### Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Update documentation
5. Submit a pull request with detailed description

## Future Enhancements

### Planned Features

- Web interface for easier management
- Advanced analytics and reporting
- Integration with CRM systems
- Multi-language support
- Advanced AI model options

### Performance Improvements

- Parallel stage execution where possible
- Advanced caching mechanisms
- Database optimization and indexing
- Memory usage optimization

### Security Enhancements

- Encryption for sensitive data storage
- Advanced input validation
- Audit logging for compliance
- Role-based access control
