# FuseSell Business Logic & Orchestration Rules

## Overview

This document captures the business logic and orchestration rules from the original server-based FuseSell system. It defines when each stage should run, what conditions trigger specific actions, and how the pipeline should behave in different scenarios.

## System Prompt (LLM Planner Logic)

The original system uses an LLM planner with this core prompt:

```
You are the best task planner. You are good at choose the correct executors in AVAILABLE EXECUTORS list to progress the task until complete.

When receive TASK, AVAILABLE EXECUTORS and PREVIOUS OPERATIONS, you give the next one or many operations in a list with suitable executors in given format.

When TASK is not complete and need more operations to complete, give task_status UNDONE.
When TASK is done, give task_status DONE.
When TASK is waiting for executing previous operations in timer, give task_status IN_TIMER.
When you think there is no suitable executor in AVAILABLE EXECUTORS to continue the TASK, give task_status NO_SUITABLE_EXECUTOR.
When there is any OPERATION in PREVIOUS OPERATIONS has Execution Status is in_queue or running or created, give task_status UNDONE with empty operations list.
```

## Pipeline Execution Rules

### Sequential Execution Order

1. **Data Acquisition** (gs_147_acquisition)
   - **Purpose**: Initiate the sales process with initial information from sellers and buyers/customers/companies
   - **Critical Rule**: If `status_info_website = 'fail'`, STOP the TASK. Otherwise, CONTINUE.
   - **Input Sources**: Website, business card, social media, free text description
   - **Minimum Execution Time**: 100 seconds

2. **Data Preparation** (gs_149_data_preparation)
   - **Purpose**: Clean, standardize, and categorize the collected data
   - **Dependency**: Requires successful Data Acquisition
   - **Process**: Structure raw data into standardized company profiles with pain points, financial info, etc.

3. **Lead Scoring** (gs_154_lead_scoring)
   - **Purpose**: Evaluate and rank potential products/customers based on set criteria
   - **Dependency**: Requires structured data from Data Preparation
   - **Output**: Detailed customer information and review scores for each product

4. **Initial Outreach** (gs_148_initial_outreach)
   - **Purpose**: Generate ONLY draft messages for initial contact with potential customers
   - **Critical Rules**:
     - First run: Generate ONLY draft messages
     - DO NOT auto-send drafts
     - After generating drafts, WAIT for human review and further instructions
     - Actions ONLY for Initial Outreach (require explicit trigger): `draft_write`, `draft_rewrite`, `send`, `close`
     - Perform ONE action per trigger
     - STOP after each action, await next trigger

5. **Follow Up** (gs_162_follow_up)
   - **Purpose**: Analyze previous interactions and maintain engagement with the customer or lead
   - **Actions**: `draft_write`, `draft_rewrite`, `send`
   - **Trigger**: Requires explicit human trigger
   - **Process**: Analyze interactions, generate follow-up actions

## Process Status Rules

### Initial Runtime Behavior
- Execute steps 1-4 automatically
- After `draft_write` in Initial Outreach, WAIT for next instruction
- Do not proceed to Follow Up without explicit trigger

### Subsequent Runtime Behavior
- Operator determines which steps to execute
- Exception: Initial Outreach and Follow Up always require explicit triggers
- Human-in-the-loop control for all outreach actions

## Stage-Specific Business Logic

### Data Acquisition Stage
**Description**: "Used to collect seller's initial data like org_id, org_name, language and extract customer information from website, business card or free text description."

**Required Inputs**:
- `org_id`, `org_name`, `language` (seller info)
- `full_input` (complete information input)
- `input_website` (website URL)
- `input_business_card` (business card image URL)
- `input_freetext` (free text description)
- `team_id`, `team_name`, `project_code`

**Critical Stop Condition**:
- If website extraction fails (`status_info_website = 'fail'`), stop entire pipeline

**Data Sources**:
- Website scraping
- Business card OCR
- LinkedIn/Facebook profiles
- Free text descriptions

### Data Preparation Stage
**Description**: "Used to cleaning, structuring, and enriching the data acquired."

**Required Inputs** (from Data Acquisition):
- Customer basic info (name, email, phone, address, website, industry)
- Contact details (name, title)
- Organization info (org_id, team_id, project_code)
- Research flags (`research_mini`, `company_mini_search`)

**Output Structure**:
- `companyInfo` (name, size, address, website, industry, annualRevenue)
- `painPoints` (array of categorized pain points)
- `primaryContact` (contact person details)
- `financialInfo` (revenue, profit, funding sources)
- `developmentPlans` (short/long term goals)
- `productsAndServices` (main products, target markets)
- `technologyAndInnovation` (patents, R&D projects)

### Lead Scoring Stage
**Description**: "Used to score for each product based on criteria. The result is detailed customer information and review scores for each product."

**Required Inputs** (from Data Preparation):
- All structured company data
- Pain points analysis
- Financial information
- Development plans
- Technology stack

**Scoring Process**:
- Evaluate customer-product fit
- Apply weighted scoring criteria
- Generate detailed breakdown for each product
- Rank products by fit score

### Initial Outreach Stage
**Description**: "Send/Rewrite the Outreach by generating draft messages for first contact with potential customers OR Close the Outreach when customers feel negative"

**Action Types**:
- `draft_write`: Generate initial draft
- `draft_rewrite`: Modify existing draft
- `send`: Send approved draft
- `close`: Close outreach (negative response)

**Human-in-the-Loop Rules**:
- Always generate drafts first
- Wait for human review before any send action
- One action per trigger
- Stop and wait after each action

**Required Context**:
- Customer company info and pain points
- Lead scoring results
- Contact information
- Team/staff details for signatures

### Follow Up Stage
**Description**: "Follow up customer, nurture leads and maintain engagement by analyzing previous interactions and the current sales stage."

**Trigger Conditions**:
- No response to initial outreach
- Customer requested more information
- Scheduled follow-up based on sales stage
- Customer showed interest but didn't respond

**Required Context**:
- Previous interaction history
- Last interaction date and summary
- Current sales stage
- Follow-up reason

**Actions**:
- `draft_write`: Create follow-up draft
- `draft_rewrite`: Modify follow-up draft
- `send`: Send approved follow-up

## Execution Control Rules

### Automatic Execution (Initial Runtime)
1. Data Acquisition → Data Preparation → Lead Scoring → Initial Outreach (draft_write only)
2. Stop after draft generation
3. Wait for human review

### Manual Execution (Subsequent Runtimes)
1. Human triggers specific actions in Initial Outreach or Follow Up
2. Each action is treated as separate operation
3. System waits for next trigger after each action

### Stop Conditions
1. **Hard Stop**: Website extraction failure in Data Acquisition
2. **Soft Stop**: After draft generation in Initial Outreach
3. **Error Stop**: Any stage returns error status
4. **Manual Stop**: Human closes outreach process

### Concurrency Rules
- Maximum 1 simultaneous operation
- Maximum 10 operations per task
- Sequential execution only
- No parallel processing

## Data Flow Dependencies

### Stage Dependencies
```
Data Acquisition (required: website URL)
    ↓
Data Preparation (required: raw customer data)
    ↓
Lead Scoring (required: structured company data + pain points)
    ↓
Initial Outreach (required: company data + lead scores + contact info)
    ↓
Follow Up (required: previous interaction data)
```

### Data References
- Follow Up references: `previous_operations['gs_149_data_preparation'][-1]['output']`
- Initial Outreach references: `previous_operations['gs_154_lead_scoring'][-1]['output']['lead_scoring']`

## Implementation Notes for Local Version

### Orchestration Logic
The local implementation should replicate this business logic by:

1. **Sequential Execution**: Implement the same stage order and dependencies
2. **Stop Conditions**: Check for website failure and other stop conditions
3. **Human Gates**: Implement wait points for human review in outreach stages
4. **Action Control**: Limit outreach actions to one per execution
5. **Data Flow**: Ensure proper data passing between stages

### Configuration Requirements
- Team-specific prompts and settings
- Product definitions for scoring
- Scoring criteria and weights
- Email templates and tone settings
- Language-specific content

This business logic should be embedded in the local pipeline orchestrator to ensure the same intelligent behavior as the original server-based system.