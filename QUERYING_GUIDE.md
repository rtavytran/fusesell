# FuseSell Local - Sales Process Querying Guide

**Complete Guide to Querying and Managing Multiple Sales Processes**

##  Overview

FuseSell Local provides comprehensive querying capabilities using a **server-compatible schema** that tracks individual sales processes with detailed execution history. Each sales process is identified by a unique task ID and contains complete per-stage execution records with input/output data, making debugging and analysis much more powerful.

###  **Server-Compatible Schema Benefits:**

- **Per-Stage Tracking**: Individual operation records for each stage execution
- **Detailed Input/Output**: JSON data for each stage's input and output
- **Execution Indexing**: Proper runtime_index and chain_index tracking
- **100% Server Compatibility**: Uses exact server table names (`llm_worker_task`, `llm_worker_operation`, `gs_customer_llmtask`)
- **Enhanced Debugging**: Detailed failure analysis with exact error data
- **Backward Compatibility**: `executions` VIEW maps to `llm_worker_task` for existing queries

##  Quick Reference

### Essential Commands

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

##  Method 1: Using the Query Tool (Recommended)

### List Recent Sales Processes

```bash
# List 10 most recent processes
python query_sales_processes.py --list

# List 20 most recent processes
python query_sales_processes.py --list --limit 20

# List processes for specific organization
python query_sales_processes.py --list --org-id "mycompany"
```

**Output Example:**

```
 Recent Sales Processes:
================================================================================
1. Task ID: fusesell_20251010_141010_3fe0e655
   Customer: Customer: Target Corp, email: contact@targetcorp.com...
   Status: completed
   Runtime Index: 5
   Created: 2025-10-10 14:10:12

2. Task ID: fusesell_20251010_135358_5073d3e4
   Customer: Customer: Test Corp, email: test@testcorp.com...
   Status: completed
   Runtime Index: 2
   Created: 2025-10-10 13:53:58
```

### Find Processes by Customer

```bash
# Find all processes for a specific customer
python query_sales_processes.py --customer "Target Corp"
python query_sales_processes.py --customer "John Smith"
```

**Use Cases:**

- Track all interactions with a specific prospect
- Find previous outreach attempts
- Review customer engagement history

### Get Complete Process Details

```bash
# Get full details for a specific sales process
python query_sales_processes.py --details "fusesell_20251010_141010_3fe0e655"
```

**Output Includes:**

- **Task Information**: ID, organization, status, customer details
- **Stage Executions**: Which stages ran, success/failure status
- **Lead Scores**: Product evaluation results
- **Email Drafts**: Generated email content
- **Summary Statistics**: Completion rates, counts

**Example Output:**

```
 Sales Process Details: fusesell_20251010_141010_3fe0e655
================================================================================
 Task Information:
   Task ID: fusesell_20251010_141010_3fe0e655
   Organization: mycompany
   Status: completed
   Current Stage: 5
   Created: 2025-10-10 14:10:12
   Customer: Target Corp, email: contact@targetcorp.com
   Language: english

 Stage Executions:
    Data Acquisition (Runtime Index: 0)
      Status: success
      Executed: 2025-10-10 14:10:13

    Data Preparation (Runtime Index: 1)
      Status: success
      Executed: 2025-10-10 14:10:15

    Lead Scoring (Runtime Index: 2)
      Status: success
      Executed: 2025-10-10 14:10:18

    Initial Outreach (Runtime Index: 3)
      Status: success
      Executed: 2025-10-10 14:10:22

    Follow Up (Runtime Index: 4)
      Status: success
      Executed: 2025-10-10 14:10:25

 Summary:
   Total Stages: 5
   Completed: 5
   Failed: 0
   Lead Scores: 2
   Email Drafts: 4

 Lead Scores:
   Product: FuseSell AI Pro
   Score: 85.5
   Date: 2025-10-10 14:10:18

   Product: FuseSell Starter
   Score: 72.3
   Date: 2025-10-10 14:10:18

 Email Drafts:
   Draft ID: draft_001
   Subject: Streamline Your Sales Process with AI-Powered Automation
   Created: 2025-10-10 14:10:22
```

### Get Specific Stage Results

```bash
# Get detailed results for a specific stage
python query_sales_processes.py --stage-result "task_id" "data_acquisition"
python query_sales_processes.py --stage-result "task_id" "data_preparation"
python query_sales_processes.py --stage-result "task_id" "lead_scoring"
python query_sales_processes.py --stage-result "task_id" "initial_outreach"
python query_sales_processes.py --stage-result "task_id" "follow_up"
```

**Use Cases:**

- Debug stage failures
- Review AI-generated content
- Analyze scoring breakdowns
- Examine email draft variations

##  Method 2: Using the Data Manager API (Server-Compatible)

For programmatic access, use the new server-compatible Data Manager API:

```python
from fusesell_local.utils.data_manager import LocalDataManager

# Initialize data manager
dm = LocalDataManager('./fusesell_data')

#  Server-compatible task management
task_with_ops = dm.get_task_with_operations("fusesell_20251010_141010_3fe0e655")
print(f"Process status: {task_with_ops['status']}")
print(f"Operations completed: {task_with_ops['summary']['completed_operations']}")

#  Get all operations for a process (replaces stages)
operations = dm.get_operations_by_task("fusesell_20251010_141010_3fe0e655")
for operation in operations:
    print(f"Operation: {operation['executor_name']} - Status: {operation['execution_status']}")

#  Get execution timeline with proper indexing
timeline = dm.get_execution_timeline("fusesell_20251010_141010_3fe0e655")
for op in timeline:
    print(f"Runtime {op['runtime_index']}, Chain {op['chain_index']}: {op['executor_name']}")

#  Performance analysis
metrics = dm.get_stage_performance_metrics("data_acquisition", org_id="mycompany")
print(f"Success rate: {metrics['success_rate']:.1f}%")

#  Find failed operations for debugging
failed_ops = dm.find_failed_operations(org_id="mycompany", limit=5)
for op in failed_ops:
    print(f"Failed: {op['executor_name']} - {op['error_summary']}")

# Find processes by customer
processes = dm.find_sales_processes_by_customer("Target Corp")
for process in processes:
    print(f"Task ID: {process['task_id']} - Status: {process['status']}")

# List all tasks for an organization
tasks = dm.list_tasks(org_id="mycompany", limit=20)
for task in tasks:
    print(f"Task: {task['task_id']} - Created: {task['created_at']}")
```

##  Method 3: Direct Database Queries

For advanced users, query the SQLite database directly:

```python
import sqlite3
import json

conn = sqlite3.connect('./fusesell_data/fusesell.db')
cursor = conn.cursor()

# Get execution summary with stage counts
cursor.execute("""
    SELECT e.execution_id, e.org_id, e.customer_name, e.status, e.started_at,
           COUNT(sr.id) as total_stages,
           SUM(CASE WHEN sr.status = 'success' THEN 1 ELSE 0 END) as successful_stages
    FROM executions e
    LEFT JOIN stage_results sr ON e.execution_id = sr.execution_id
    WHERE e.org_id = -
    GROUP BY e.execution_id
    ORDER BY e.started_at DESC
    LIMIT 10
""", ("mycompany",))

for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"Customer: {row[2]}")
    print(f"Status: {row[3]}")
    print(f"Stages: {row[6]}/{row[5]}")
    print()

# Get lead scores for a specific process
cursor.execute("""
    SELECT product_id, score, criteria_breakdown, created_at
    FROM lead_scores
    WHERE execution_id = -
    ORDER BY score DESC
""", ("fusesell_20251010_141010_3fe0e655",))

for row in cursor.fetchall():
    print(f"Product: {row[0]}")
    print(f"Score: {row[1]}")
    print(f"Date: {row[3]}")

    # Parse criteria breakdown
    if row[2]:
        breakdown = json.loads(row[2])
        for criterion, details in breakdown.items():
            print(f"  {criterion}: {details.get('score', 'N/A')}")
    print()

# Get email drafts for a specific process
cursor.execute("""
    SELECT draft_id, subject, content, draft_type, created_at
    FROM email_drafts
    WHERE execution_id = -
    ORDER BY created_at
""", ("fusesell_20251010_141010_3fe0e655",))

for row in cursor.fetchall():
    print(f"Draft: {row[0]}")
    print(f"Type: {row[3]}")
    print(f"Subject: {row[1]}")
    print(f"Created: {row[4]}")
    print()

conn.close()
```

##  Key Database Tables (Server-Compatible Schema)

Understanding the new server-compatible schema:

###  **Primary Tables (Server Schema)**

- **`tasks`**: Sales process records (equivalent to server's llm_worker_task)
  - Contains: task_id, plan_id, org_id, status, current_runtime_index, request_body
- **`operations`**: Individual stage executions (equivalent to server's llm_worker_operation)
  - Contains: operation_id, task_id, executor_name, runtime_index, chain_index, execution_status, input_data, output_data

###  **Results Tables**

- **`lead_scores`**: Product evaluation scores and breakdowns
- **`email_drafts`**: Generated email content and variations
- **`customers`**: Customer profile information
- **`customer_tasks`**: Customer task data (equivalent to server's gs_customer_llmtask)

###  **Configuration Tables**

- **`team_settings`**: Team-specific configurations
- **`products`**: Available products for evaluation
- **`gs_company_criteria`**: Scoring criteria definitions
- **`llm_worker_plan`**: Workflow plan definitions

###  **Backward Compatibility**

- **`executions`**: Legacy execution records (maintained for compatibility)
- **`stage_results`**: Legacy stage results (maintained for compatibility)
- **Compatibility views**: Automatically map old queries to new schema

##  Common Query Patterns

### Find Failed Processes

```bash
# Using query tool (filter manually from --list output)
python query_sales_processes.py --list

# Using SQL
SELECT execution_id, customer_name, started_at
FROM executions
WHERE status = 'failed'
ORDER BY started_at DESC;
```

### Find High-Scoring Leads

```sql
SELECT e.execution_id, e.customer_name, ls.product_id, ls.score
FROM executions e
JOIN lead_scores ls ON e.execution_id = ls.execution_id
WHERE ls.score > 80
ORDER BY ls.score DESC;
```

### Find Recent Email Drafts

```sql
SELECT e.customer_name, ed.subject, ed.draft_type, ed.created_at
FROM executions e
JOIN email_drafts ed ON e.execution_id = ed.execution_id
WHERE ed.created_at > datetime('now', '-7 days')
ORDER BY ed.created_at DESC;
```

### Track Customer Engagement

```bash
# Find all processes for a customer
python query_sales_processes.py --customer "Target Corp"

# Get detailed history
python query_sales_processes.py --details "task_id_1"
python query_sales_processes.py --details "task_id_2"
```

##  Monitoring and Analytics

### Process Success Rates

```sql
SELECT
    org_id,
    COUNT(*) as total_processes,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    ROUND(
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) as success_rate
FROM executions
GROUP BY org_id;
```

### Average Lead Scores by Product

```sql
SELECT
    product_id,
    COUNT(*) as evaluations,
    ROUND(AVG(score), 2) as avg_score,
    MIN(score) as min_score,
    MAX(score) as max_score
FROM lead_scores
GROUP BY product_id
ORDER BY avg_score DESC;
```

### Stage Performance Analysis

```sql
SELECT
    stage_name,
    COUNT(*) as total_executions,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    ROUND(
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) as success_rate
FROM stage_results
GROUP BY stage_name
ORDER BY success_rate DESC;
```

##  Best Practices

### 1. Use Task IDs for Unique Identification

Task IDs like `fusesell_20251010_141010_3fe0e655` uniquely identify each sales process:

- Format: `fusesell_YYYYMMDD_HHMMSS_randomhex`
- Always use the complete task ID for queries
- Task IDs are consistent across all tables

### 2. Filter by Organization

When working with multiple organizations:

```bash
python query_sales_processes.py --list --org-id "mycompany"
```

### 3. Regular Monitoring

Set up regular checks for:

- Failed processes that need attention
- High-scoring leads for immediate follow-up
- Email drafts ready for review and sending

### 4. Data Retention

Consider implementing data retention policies:

- Archive old processes after a certain period
- Keep high-value leads for longer analysis
- Backup important customer data

##  Troubleshooting

### Common Issues

**"No sales processes found"**

- Check if you're in the correct data directory
- Verify the database file exists: `./fusesell_data/fusesell.db`
- Ensure processes have been run successfully

**"Task not found"**

- Verify the task ID is correct and complete
- Check if the task belongs to the expected organization
- Use `--list` to see available task IDs

**"Stage not found"**

- Use exact stage names: `data_acquisition`, `data_preparation`, `lead_scoring`, `initial_outreach`, `follow_up`
- Check if the stage actually executed for that task

### Debug Commands

```bash
# Verify database exists and has data
python -c "
import sqlite3
conn = sqlite3.connect('./fusesell_data/fusesell.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM executions')
print(f'Total executions: {cursor.fetchone()[0]}')
conn.close()
"

# Check recent activity
python query_sales_processes.py --list --limit 5
```

##  Server-Compatible Database Schema

FuseSell Local now uses **100% server-compatible table names** for seamless integration:

### Core Execution Tables

| Table Name | Purpose | Server Compatibility |
|------------|---------|---------------------|
| `llm_worker_task` | Task management and process tracking |  **Exact server match** |
| `llm_worker_operation` | Individual stage execution records |  **Exact server match** |
| `gs_customer_llmtask` | Customer data storage |  **Exact server match** |
| `executions` (VIEW) | Backward compatibility mapping |  **Maps to llm_worker_task** |

### Schema Benefits

- **Direct Server Integration**: Tables can be synchronized with server without schema conversion
- **Enhanced Debugging**: Per-stage operation tracking with input/output JSON data
- **Performance Analysis**: Stage-specific success rates and execution metrics
- **Backward Compatibility**: Existing queries continue to work via `executions` VIEW

### Advanced Querying

For direct database access, you can now query server-compatible tables:

```sql
-- Query tasks (sales processes)
SELECT task_id, org_id, status, current_runtime_index 
FROM llm_worker_task 
WHERE org_id = 'mycompany' 
ORDER BY created_at DESC;

-- Query operations (stage executions)
SELECT operation_id, executor_name, execution_status, runtime_index
FROM llm_worker_operation 
WHERE task_id = 'fusesell_20251010_141010_3fe0e655'
ORDER BY chain_index;

-- Query customer data
SELECT task_id, customer_name, customer_email, org_id
FROM gs_customer_llmtask
WHERE org_id = 'mycompany';
```

##  Related Documentation

- **[README.md](README.md)**: Main usage guide and installation
- **[VERIFICATION_REPORT.md](VERIFICATION_REPORT.md)**: Server schema compliance verification
- **[DATABASE.md](DATABASE.md)**: Complete database schema reference
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)**: Data Manager API reference
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**: Common issues and solutions

---

**Need Help-**

- Check the troubleshooting section above
- Review the server schema compliance in `VERIFICATION_REPORT.md`
- Use `python query_sales_processes.py --help` for command reference
