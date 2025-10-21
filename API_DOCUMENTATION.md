# FuseSell Local - API Documentation

## Overview

FuseSell Local is a Python-based sales automation pipeline that converts server-based YAML workflows into local, executable modules. This document provides technical details for developers who want to understand, modify, or extend the system.

## Architecture Overview

```

                    FuseSell Local Architecture              

 CLI Interface (fusesell.py)                                
  Argument parsing and validation                        
  Configuration object creation                          
  Pipeline execution orchestration                       

 Pipeline Engine (fusesell_local/pipeline.py)               
  Sequential stage execution                             
  Context management and data flow                       
  Error handling and recovery                            
  Process continuation support                           

 Stage Modules (fusesell_local/stages/)                     
  BaseStage - Abstract base class                        
  DataAcquisitionStage - Multi-source data collection    
  DataPreparationStage - AI-powered data structuring     
  LeadScoringStage - Product-customer fit evaluation     
  InitialOutreachStage - Email draft generation          
  FollowUpStage - Context-aware follow-up sequences      

 Utilities (fusesell_local/utils/)                          
  DataManager - SQLite database operations               
  LLMClient - OpenAI API integration                     
  EventScheduler - Database-based event scheduling       
  TimezoneDetector - Timezone detection from location    
  Validators - Input validation and sanitization         

 Configuration (fusesell_local/config/)                     
  Team-specific settings                                 
  Customizable LLM prompts                               
  Scoring criteria configuration                         

```

## Core Components

### 1. Pipeline Engine (`fusesell_local/pipeline.py`)

The main orchestration engine that manages stage execution and data flow.

#### Class: `FuseSellPipeline`

**Constructor:**
```python
def __init__(self, config: Dict[str, Any])
```

**Parameters:**
- `config`: Configuration dictionary containing API keys, settings, and execution parameters

**Key Methods:**

##### `execute(input_data: Dict[str, Any]) -> Dict[str, Any]`
Executes the complete pipeline or continues from a specific stage.

**Parameters:**
- `input_data`: Input data containing customer information and execution parameters

**Returns:**
- Dictionary containing execution results, stage outputs, and metadata

**Example:**
```python
pipeline = FuseSellPipeline(config)
result = pipeline.execute({
    'input_website': 'https://example.com',
    'org_id': 'rta',
    'org_name': 'RTA Corp'
})
```

##### `continue_execution(execution_id: str, action: str, **kwargs) -> Dict[str, Any]`
Continues a previous execution with a specific action.

**Parameters:**
- `execution_id`: ID of the execution to continue
- `action`: Action to perform ('draft_write', 'draft_rewrite', 'send', 'close')
- `**kwargs`: Additional parameters specific to the action

### 2. Base Stage (`fusesell_local/stages/base_stage.py`)

Abstract base class that all stage implementations inherit from.

#### Class: `BaseStage`

**Abstract Methods:**
```python
def execute(self, context: Dict[str, Any]) -> Dict[str, Any]
def validate_input(self, context: Dict[str, Any]) -> bool
def get_required_fields(self) -> List[str]
```

**Utility Methods:**

##### `call_llm(prompt: str, **kwargs) -> str`
Makes a call to the configured LLM with error handling and retries.

##### `save_stage_result(context: Dict[str, Any], result_data: Dict[str, Any]) -> bool`
Saves stage results to the database.

##### `create_success_result(data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]`
Creates a standardized success response.

##### `handle_stage_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]`
Handles stage errors with logging and standardized error responses.

### 3. Stage Implementations

#### DataAcquisitionStage

Collects customer data from multiple sources.

**Supported Data Sources:**
- Website scraping (direct HTTP + Serper API)
- Business card OCR (Tesseract, EasyOCR, Cloud OCR)
- Social media profiles (LinkedIn, Facebook)
- Free text input
- Customer descriptions

**Key Methods:**

##### `_scrape_website(url: str) -> Optional[str]`
Scrapes website content using multiple methods.

##### `_process_business_card(business_card_url: str) -> Optional[str]`
Processes business card images using OCR.

##### `_extract_text_from_image(image_data: bytes) -> Optional[str]`
Extracts text from images using multiple OCR engines.

**OCR Support:**
- **Tesseract OCR**: Primary OCR engine with preprocessing
- **EasyOCR**: Fallback OCR with confidence scoring
- **Cloud OCR**: Google Vision API, Azure Computer Vision
- **PDF Support**: PyPDF2 and PyMuPDF for PDF business cards

#### DataPreparationStage

Structures and enriches customer data using AI.

**Key Methods:**

##### `_structure_customer_data(raw_data: str) -> Dict[str, Any]`
Uses LLM to extract structured information from raw data.

##### `_extract_pain_points(structured_data: Dict[str, Any]) -> List[Dict[str, Any]]`
Identifies and categorizes customer pain points.

##### `_analyze_financial_data(structured_data: Dict[str, Any]) -> Dict[str, Any]`
Analyzes company financial health and size indicators.

#### LeadScoringStage

Evaluates product-customer fit using weighted criteria.

**Scoring Criteria:**
- Industry fit (25%)
- Pain points alignment (30%)
- Company size fit (20%)
- Product feature alignment (15%)
- Geographic fit (10%)

**Key Methods:**

##### `_evaluate_product_fit(customer_data: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]`
Evaluates how well a product fits the customer's needs.

##### `_calculate_weighted_score(criteria_scores: Dict[str, float]) -> float`
Calculates final weighted score based on criteria.

#### InitialOutreachStage

Generates personalized email drafts with action-based routing.

**Supported Actions:**
- `draft_write`: Generate new email drafts
- `draft_rewrite`: Modify existing draft
- `send`: Send approved draft (immediate or scheduled)
- `close`: Close outreach process

**Key Methods:**

##### `_generate_email_drafts(customer_data: Dict[str, Any], product: Dict[str, Any]) -> List[Dict[str, Any]]`
Generates multiple email draft variations.

##### `_schedule_email(draft: Dict[str, Any], recipient_address: str, recipient_name: str, context: Dict[str, Any]) -> Dict[str, Any]`
Schedules email for optimal sending time.

#### FollowUpStage

Manages follow-up email sequences with context awareness.

**Key Methods:**

##### `_analyze_interaction_history(context: Dict[str, Any]) -> Dict[str, Any]`
Analyzes previous interactions to determine follow-up strategy.

##### `_generate_follow_up_strategy(context: Dict[str, Any]) -> Dict[str, Any]`
Creates follow-up strategy based on interaction history.

### 4. Utilities

#### DataManager (`fusesell_local/utils/data_manager.py`)

Manages SQLite database operations and data persistence.

**Database Schema:**
```sql
-- Execution tracking
CREATE TABLE executions (
    execution_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    config_json TEXT,
    results_json TEXT
);

-- Stage results
CREATE TABLE stage_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    status TEXT NOT NULL,
    input_data TEXT,
    output_data TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Customer profiles
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    company_name TEXT,
    website TEXT,
    industry TEXT,
    profile_data TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lead scores
CREATE TABLE lead_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    customer_id TEXT,
    product_id TEXT,
    score REAL,
    criteria_breakdown TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email drafts
CREATE TABLE email_drafts (
    draft_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    customer_id TEXT,
    subject TEXT,
    content TEXT,
    draft_type TEXT, -- initial_outreach, follow_up
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scheduling rules
CREATE TABLE scheduling_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    team_id TEXT,
    rule_name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    business_hours_start TEXT DEFAULT '08:00',
    business_hours_end TEXT DEFAULT '20:00',
    default_delay_hours INTEGER DEFAULT 2,
    timezone TEXT DEFAULT 'Asia/Bangkok',
    follow_up_delay_hours INTEGER DEFAULT 120,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Key Methods:**

##### `save_execution(execution_data: Dict[str, Any]) -> bool`
Saves execution metadata to database.

##### `get_execution(execution_id: str) -> Optional[Dict[str, Any]]`
Retrieves execution data by ID.

##### `save_email_draft(draft_data: Dict[str, Any]) -> bool`
Saves email draft to database.

##### `get_email_draft(draft_id: str) -> Optional[Dict[str, Any]]`
Retrieves email draft by ID.

#### EventScheduler (`fusesell_local/utils/event_scheduler.py`)

Database-based event scheduling system that creates scheduled events for external processing.

**Key Methods:**

##### `schedule_email(draft_id: str, recipient_address: str, recipient_name: str, org_id: str, team_id: str = None, customer_timezone: str = None, email_type: str = 'initial') -> Dict[str, Any]`
Schedules an email for delayed sending.

**Parameters:**
- `draft_id`: ID of the email draft to send
- `recipient_address`: Email address of recipient
- `recipient_name`: Name of recipient
- `org_id`: Organization ID
- `team_id`: Team ID (optional)
- `customer_timezone`: Customer's timezone (optional, auto-detected if not provided)
- `email_type`: Type of email ('initial' or 'follow_up')

**Returns:**
- Dictionary containing scheduling result with job ID and send time

##### `create_scheduling_rule(org_id: str, team_id: str = None, **kwargs) -> bool`
Creates or updates a scheduling rule for an organization/team.

#### TimezoneDetector (`fusesell_local/utils/timezone_detector.py`)

Detects customer timezone from address and location information.

**Key Methods:**

##### `detect_timezone(customer_data: Dict[str, Any]) -> str`
Detects customer timezone from various data sources.

**Detection Sources:**
- Explicit timezone field
- Address parsing (country, state, city)
- Company location information
- Contact location details

**Supported Timezones:**
- All major world timezones
- US state-specific timezones
- Major city timezones
- Country-based timezone mapping

#### LLMClient (`fusesell_local/utils/llm_client.py`)

OpenAI API integration with error handling and response parsing.

**Key Methods:**

##### `call_llm(prompt: str, model: str = 'gpt-4o-mini', **kwargs) -> str`
Makes API call to OpenAI with retries and error handling.

##### `parse_json_response(response: str) -> Dict[str, Any]`
Parses JSON responses from LLM with fallback handling.

## Configuration System

### Team-Specific Configuration

Configuration files are stored in `fusesell_data/config/`:

#### `prompts.json`
Customizable LLM prompts for each stage:

```json
{
  "data_preparation": {
    "customer_analysis": "Analyze the following customer data...",
    "pain_point_identification": "Identify pain points from..."
  },
  "lead_scoring": {
    "product_evaluation": "Evaluate product fit..."
  },
  "initial_outreach": {
    "email_generation": "Generate personalized email..."
  },
  "follow_up": {
    "follow_up_analysis": "Analyze follow-up context..."
  }
}
```

#### `scoring_criteria.json`
Lead scoring weights and criteria:

```json
{
  "criteria": {
    "industry_fit": {"weight": 25, "description": "Industry alignment"},
    "company_size": {"weight": 20, "description": "Company size fit"},
    "pain_points": {"weight": 30, "description": "Pain point match"},
    "technology": {"weight": 15, "description": "Technology compatibility"},
    "budget": {"weight": 10, "description": "Budget indicators"}
  },
  "thresholds": {
    "high_quality": 80,
    "medium_quality": 60,
    "low_quality": 40
  }
}
```

## Error Handling

### Error Types

```python
class FuseSellError(Exception):
    """Base exception for FuseSell errors"""
    pass

class ValidationError(FuseSellError):
    """Input validation errors"""
    pass

class ExternalServiceError(FuseSellError):
    """External API/service errors"""
    pass

class DataProcessingError(FuseSellError):
    """Data processing and transformation errors"""
    pass

class SchedulingError(FuseSellError):
    """Email scheduling errors"""
    pass
```

### Error Handling Strategy

1. **Input Validation**: Comprehensive validation at CLI and stage levels
2. **External Service Failures**: Retry logic with exponential backoff
3. **Data Processing Errors**: Graceful degradation with fallback data
4. **Partial Results**: Save intermediate results for recovery
5. **Logging**: Detailed error logging with context information

## Extension Points

### Adding New Stages

1. Create a new class inheriting from `BaseStage`
2. Implement required abstract methods
3. Add stage to pipeline configuration
4. Update CLI arguments if needed

Example:
```python
class CustomStage(BaseStage):
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation here
        pass
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        # Validation logic
        pass
    
    def get_required_fields(self) -> List[str]:
        return ['required_field1', 'required_field2']
```

### Adding New Data Sources

1. Add new method to `DataAcquisitionStage`
2. Update CLI arguments
3. Add validation logic
4. Update documentation

### Customizing LLM Prompts

1. Edit `fusesell_data/config/prompts.json`
2. Use placeholders for dynamic content: `{customer_name}`, `{company_name}`
3. Test prompts with dry-run mode

### Adding New Scheduling Rules

1. Use `EventScheduler.create_scheduling_rule()`
2. Configure business hours, delays, timezones
3. Rules are automatically applied to new emails

## Performance Considerations

### Database Optimization

- Use indexes on frequently queried fields
- Regular cleanup of old execution data
- Consider partitioning for large datasets

### LLM API Optimization

- Use appropriate temperature settings (0.2-0.8)
- Implement response caching for repeated queries
- Monitor token usage and costs

### Memory Management

- Process large datasets in chunks
- Clean up temporary files after processing
- Monitor memory usage during OCR operations

## Security Considerations

### API Key Management

- Never store API keys in code or configuration files
- Use environment variables or secure key management
- Rotate keys regularly

### Data Privacy

- All customer data stays local
- Implement data retention policies
- Secure database file permissions

### Input Validation

- Sanitize all user inputs
- Validate URLs before scraping
- Check file types before processing

## Troubleshooting Guide

### Common Issues

#### 1. "No data could be collected from any source"
**Cause**: All data sources failed to return data
**Solution**: 
- Check internet connectivity
- Verify URLs are accessible
- Check API keys and quotas

#### 2. "LLM API call failed"
**Cause**: OpenAI API issues
**Solution**:
- Verify API key is valid
- Check API quota and billing
- Try with lower temperature or different model

#### 3. "Database connection failed"
**Cause**: SQLite database issues
**Solution**:
- Check file permissions
- Verify disk space
- Check database file corruption

#### 4. "Email scheduling failed"
**Cause**: Scheduler service issues
**Solution**:
- Check if scheduler service is running
- Verify timezone configuration
- Check database connectivity

### Debug Mode

Enable debug logging:
```bash
python fusesell.py --log-level DEBUG --verbose
```

### Dry Run Mode

Test without API calls:
```bash
python fusesell.py --dry-run
```

## Development Workflow

### Setting Up Development Environment

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up test data directory
4. Configure test API keys
5. Run tests: `python -m pytest`

### Testing Strategy

1. **Unit Tests**: Test individual methods and functions
2. **Integration Tests**: Test stage-to-stage data flow
3. **End-to-End Tests**: Test complete pipeline execution
4. **Performance Tests**: Test with large datasets

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Add logging for important operations

## API Reference Summary

### Main Classes

| Class | Module | Purpose |
|-------|--------|---------|
| `FuseSellPipeline` | `pipeline.py` | Main orchestration engine |
| `BaseStage` | `stages/base_stage.py` | Abstract base for all stages |
| `DataManager` | `utils/data_manager.py` | Database operations |
| `EventScheduler` | `utils/event_scheduler.py` | Event scheduling system |
| `TimezoneDetector` | `utils/timezone_detector.py` | Timezone detection |
| `LLMClient` | `utils/llm_client.py` | OpenAI API integration |

### Key Methods

| Method | Class | Purpose |
|--------|-------|---------|
| `execute()` | `FuseSellPipeline` | Execute pipeline |
| `call_llm()` | `BaseStage` | Make LLM API call |
| `schedule_email_event()` | `EventScheduler` | Schedule email event |
| `detect_timezone()` | `TimezoneDetector` | Detect customer timezone |
| `save_email_draft()` | `DataManager` | Save draft to database |

This documentation provides a comprehensive technical reference for developers working with FuseSell Local. For user-focused documentation, see `README.md` and `HELP.md`.