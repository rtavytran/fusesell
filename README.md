# FuseSell Local

**Complete AI-powered sales automation pipeline that runs entirely on your local machine.**

FuseSell Local is a production-ready implementation of the FuseSell AI sales automation system, converted from server-based YAML workflows to a comprehensive Python command-line tool with full data ownership and privacy control.

> Latest release: `fusesell==1.2.0` is available on PyPI via `pip install fusesell`.

## ðŸš€ Complete Pipeline Overview

FuseSell Local processes leads through a complete 5-stage AI-powered pipeline:

1. **Data Acquisition** âœ… - Multi-source customer data extraction (websites, business cards, social media)
2. **Data Preparation** âœ… - AI-powered customer profiling and pain point analysis
3. **Lead Scoring** âœ… - Advanced product-customer fit evaluation with detailed scoring
4. **Initial Outreach** âœ… - Intelligent email generation with multiple personalized approaches
5. **Follow-up** âœ… - Context-aware follow-up sequences with interaction history analysis

**Status: 100% Complete - Production Ready**

## ðŸš€ Quick Start

### Installation

1. **Install Python dependencies:**

```bash
cd fusesell-local
pip install -r requirements.txt
```

**That's it!** No additional setup required. The system automatically creates all necessary database tables and default configurations on first run.

2. **Test the installation:**

```bash
python fusesell.py --openai-api-key YOUR_API_KEY \
                   --org-id test_org \
                   --org-name "Test Company" \
                   --input-website "https://example.com" \
                   --dry-run
```

### First Run (Complete Pipeline)

```bash
# Full end-to-end sales automation
python fusesell.py \
  --openai-api-key "sk-your-key" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-website "https://targetcompany.com"
```

This single command will:
1. Extract customer data from the website
2. Analyze and structure the data using AI
3. Score the lead against your products
4. Generate personalized email drafts
5. Create follow-up sequences

## Library Integration

FuseSell Local can now be imported directly so orchestrators like RealtimeX can execute the pipeline without spawning the CLI.

1. Install the package in your Python environment:

   ```bash
   pip install fusesell
   ```

2. Run the pipeline programmatically with default helpers:

   ```python
   from fusesell_local import execute_pipeline

   result = execute_pipeline(
       {
           "openai_api_key": "sk-your-key",
           "org_id": "mycompany",
           "org_name": "My Company Inc",
           "full_input": "Seller: My Company Inc, Customer: Target Corp, Communication: English",
           "input_website": "https://targetcompany.com",
       }
   )

   print(result["status"])
   ```

3. For finer-grained control (custom logging, shared storage, etc.), compose the lower-level utilities:

   ```python
   from fusesell_local import (
       build_config,
       configure_logging,
       prepare_data_directory,
       run_pipeline,
       validate_config,
   )

   options = {
       "openai_api_key": "sk-your-key",
       "org_id": "mycompany",
       "org_name": "My Company Inc",
       "full_input": "Seller: My Company Inc, Customer: Target Corp, Communication: English",
       "input_website": "https://targetcompany.com",
       "customer_timezone": "America/New_York",
   }

   config = build_config(options)
   prepare_data_directory(config)
   configure_logging(config)
   valid, errors = validate_config(config)
   if not valid:
       raise ValueError(errors)

   outputs = run_pipeline(config)
   ```

When embedding FuseSell inside ephemeral interpreter services, consider supplying a custom `data_dir` scoped per run and set `auto_configure_logging=False` if you prefer stdout logging.

4. Reuse the packaged CLI inside scripts or tests:

   ```python
   from fusesell_local import FuseSellCLI

   cli = FuseSellCLI()
   cli.run([
       "--openai-api-key", "sk-your-key",
       "--org-id", "mycompany",
       "--org-name", "My Company Inc",
       "--full-input", "Seller: My Company Inc, Customer: Target Corp, Communication: English",
       "--input-description", "Example Corp lead from automation script",
       "--dry-run",
   ])
   ```

## ðŸ“‹ Complete Usage Examples

### Example 1: Full Pipeline - Website to Follow-up

```bash
# Complete end-to-end sales automation
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-website "https://targetcompany.com"
```

**Complete Pipeline Execution:**
1. **Data Acquisition**: Scrapes website, extracts company information
2. **Data Preparation**: AI analysis of company profile and pain points
3. **Lead Scoring**: Evaluates product-customer fit with detailed scoring
4. **Initial Outreach**: Generates 4 personalized email draft variations
5. **Follow-up**: Creates context-aware follow-up sequence strategies
### Exa
mple 2: Multi-Source Data Collection

```bash
# Combine multiple data sources for comprehensive profiling
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-website "https://targetcompany.com" \
  --input-business-card "https://example.com/business-card.jpg" \
  --input-linkedin-url "https://linkedin.com/company/targetcompany" \
  --input-facebook-url "https://facebook.com/targetcompany" \
  --input-description "Leading fintech startup in NYC, 50+ employees"
```

**Multi-Source Processing:**
- **Website**: Company information, services, team details
- **Business Card**: Contact information via OCR processing
- **LinkedIn**: Professional information, company updates, connections
- **Facebook**: Business information, customer engagement, posts
- **Description**: Additional context and insights

### Example 3: Email Generation and Management

```bash
# Generate initial outreach emails only
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-description "Customer: John Smith at Acme Corp, email: john@acme.com, industry: manufacturing" \
  --stop-after initial_outreach
```

**Email Generation Features:**
- **4 Draft Approaches**: Professional Direct, Consultative, Industry Expert, Relationship Building
- **Personalized Subject Lines**: 4 variations per draft
- **Personalization Scoring**: 0-100 score based on customer data usage
- **Draft Comparison**: Side-by-side analysis with recommendations

### Example 4: Email Sending with Smart Scheduling

```bash
# Send email with optimal timing
python fusesell.py \
  --action send \
  --selected-draft-id "draft_professional_direct_abc123" \
  --recipient-address "john@acme.com" \
  --recipient-name "John Smith" \
  --org-id "mycompany" \
  --customer-timezone "America/New_York" \
  --business-hours-start "09:00" \
  --business-hours-end "17:00"
```

**Smart Scheduling Features:**
- **Timezone Intelligence**: Respects customer's business hours
- **Optimal Timing**: 2-hour default delay with business hours respect
- **Weekend Handling**: Automatically schedules for next business day
- **Database Events**: Creates events for external app processing

### Example 5: Follow-up Email Generation

```bash
# Generate context-aware follow-up emails
python fusesell.py \
  --action draft_write \
  --stage follow_up \
  --execution-id "exec_abc123_20241209" \
  --org-id "mycompany"
```

**Follow-up Intelligence:**
- **Interaction Analysis**: Analyzes previous email history and engagement
- **Strategy Selection**: Chooses appropriate follow-up approach (1st, 2nd, 3rd, final)
- **Context Awareness**: References previous interactions appropriately
- **Respectful Limits**: Maximum 5 follow-ups with graceful closure

### Example 6: Draft Rewriting and Improvement

```bash
# Rewrite existing draft based on feedback
python fusesell.py \
  --action draft_rewrite \
  --selected-draft-id "draft_consultative_xyz789" \
  --reason "Make it more technical and focus on ROI benefits" \
  --org-id "mycompany"
```

**Draft Rewriting Features:**
- **LLM-Powered Rewriting**: Uses AI to incorporate feedback
- **Version Control**: Tracks all rewrites with history
- **Personalization Maintenance**: Keeps customer-specific details
- **Improvement Tracking**: Monitors changes and effectiveness

### Example 7: Pipeline Control and Testing

```bash
# Stop after lead scoring (don't generate emails)
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-website "https://targetcorp.com" \
  --stop-after lead_scoring

# Skip follow-up generation
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-website "https://targetcorp.com" \
  --skip-stages follow_up

# Dry run (no API calls, uses mock data)
python fusesell.py \
  --openai-api-key "test-key" \
  --org-id "test" \
  --org-name "Test Company" \
  --input-website "https://example.com" \
  --dry-run

# Debug mode with detailed logging
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-website "https://targetcorp.com" \
  --log-level DEBUG
```

### Example 8: Process Continuation

```bash
# First run - stop after data preparation
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-website "https://targetcorp.com" \
  --execution-id "lead_001" \
  --stop-after data_preparation

# Continue from where we left off
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --continue-execution "lead_001" \
  --continue-action "approve_and_continue"
```

## ðŸ“Š Command Reference

### Required Arguments

| Argument           | Description                                              | Example                                                       |
| ------------------ | -------------------------------------------------------- | ------------------------------------------------------------- |
| `--openai-api-key` | Your OpenAI API key                                      | `sk-proj-abc123...`                                           |
| `--org-id`         | Organization identifier                                  | `rta`                                                         |
| `--org-name`       | Organization name                                        | `"RTA Corp"`                                                  |
| `--full-input`     | Full information input (Seller, Customer, Communication) | `"Seller: RTA Corp, Customer: Nagen, Communication: English"` |

### Data Sources (At Least One Required)

| Argument                | Description                                            | Example                                                                        |
| ----------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `--input-website`       | Website URL (empty if not provided)                    | `https://example.com`                                                          |
| `--input-description`   | Full customer info (name, phone, email, address, etc.) | `"Customer: Simone Simmons of company Nagen with email: simonesimmons@rta.vn"` |
| `--input-business-card` | Business card image URL (empty if not provided)        | `https://example.com/card.jpg`                                                 |
| `--input-linkedin-url`  | LinkedIn profile/business page URL                     | `https://linkedin.com/company/acme`                                            |
| `--input-facebook-url`  | Facebook profile/business page URL                     | `https://facebook.com/acme`                                                    |
| `--input-freetext`      | Free text input with customer information              | `"Contact John at Acme Corp for software solutions"`                           |

### Optional Context Fields

| Argument        | Description                                     | Example                                     |
| --------------- | ----------------------------------------------- | ------------------------------------------- |
| `--customer-id` | Customer ID for tracking (null if not provided) | `uuid:5b06617a-339e-47c2-b516-6b32de8ec9a7` |

### Pipeline Control

| Argument               | Description                 | Example                                  |
| ---------------------- | --------------------------- | ---------------------------------------- |
| `--stop-after`         | Stop after specific stage   | `--stop-after lead_scoring`              |
| `--skip-stages`        | Skip specific stages        | `--skip-stages follow_up`                |
| `--continue-execution` | Continue previous execution | `--continue-execution exec_123`          |
| `--continue-action`    | Action for continuation     | `--continue-action approve_and_continue` |

### Output Options

| Argument          | Description              | Example                |
| ----------------- | ------------------------ | ---------------------- |
| `--output-format` | Output format            | `json`, `yaml`, `text` |
| `--data-dir`      | Data directory           | `./my_data`            |
| `--execution-id`  | Custom execution ID      | `my_execution_001`     |
| `--dry-run`       | Test mode (no API calls) | `--dry-run`            |

### Team & Project Settings

| Argument         | Description     | Example                                     |
| ---------------- | --------------- | ------------------------------------------- |
| `--team-id`      | Team identifier | `uuid:6dc8faf9-cf04-07eb-846b-a928dddd701c` |
| `--team-name`    | Team name       | `"Annuity Products Sales Team"`             |
| `--project-code` | Project code    | `C1293`                                     |

### Advanced Options

| Argument            | Description                     | Example                    |
| ------------------- | ------------------------------- | -------------------------- |
| `--language`        | Processing language             | `en`, `vi`                 |
| `--llm-temperature` | LLM creativity (0.0-1.0)        | `0.7`                      |
| `--llm-max-tokens`  | Max tokens per request          | `2000`                     |
| `--serper-api-key`  | Serper API key for enhanced web scraping | `your-serper-key`          |
| `--log-level`       | Logging level                   | `DEBUG`, `INFO`, `WARNING` |

### Email Scheduling Options

| Argument                 | Description                        | Example              |
| ------------------------ | ---------------------------------- | -------------------- |
| `--send-immediately`     | Skip timing optimization, send now | `--send-immediately` |
| `--customer-timezone`    | Customer's timezone                | `"America/New_York"` |
| `--business-hours-start` | Business hours start time          | `"09:00"`            |
| `--business-hours-end`   | Business hours end time            | `"17:00"`            |
| `--delay-hours`          | Custom delay before sending        | `4`                  |

### Action-Based Operations

| Action          | Description               | Required Parameters                          |
| --------------- | ------------------------- | -------------------------------------------- |
| `draft_write`   | Generate new email drafts | `--org-id`, `--org-name`                     |
| `draft_rewrite` | Modify existing draft     | `--selected-draft-id`, `--reason`            |
| `send`          | Send/schedule email       | `--selected-draft-id`, `--recipient-address` |
| `close`         | Close outreach sequence   | `--reason`                                   |

### Stage-Specific Operations

| Stage              | Purpose               | Key Parameters                           |
| ------------------ | --------------------- | ---------------------------------------- |
| `data_acquisition` | Extract customer data | `--input-website`, `--input-description` |
| `data_preparation` | AI customer analysis  | Automatic (uses previous stage data)     |
| `lead_scoring`     | Product-customer fit  | Automatic (uses previous stage data)     |
| `initial_outreach` | Email generation      | `--action draft_write`                   |
| `follow_up`        | Follow-up sequences   | `--action draft_write`, `--execution-id` |## ðŸŒ Enha
nced Web Scraping with Serper API

**Optional but Recommended:** Add `--serper-api-key` for better data collection:

```bash
# Enhanced scraping capabilities
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --serper-api-key "your-serper-key" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --input-website "https://targetcompany.com"
```

**Benefits:**
- ðŸŒ **Better Website Scraping**: More reliable content extraction
- ðŸ” **Company Research**: Automatic Google search for company info
- ðŸ“± **Social Media Access**: Enhanced LinkedIn/Facebook scraping
- ðŸš« **Graceful Fallback**: Works without Serper API (shows warnings)

**Get Serper API Key:** Visit [serper.dev](https://serper.dev) â†’ Sign up â†’ Get free API key

## ðŸ”„ Complete Pipeline Stages

### 1. Data Acquisition âœ…

**Purpose:** Multi-source customer data extraction

**Data Sources:**
- **Website Scraping**: Company information, contact details, business description
- **Business Card OCR**: Contact extraction from images (Tesseract, EasyOCR, Cloud APIs)
- **LinkedIn Profiles**: Professional information, company details, connections
- **Facebook Pages**: Business information, contact details, public posts
- **Manual Input**: Structured customer descriptions

**AI Processing:**
- LLM-powered information extraction and structuring
- Multi-source data merging and conflict resolution
- Company research via search APIs

**Output:** Comprehensive customer profile with contact information

### 2. Data Preparation âœ…

**Purpose:** AI-powered customer profiling and analysis

**AI Analysis:**
- **Customer Profiling**: Structured company information extraction
- **Pain Point Identification**: Categorized business challenges and priorities
- **Financial Analysis**: Revenue estimation, growth potential, funding sources
- **Technology Assessment**: Digital maturity and technology stack analysis
- **Competitive Analysis**: Market positioning and competitive landscape
- **Development Planning**: Growth plans, timeline estimates, resource requirements

**Output:** Enriched customer profile with pain points and business insights

### 3. Lead Scoring âœ…

**Purpose:** Advanced product-customer fit evaluation

**Scoring Framework:**
- **5 Weighted Criteria**: Industry fit, company size, pain points, technology, budget
- **ROI Analysis**: Payback period estimation and financial impact assessment
- **Implementation Feasibility**: Technical complexity and resource requirements
- **Competitive Positioning**: Market advantage and differentiation analysis
- **Feature Alignment**: Product capabilities vs. customer needs matching
- **Scalability Assessment**: Growth potential and expansion opportunities

**Output:** Detailed scoring breakdown with product recommendations and justifications

### 4. Initial Outreach âœ…

**Purpose:** Intelligent email generation and draft management

**Email Generation:**
- **4 Approach Variations**: Professional Direct, Consultative, Industry Expert, Relationship Building
- **Personalized Subject Lines**: 4 variations per draft with company-specific messaging
- **Advanced Personalization**: 0-100 scoring based on customer data usage
- **Call-to-Action Optimization**: Automatic CTA extraction and optimization

**Draft Management:**
- **Comparison System**: Side-by-side draft analysis with recommendations
- **Version Control**: Track original drafts and all rewrites with history
- **Selection Algorithms**: Configurable criteria-based best draft selection
- **Customer Readiness**: Outreach readiness scoring with improvement recommendations

**Output:** Multiple personalized email drafts with management tools

### 5. Follow-up âœ…

**Purpose:** Context-aware follow-up sequences with interaction analysis

**Interaction Analysis:**
- **History Tracking**: Days since last interaction, total attempts, engagement patterns
- **Sentiment Detection**: Customer response analysis and engagement level scoring
- **Sequence Intelligence**: Automatic progression through follow-up stages
- **Respectful Limits**: Maximum 5 follow-ups with graceful closure handling

**Follow-up Strategies:**
- **Gentle Reminder** (1st): Friendly check-in with soft approach
- **Value-Add** (2nd): Industry insights, resources, and helpful information
- **Alternative Approach** (3rd): Different angle, case studies, social proof
- **Final Attempt** (4th): Respectful closure with future opportunity maintenance
- **Graceful Farewell** (5th): Professional relationship preservation

**Smart Features:**
- **Timing Intelligence**: Minimum 3-day intervals between follow-ups
- **Context Awareness**: References previous interactions appropriately
- **Engagement Adaptation**: Adjusts tone and approach based on customer behavior

**Output:** Context-aware follow-up emails with sequence management## ðŸ” M
anaging Multiple Sales Processes

When running multiple sales processes, use the querying tools:

```bash
# List all recent sales processes
python query_sales_processes.py --list

# Get complete details for a specific process
python query_sales_processes.py --details "fusesell_20251010_141010_3fe0e655"

# Find processes by customer name
python query_sales_processes.py --customer "Target Corp"

# Get specific stage results
python query_sales_processes.py --stage-result "task_id" "lead_scoring"
```

**ðŸ“š Complete querying guide: [QUERYING_GUIDE.md](QUERYING_GUIDE.md)**

## ðŸ“ Data Storage & Configuration

All data is stored locally in the `fusesell_data` directory with **100% server-compatible schema**:

```
fusesell_data/
â”œâ”€â”€ fusesell.db              # SQLite database
â”œâ”€â”€ config/                  # Configuration files
â”‚   â”œâ”€â”€ prompts.json        # LLM prompts
â”‚   â”œâ”€â”€ scoring_criteria.json
â”‚   â””â”€â”€ email_templates.json
â”œâ”€â”€ drafts/                 # Generated email drafts
â””â”€â”€ logs/                   # Execution logs
```

### Database Tables

- `executions` - Execution records and metadata
- `customers` - Customer profiles and information
- `lead_scores` - Lead scoring results and breakdowns
- `email_drafts` - Generated email drafts and variations
- `stage_results` - Intermediate results from each stage

### ðŸ—ï¸ Server-Compatible Database Schema

FuseSell Local uses **exact server table names** for seamless integration:

- **`llm_worker_task`**: Task management (matches server exactly)
- **`llm_worker_operation`**: Stage execution tracking (matches server exactly)
- **`gs_customer_llmtask`**: Customer data storage (matches server exactly)
- **`executions`**: Backward compatibility VIEW that maps to `llm_worker_task`

### Configuration Files

#### Custom Prompts (`config/prompts.json`)

Customize LLM prompts for different stages:

```json
{
  "data_preparation": {
    "customer_analysis": "Your custom prompt for customer analysis...",
    "pain_point_identification": "Your custom prompt for pain points..."
  },
  "lead_scoring": {
    "product_evaluation": "Your custom scoring prompt..."
  }
}
```

#### Scoring Criteria (`config/scoring_criteria.json`)

Customize lead scoring weights and criteria:

```json
{
  "criteria": {
    "industry_fit": { "weight": 25, "description": "Industry alignment" },
    "company_size": { "weight": 20, "description": "Company size fit" },
    "pain_points": { "weight": 30, "description": "Pain point match" },
    "technology": { "weight": 15, "description": "Technology compatibility" },
    "budget": { "weight": 10, "description": "Budget indicators" }
  }
}
```

## ðŸŽ¯ Key Features

### âœ… Complete AI-Powered Sales Automation

- **Multi-Source Data Collection**: Websites, business cards (OCR), LinkedIn, Facebook
- **AI Customer Profiling**: Pain point analysis, company research, financial assessment
- **Intelligent Lead Scoring**: Product-customer fit evaluation with detailed breakdowns
- **Personalized Email Generation**: 4 different approaches with subject line variations
- **Context-Aware Follow-ups**: Smart sequence management with interaction history analysis

### âœ… 100% Local Execution & Privacy

- **Complete Data Ownership**: All customer data stays on your machine
- **No External Dependencies**: Except OpenAI API for LLM processing
- **SQLite Database**: Local data storage with full CRUD operations
- **Event-Based Scheduling**: Database events for external app integration
- **Comprehensive Logging**: Detailed execution tracking and debugging

### âœ… Production-Ready Architecture

- **Action-Based Routing**: draft_write, draft_rewrite, send, close operations
- **Error Handling**: Graceful degradation with fallback templates
- **Draft Management**: Comparison, versioning, and selection utilities
- **Timezone Intelligence**: Optimal email timing with business hours respect
- **Extensible Design**: Easy customization and integration

### âœ… Advanced Intelligence Features

- **Personalization Scoring**: 0-100 scoring based on customer data usage
- **Engagement Analysis**: Customer interaction patterns and sentiment detection
- **Readiness Assessment**: Outreach readiness scoring with recommendations
- **Sequence Management**: Automatic follow-up progression (1st â†’ 2nd â†’ 3rd â†’ final)
- **Respectful Automation**: Smart limits and graceful closure handling## ðŸ› ï¸ Trou
bleshooting

### Common Issues

#### 1. "No such file or directory: requirements.txt"

**Solution:** Make sure you're in the `fusesell-local` directory:

```bash
cd fusesell-local
pip install -r requirements.txt
```

#### 2. "OpenAI API key not provided"

**Solution:** Ensure your API key is correct and has sufficient credits:

```bash
python fusesell.py --openai-api-key "sk-proj-your-actual-key" ...
```

#### 3. "No data could be collected from any source"

**Solution:** Ensure the website URL is accessible and valid:

```bash
# Test with a known working website
python fusesell.py ... --input-website "https://google.com" --dry-run
```

#### 4. "Permission denied" errors

**Solution:** Use user installation or virtual environment:

```bash
pip install --user -r requirements.txt
# OR
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Debug Mode

Enable detailed logging to troubleshoot issues:

```bash
python fusesell.py \
  --openai-api-key "sk-proj-abc123" \
  --org-id "test" \
  --org-name "Test Company" \
  --input-website "https://example.com" \
  --log-level DEBUG \
  --dry-run
```

### Dry Run Testing

Test the system without making API calls:

```bash
python fusesell.py \
  --openai-api-key "test-key" \
  --org-id "test" \
  --org-name "Test Company" \
  --input-website "https://example.com" \
  --dry-run
```

**ðŸ“š Complete troubleshooting guide: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

## ðŸ† Production Status

**FuseSell Local is 100% complete and production-ready!**

### âœ… All Components Complete:

- **CLI Interface**: 25+ configuration options with comprehensive validation
- **Pipeline Engine**: Complete 5-stage orchestration with business logic
- **Data Layer**: SQLite database with full CRUD operations and event scheduling
- **AI Integration**: OpenAI GPT-4o-mini with structured response parsing
- **Stage Implementations**: All 5 stages production-ready (7,400+ lines of code)
- **Documentation**: Complete user guides, technical docs, and troubleshooting

### âœ… Stage Implementation Status:

| Stage                | Status      | Lines  | Key Features                                   |
| -------------------- | ----------- | ------ | ---------------------------------------------- |
| **Data Acquisition** | âœ… Complete | 1,422  | Multi-source extraction, OCR, social media     |
| **Data Preparation** | âœ… Complete | 1,201  | AI profiling, pain point analysis              |
| **Lead Scoring**     | âœ… Complete | 1,426  | Product-customer fit evaluation                |
| **Initial Outreach** | âœ… Complete | 1,600+ | Intelligent email generation, draft management |
| **Follow-up**        | âœ… Complete | 1,800+ | Context-aware sequences, interaction analysis  |

## ðŸ“ Directory Structure

```
fusesell-local/
â”œâ”€â”€ fusesell.py                 # Main CLI entry point
â”œâ”€â”€ requirements.txt            # Python dependencies
â”œâ”€â”€ README.md                   # This file
â”œâ”€â”€ fusesell_local/            # Main package
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ pipeline.py            # Pipeline orchestrator
â”‚   â”œâ”€â”€ stages/                # Pipeline stages
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”œâ”€â”€ base_stage.py      # Base stage interface
â”‚   â”‚   â”œâ”€â”€ data_acquisition.py
â”‚   â”‚   â”œâ”€â”€ data_preparation.py
â”‚   â”‚   â”œâ”€â”€ lead_scoring.py
â”‚   â”‚   â”œâ”€â”€ initial_outreach.py
â”‚   â”‚   â””â”€â”€ follow_up.py
â”‚   â”œâ”€â”€ utils/                 # Utilities
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”œâ”€â”€ data_manager.py    # SQLite database manager
â”‚   â”‚   â”œâ”€â”€ llm_client.py      # OpenAI API client
â”‚   â”‚   â”œâ”€â”€ validators.py      # Input validation
â”‚   â”‚   â””â”€â”€ logger.py          # Logging configuration
â”‚   â””â”€â”€ config/                # Configuration
â”‚       â””â”€â”€ __init__.py
â””â”€â”€ fusesell_data/             # Local data storage
    â”œâ”€â”€ config/                # Configuration files
    â”‚   â”œâ”€â”€ prompts.json       # LLM prompts
    â”‚   â”œâ”€â”€ scoring_criteria.json
    â”‚   â””â”€â”€ email_templates.json
    â”œâ”€â”€ drafts/                # Generated email drafts
    â””â”€â”€ logs/                  # Execution logs
```

## ðŸ”’ Security & Privacy

- **Complete data ownership**: All customer data stays on your machine
- **API key security**: Keys are only used for LLM calls, never stored
- **Input validation**: Prevents injection attacks and validates all inputs
- **Local processing**: No external dependencies except for LLM API calls

## ðŸ“š Additional Documentation

### User Documentation
- **[QUERYING_GUIDE.md](QUERYING_GUIDE.md)** - Managing multiple sales processes
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

### Developer Documentation
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Customization and extension guide
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Technical API reference
- **[TECHNICAL.md](TECHNICAL.md)** - Architecture and technical details
- **[DATABASE.md](DATABASE.md)** - Database schema reference

### Reference Documentation
- **[business_logic.md](business_logic.md)** - Business logic and orchestration rules
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates

## ðŸš€ Ready for Production Use

- **End-to-End Pipeline**: Complete sales automation workflow
- **Local Data Ownership**: Full privacy and control
- **AI-Powered Intelligence**: Personalized and context-aware
- **Integration Ready**: Database events for external app integration
- **Comprehensive Testing**: Dry-run mode and extensive error handling

## ðŸ’¡ Performance Tips

### 1. Use Dry Run for Testing

Always test with `--dry-run` first to validate your configuration.

### 2. Optimize API Usage

- Use appropriate `--llm-temperature` (0.2-0.8)
- Set reasonable `--llm-max-tokens` limits
- Consider stopping after specific stages for testing

### 3. Batch Processing

For multiple leads, use different `--execution-id` values:

```bash
python fusesell.py ... --execution-id "lead_001"
python fusesell.py ... --execution-id "lead_002"
```

### 4. Data Directory Management

Use custom data directories for different projects:

```bash
python fusesell.py ... --data-dir "./project_a_data"
python fusesell.py ... --data-dir "./project_b_data"
```

## ðŸ¤ Support

For issues, questions, or contributions:
- Check the troubleshooting guide for common issues
- Review the technical documentation for advanced usage
- Refer to the business logic documentation for workflow details
- Contact the development team for custom requirements

---

**FuseSell Local - Complete AI Sales Automation, 100% Local, 100% Private** ðŸš€
