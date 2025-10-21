# FuseSell Local - Database Documentation

## Overview

FuseSell Local uses a single SQLite database file (`fusesell_data/fusesell.db`) with 12 normalized tables to store all execution data, customer profiles, scoring results, email drafts, tasks, teams, products, and configuration settings.

## Database Location

```
fusesell_data/
└── fusesell.db          # Single SQLite file containing all tables
```

## Complete Database Schema

### 1. **executions** Table - Main Execution Tracking

**Purpose**: Track pipeline executions, their status, and configuration

```sql
CREATE TABLE executions (
    execution_id TEXT PRIMARY KEY,           -- Unique execution identifier (e.g., "fusesell_20241006_123456_abc123")
    org_id TEXT NOT NULL,                   -- Organization ID (e.g., "rta")
    org_name TEXT,                          -- Organization name (e.g., "RTA Corp")
    customer_website TEXT,                  -- Customer website URL
    customer_name TEXT,                     -- Customer company name
    status TEXT NOT NULL,                   -- Execution status: "running", "completed", "failed", "stopped"
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    config_json TEXT,                       -- Full execution configuration as JSON
    results_json TEXT                       -- Final execution results as JSON
);
```

**Data Stored**:
- Execution metadata and tracking
- Complete configuration used for the run
- Final aggregated results
- Timing and status information

### 2. **stage_results** Table - Individual Stage Outputs

**Purpose**: Store results from each pipeline stage execution

```sql
CREATE TABLE stage_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,             -- Links to executions.execution_id
    stage_name TEXT NOT NULL,               -- Stage name: "data_acquisition", "data_preparation", "lead_scoring", "initial_outreach", "follow_up"
    status TEXT NOT NULL,                   -- Stage status: "success", "failed", "skipped"
    input_data TEXT,                        -- Stage input data as JSON
    output_data TEXT,                       -- Stage output data as JSON
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,                     -- Error details if stage failed
    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
);
```

**Data Stored**:
- Individual stage execution results
- Input and output data for each stage
- Error messages and debugging information
- Stage timing and performance data

### 3. **customers** Table - Customer Profile Data

**Purpose**: Store structured customer information and profiles

```sql
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,           -- Unique customer identifier
    org_id TEXT NOT NULL,                   -- Organization ID
    company_name TEXT,                      -- Customer company name
    website TEXT,                           -- Customer website
    industry TEXT,                          -- Customer industry
    contact_name TEXT,                      -- Primary contact name
    contact_email TEXT,                     -- Primary contact email
    contact_phone TEXT,                     -- Primary contact phone
    address TEXT,                           -- Customer address
    profile_data TEXT,                      -- Full customer profile as JSON (pain points, tech stack, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored**:
- Basic customer contact information
- Company details and industry classification
- Rich profile data from AI analysis
- Pain points, technology stack, financial info

### 4. **lead_scores** Table - Scoring Results

**Purpose**: Store lead scoring results and detailed breakdowns

```sql
CREATE TABLE lead_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,             -- Links to executions.execution_id
    customer_id TEXT,                       -- Links to customers.customer_id
    product_id TEXT,                        -- Product being scored against
    score REAL,                             -- Numerical score (0-100)
    criteria_breakdown TEXT,                -- Detailed scoring breakdown as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
);
```

**Data Stored**:
- Overall lead scores for customer-product fit
- Detailed scoring criteria breakdowns
- Product-specific scoring results
- Recommendations and next steps

### 5. **email_drafts** Table - Generated Email Content

**Purpose**: Store generated email drafts and versions

```sql
CREATE TABLE email_drafts (
    draft_id TEXT PRIMARY KEY,              -- Unique draft identifier
    execution_id TEXT NOT NULL,             -- Links to executions.execution_id
    customer_id TEXT,                       -- Links to customers.customer_id
    subject TEXT,                           -- Email subject line
    content TEXT,                           -- Email body content
    draft_type TEXT,                        -- Draft type: "initial", "follow_up", "rewrite"
    version INTEGER DEFAULT 1,              -- Draft version number
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
);
```

**Data Stored**:
- Email subject lines and content
- Multiple draft variations
- Draft versioning for rewrites
- Draft type classification

## Performance Indexes

```sql
-- Optimize queries by organization
CREATE INDEX idx_executions_org_id ON executions(org_id);
CREATE INDEX idx_customers_org_id ON customers(org_id);

-- Optimize queries by execution
CREATE INDEX idx_stage_results_execution_id ON stage_results(execution_id);
CREATE INDEX idx_lead_scores_execution_id ON lead_scores(execution_id);
CREATE INDEX idx_email_drafts_execution_id ON email_drafts(execution_id);
```

## Data Relationships

```
executions (1) ──────── (many) stage_results
    │
    ├─────────── (many) lead_scores
    │
    └─────────── (many) email_drafts

customers (1) ────────── (many) lead_scores
    │
    └─────────── (many) email_drafts
```

## Data Flow by Stage

### **Data Acquisition Stage**
- **Input**: Customer website, business card, social media URLs
- **Output**: Raw customer data
- **Storage**: `stage_results.output_data` (JSON)

### **Data Preparation Stage**
- **Input**: Raw customer data from previous stage
- **Output**: Structured customer profile
- **Storage**: `customers` table + `stage_results.output_data`

### **Lead Scoring Stage**
- **Input**: Structured customer profile
- **Output**: Lead scores and recommendations
- **Storage**: `lead_scores` table + `stage_results.output_data`

### **Initial Outreach Stage**
- **Input**: Customer profile and lead scores
- **Output**: Email drafts
- **Storage**: `email_drafts` table + `stage_results.output_data`

### **Follow-up Stage**
- **Input**: Previous interaction history
- **Output**: Follow-up email drafts
- **Storage**: `email_drafts` table (new versions) + `stage_results.output_data`

## Query Examples

### Get All Executions for an Organization
```sql
SELECT * FROM executions 
WHERE org_id = 'rta' 
ORDER BY started_at DESC;
```

### Get Complete Execution Details
```sql
SELECT 
    e.execution_id,
    e.status,
    e.customer_name,
    sr.stage_name,
    sr.status as stage_status
FROM executions e
LEFT JOIN stage_results sr ON e.execution_id = sr.execution_id
WHERE e.execution_id = 'fusesell_20241006_123456_abc123'
ORDER BY sr.started_at;
```

### Get Customer Profile with Latest Scores
```sql
SELECT 
    c.company_name,
    c.contact_name,
    c.contact_email,
    ls.score,
    ls.criteria_breakdown
FROM customers c
LEFT JOIN lead_scores ls ON c.customer_id = ls.customer_id
WHERE c.org_id = 'rta'
ORDER BY ls.created_at DESC;
```

### Get Email Drafts for Customer
```sql
SELECT 
    ed.subject,
    ed.content,
    ed.draft_type,
    ed.version,
    ed.created_at
FROM email_drafts ed
JOIN customers c ON ed.customer_id = c.customer_id
WHERE c.company_name = 'Acme Inc'
ORDER BY ed.created_at DESC;
```

## Data Management Operations

### Backup Database
```bash
# Copy the entire database file
cp fusesell_data/fusesell.db fusesell_data/backup_$(date +%Y%m%d).db
```

### Export Data
```sql
-- Export executions to CSV
.mode csv
.output executions_export.csv
SELECT * FROM executions;
```

### Clean Old Data
```sql
-- Delete executions older than 90 days
DELETE FROM executions 
WHERE started_at < datetime('now', '-90 days');

-- This will cascade delete related records due to foreign keys
```

## Database Maintenance

### Regular Maintenance Tasks
1. **Vacuum**: Reclaim space from deleted records
   ```sql
   VACUUM;
   ```

2. **Analyze**: Update query optimizer statistics
   ```sql
   ANALYZE;
   ```

3. **Integrity Check**: Verify database consistency
   ```sql
   PRAGMA integrity_check;
   ```

### Monitoring Database Size
```sql
-- Check database size and table statistics
SELECT 
    name,
    COUNT(*) as record_count
FROM sqlite_master sm
JOIN (
    SELECT 'executions' as name, COUNT(*) as cnt FROM executions
    UNION ALL
    SELECT 'stage_results', COUNT(*) FROM stage_results
    UNION ALL
    SELECT 'customers', COUNT(*) FROM customers
    UNION ALL
    SELECT 'lead_scores', COUNT(*) FROM lead_scores
    UNION ALL
    SELECT 'email_drafts', COUNT(*) FROM email_drafts
) counts ON sm.name = counts.name
WHERE sm.type = 'table';
```

## Security Considerations

### Data Protection
- Database file permissions: `600` (owner read/write only)
- No sensitive API keys stored in database
- Customer data encrypted at rest (OS-level encryption recommended)

### Access Control
- Single-user local access only
- No network access to database
- Application-level validation prevents SQL injection

### Privacy Compliance
- All customer data stored locally
- No external data transmission except LLM API calls
- Complete data ownership and control
- Easy data deletion and export for compliance

## Troubleshooting

### Common Issues

1. **Database Locked Error**
   - Cause: Another process accessing the database
   - Solution: Ensure only one FuseSell instance running

2. **Disk Space Issues**
   - Cause: Database file growing too large
   - Solution: Regular cleanup of old executions

3. **Corruption Issues**
   - Cause: Unexpected shutdown during write operations
   - Solution: Restore from backup, run integrity check

### Recovery Procedures

1. **Backup Restoration**
   ```bash
   cp fusesell_data/backup_YYYYMMDD.db fusesell_data/fusesell.db
   ```

2. **Schema Recreation**
   ```bash
   # Delete corrupted database
   rm fusesell_data/fusesell.db
   
   # Run FuseSell to recreate schema
   python fusesell.py --dry-run [other args]
   ```

This documentation provides complete details on the database structure, data storage patterns, and management procedures for FuseSell Local.
#
## 6. **tasks** Table - Task Management (equivalent to llm_worker_task)

**Purpose**: Store task definitions and metadata for sales processes

```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,               -- Unique task identifier
    plan_id TEXT NOT NULL,                  -- Plan/workflow identifier
    org_id TEXT NOT NULL,                   -- Organization ID
    status TEXT NOT NULL,                   -- Task status (draft, running, completed, failed)
    current_runtime_index INTEGER DEFAULT 0, -- Current execution step
    messages TEXT,                          -- Task messages as JSON
    request_body TEXT,                      -- Original request data as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored**:
- Task definitions and workflow metadata
- Current execution state and progress
- Original request parameters
- Task status and lifecycle tracking

### 7. **operations** Table - Operation Executions (equivalent to llm_worker_operation)

**Purpose**: Store individual operation executions within tasks

```sql
CREATE TABLE operations (
    operation_id TEXT PRIMARY KEY,          -- Unique operation identifier
    task_id TEXT NOT NULL,                  -- Links to tasks table
    executor_id TEXT,                       -- Executor/stage identifier
    chain_order INTEGER NOT NULL,          -- Order in execution chain
    chain_index INTEGER NOT NULL,          -- Chain index
    runtime_index INTEGER NOT NULL,        -- Runtime execution index
    item_index INTEGER NOT NULL,           -- Item index
    execution_status TEXT NOT NULL,        -- Operation status (done, failed, pending)
    input_data TEXT,                        -- Operation input as JSON
    output_data TEXT,                       -- Operation output as JSON
    payload TEXT,                           -- Operation payload as JSON
    user_messages TEXT,                     -- User messages as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

**Data Stored**:
- Individual operation executions within tasks
- Execution chain and ordering information
- Operation input/output data
- User interactions and messages

### 8. **teams** Table - Team Management (equivalent to llm_worker_plan_team)

**Purpose**: Store team configurations and settings

```sql
CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,              -- Unique team identifier
    org_id TEXT NOT NULL,                  -- Organization ID
    org_name TEXT,                         -- Organization name
    plan_id TEXT NOT NULL,                 -- Plan identifier
    plan_name TEXT,                        -- Plan name
    project_code TEXT,                     -- Project code
    name TEXT NOT NULL,                    -- Team name
    description TEXT,                      -- Team description
    avatar TEXT,                           -- Team avatar URL
    completed_settings INTEGER DEFAULT 0,  -- Number of completed settings
    total_settings INTEGER DEFAULT 0,      -- Total number of settings
    completed_settings_list TEXT,          -- Completed settings as JSON
    missing_settings_list TEXT,            -- Missing settings as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored**:
- Team metadata and configuration
- Settings completion tracking
- Team branding and description
- Plan and project associations

### 9. **team_settings** Table - Team Configuration (equivalent to gs_team_settings)

**Purpose**: Store detailed team settings and configurations

```sql
CREATE TABLE team_settings (
    id TEXT PRIMARY KEY,                    -- Unique settings identifier
    team_id TEXT NOT NULL,                 -- Links to teams table
    org_id TEXT NOT NULL,                  -- Organization ID
    plan_id TEXT NOT NULL,                 -- Plan identifier
    plan_name TEXT,                        -- Plan name
    project_code TEXT,                     -- Project code
    team_name TEXT,                        -- Team name
    organization_settings TEXT,            -- Organization settings as JSON
    sales_rep_settings TEXT,               -- Sales rep settings as JSON
    product_settings TEXT,                 -- Product settings as JSON
    schedule_time_settings TEXT,           -- Schedule settings as JSON
    initial_outreach_settings TEXT,        -- Initial outreach settings as JSON
    follow_up_settings TEXT,               -- Follow-up settings as JSON
    auto_interaction_settings TEXT,        -- Auto interaction settings as JSON
    followup_schedule_settings TEXT,       -- Follow-up schedule settings as JSON
    birthday_email_settings TEXT,          -- Birthday email settings as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
```

**Data Stored**:
- Comprehensive team configuration settings
- Stage-specific settings (outreach, follow-up, etc.)
- Scheduling and automation rules
- Sales representative information

### 10. **products** Table - Product Catalog (equivalent to sell_products)

**Purpose**: Store product information for lead scoring and outreach

```sql
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,           -- Unique product identifier
    org_id TEXT NOT NULL,                  -- Organization ID
    org_name TEXT,                         -- Organization name
    project_code TEXT,                     -- Project code
    product_name TEXT NOT NULL,            -- Product name
    short_description TEXT,                -- Brief product description
    long_description TEXT,                 -- Detailed product description
    category TEXT,                         -- Product category
    subcategory TEXT,                      -- Product subcategory
    target_users TEXT,                     -- Target users as JSON
    key_features TEXT,                     -- Key features as JSON
    unique_selling_points TEXT,            -- USPs as JSON
    pain_points_solved TEXT,               -- Pain points addressed as JSON
    competitive_advantages TEXT,           -- Competitive advantages as JSON
    pricing TEXT,                          -- Pricing information as JSON
    pricing_rules TEXT,                    -- Pricing rules as JSON
    product_website TEXT,                  -- Product website URL
    demo_available BOOLEAN DEFAULT FALSE,  -- Demo availability
    trial_available BOOLEAN DEFAULT FALSE, -- Trial availability
    sales_contact_email TEXT,              -- Sales contact email
    image_url TEXT,                        -- Product image URL
    sales_metrics TEXT,                    -- Sales metrics as JSON
    customer_feedback TEXT,                -- Customer feedback as JSON
    keywords TEXT,                         -- Keywords as JSON
    related_products TEXT,                 -- Related products as JSON
    seasonal_demand TEXT,                  -- Seasonal demand as JSON
    market_insights TEXT,                  -- Market insights as JSON
    case_studies TEXT,                     -- Case studies as JSON
    testimonials TEXT,                     -- Testimonials as JSON
    success_metrics TEXT,                  -- Success metrics as JSON
    product_variants TEXT,                 -- Product variants as JSON
    availability TEXT,                     -- Availability status
    technical_specifications TEXT,         -- Technical specs as JSON
    compatibility TEXT,                    -- Compatibility info as JSON
    support_info TEXT,                     -- Support information as JSON
    regulatory_compliance TEXT,            -- Compliance info as JSON
    localization TEXT,                     -- Localization info as JSON
    installation_requirements TEXT,        -- Installation requirements
    user_manual_url TEXT,                  -- User manual URL
    return_policy TEXT,                    -- Return policy
    shipping_info TEXT,                    -- Shipping info as JSON
    schema_version TEXT DEFAULT '1.3',     -- Schema version
    status TEXT DEFAULT 'active',          -- Product status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored**:
- Complete product catalog information
- Marketing and sales materials
- Technical specifications and compatibility
- Pricing and availability information

### 11. **customer_tasks** Table - Customer Task Mapping (equivalent to gs_customer_llmtask)

**Purpose**: Link customers to specific tasks and store customer context

```sql
CREATE TABLE customer_tasks (
    id TEXT PRIMARY KEY,                    -- Unique record identifier
    task_id TEXT NOT NULL,                 -- Links to tasks table
    customer_id TEXT NOT NULL,             -- Links to customers table
    customer_name TEXT NOT NULL,           -- Customer company name
    customer_phone TEXT,                   -- Customer phone
    customer_address TEXT,                 -- Customer address
    customer_email TEXT,                   -- Customer email
    customer_industry TEXT,                -- Customer industry
    customer_taxcode TEXT,                 -- Customer tax code
    customer_website TEXT,                 -- Customer website
    contact_name TEXT,                     -- Primary contact name
    org_id TEXT NOT NULL,                  -- Organization ID
    org_name TEXT,                         -- Organization name
    project_code TEXT,                     -- Project code
    crm_dob DATE,                          -- CRM date of birth
    image_url TEXT,                        -- Customer image URL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
```

**Data Stored**:
- Customer-task relationships
- Customer contact information
- CRM integration data
- Task-specific customer context

### 12. **prompts** Table - Prompt Management (equivalent to gs_plan_team_prompt)

**Purpose**: Store LLM prompts for different stages and teams

```sql
CREATE TABLE prompts (
    id TEXT PRIMARY KEY,                    -- Unique prompt identifier
    execution_id TEXT,                     -- Execution identifier
    org_id TEXT NOT NULL,                  -- Organization ID
    plan_id TEXT,                          -- Plan identifier
    team_id TEXT,                          -- Team identifier
    project_code TEXT,                     -- Project code
    input_stage TEXT NOT NULL,             -- Stage name (data_acquisition, etc.)
    prompt TEXT NOT NULL,                  -- Prompt content
    fewshots BOOLEAN DEFAULT FALSE,        -- Whether prompt includes few-shot examples
    instance_id TEXT,                      -- Instance identifier
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retrieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored**:
- LLM prompts for each pipeline stage
- Team-specific prompt customizations
- Prompt versioning and tracking
- Few-shot example configurations

### 13. **scheduler_rules** Table - Scheduling Rules (equivalent to gs_scheduler)

**Purpose**: Store scheduling rules and timing configurations

```sql
CREATE TABLE scheduler_rules (
    id TEXT PRIMARY KEY,                    -- Unique rule identifier
    org_id TEXT NOT NULL,                  -- Organization ID
    org_name TEXT,                         -- Organization name
    plan_id TEXT,                          -- Plan identifier
    plan_name TEXT,                        -- Plan name
    team_id TEXT,                          -- Team identifier
    team_name TEXT,                        -- Team name
    project_code TEXT,                     -- Project code
    input_stage TEXT NOT NULL,             -- Stage for scheduling
    input_stage_label TEXT,                -- Stage label
    language TEXT,                         -- Language setting
    rule_config TEXT,                      -- Rule configuration as JSON
    is_autorun_time_rule BOOLEAN DEFAULT FALSE, -- Auto-run flag
    status_code INTEGER,                   -- Status code
    message TEXT,                          -- Status message
    md_code TEXT,                          -- MD code
    username TEXT,                         -- Username
    fullname TEXT,                         -- Full name
    instance_id TEXT,                      -- Instance identifier
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored**:
- Email sending schedules and timing rules
- Time zone and office hours configurations
- Automated scheduling preferences
- User-specific scheduling settings

### 14. **extracted_files** Table - File Extraction Data (equivalent to gs_plan_setting_extracted_file)

**Purpose**: Store extracted data from uploaded files

```sql
CREATE TABLE extracted_files (
    id TEXT PRIMARY KEY,                    -- Unique record identifier
    org_id TEXT NOT NULL,                  -- Organization ID
    plan_id TEXT,                          -- Plan identifier
    team_id TEXT,                          -- Team identifier
    project_code TEXT,                     -- Project code
    import_uuid TEXT,                      -- Import UUID
    file_url TEXT,                         -- File URL
    project_url TEXT,                      -- Project URL
    extracted_data TEXT,                   -- Extracted data as JSON
    username TEXT,                         -- Username
    fullname TEXT,                         -- Full name
    instance_id TEXT,                      -- Instance identifier
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retrieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored**:
- OCR and file extraction results
- Business card and document processing
- File upload metadata and tracking
- Extracted content analysis

## Updated Data Relationships

```
executions (1) ──────── (many) stage_results
    │
    ├─────────── (many) lead_scores
    │
    └─────────── (many) email_drafts

customers (1) ────────── (many) lead_scores
    │
    ├─────────── (many) email_drafts
    │
    └─────────── (many) customer_tasks

tasks (1) ──────────── (many) operations
    │
    └─────────── (many) customer_tasks

teams (1) ──────────── (1) team_settings
    │
    └─────────── (many) prompts

products (many) ──────── (many) lead_scores (via product_id)

scheduler_rules (many) ── (1) teams (via team_id)

extracted_files (many) ── (1) teams (via team_id)
```

## Complete Data Storage Strategy

| **Data Type** | **Table** | **Purpose** |
|---------------|-----------|-------------|
| **Pipeline Execution** | `executions` | Track pipeline runs, status, configuration |
| **Stage Results** | `stage_results` | Store individual stage results and errors |
| **Customer Data** | `customers` | Structured customer information and profiles |
| **Lead Scoring** | `lead_scores` | Scoring results and detailed breakdowns |
| **Email Content** | `email_drafts` | Generated email drafts and versions |
| **Task Management** | `tasks` | Sales process tasks and workflow tracking |
| **Operations** | `operations` | Individual operation executions within tasks |
| **Team Management** | `teams` | Team configurations and metadata |
| **Team Settings** | `team_settings` | Detailed team configuration settings |
| **Product Catalog** | `products` | Product information for scoring and outreach |
| **Customer Tasks** | `customer_tasks` | Link customers to specific tasks |
| **Prompt Library** | `prompts` | LLM prompts for different stages and teams |
| **Scheduling** | `scheduler_rules` | Timing and scheduling configurations |
| **File Processing** | `extracted_files` | Data extracted from uploaded files |

## Updated Performance Indexes

```sql
-- Core execution indexes
CREATE INDEX idx_executions_org_id ON executions(org_id);
CREATE INDEX idx_stage_results_execution_id ON stage_results(execution_id);
CREATE INDEX idx_customers_org_id ON customers(org_id);
CREATE INDEX idx_lead_scores_execution_id ON lead_scores(execution_id);
CREATE INDEX idx_email_drafts_execution_id ON email_drafts(execution_id);

-- Task management indexes
CREATE INDEX idx_tasks_org_id ON tasks(org_id);
CREATE INDEX idx_operations_task_id ON operations(task_id);

-- Team and configuration indexes
CREATE INDEX idx_teams_org_id ON teams(org_id);
CREATE INDEX idx_team_settings_team_id ON team_settings(team_id);
CREATE INDEX idx_products_org_id ON products(org_id);

-- Customer and prompt indexes
CREATE INDEX idx_customer_tasks_task_id ON customer_tasks(task_id);
CREATE INDEX idx_prompts_org_id ON prompts(org_id);
CREATE INDEX idx_scheduler_rules_org_id ON scheduler_rules(org_id);
CREATE INDEX idx_extracted_files_org_id ON extracted_files(org_id);
```

This comprehensive database schema now matches the original server-based system and provides complete data storage for all FuseSell functionality including tasks, teams, products, settings, prompts, scheduling, and file processing.