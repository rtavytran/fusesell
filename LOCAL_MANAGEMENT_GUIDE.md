# FuseSell Local Management Guide

This guide covers the complete local management capabilities of FuseSell Local, allowing you to manage teams, products, and settings entirely from the command line without requiring external APIs or services.

## Overview

FuseSell Local now supports comprehensive local management through CLI commands:

- **Team Management**: Create, update, list, and describe teams
- **Product Management**: Create, update, and list products  
- **Settings Management**: Configure team-specific settings including product associations
- **Pipeline Execution**: Run sales automation pipelines with team-specific configurations

## Quick Start Tutorial

Follow this step-by-step tutorial to set up a complete team-based sales process locally.

### Step 1: Create a Team

First, create a new sales team:

```bash
python fusesell.py team create \
  --name "Enterprise Sales Team" \
  --description "Team focused on enterprise customers" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --plan-id "plan-enterprise-2024"
```

This will output a team ID like: `team_mycompany_20241017_143022`

### Step 2: Create Products

Create products that your team will sell:

```bash
# Create first product
python fusesell.py product create \
  --name "Enterprise CRM Pro" \
  --description "Advanced CRM solution for large enterprises" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --category "CRM Software" \
  --subcategory "Enterprise Solutions"

# Create second product  
python fusesell.py product create \
  --name "Sales Analytics Suite" \
  --description "Comprehensive sales analytics and reporting" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --category "Analytics" \
  --product-data '{"pricing": {"model": "subscription", "starting_price": "$299/month"}}'
```

Each command will output a product ID like: `prod-abc123-def4-5678-9012-345678901234`

### Step 3: Configure Team Settings

Link the products to your team and configure other settings:

```bash
# Link products to the team
python fusesell.py settings set team_mycompany_20241017_143022 \
  --setting-name product_settings \
  --value-json '[{"product_id": "prod-abc123-def4-5678-9012-345678901234"}, {"product_id": "prod-def456-789a-bcde-f012-3456789abcde"}]'

# Configure organization settings
python fusesell.py settings set team_mycompany_20241017_143022 \
  --setting-name organization_settings \
  --value-json '{"company_name": "My Company Inc", "industry": "Software", "target_market": "Enterprise"}'

# Configure sales rep settings
python fusesell.py settings set team_mycompany_20241017_143022 \
  --setting-name sales_rep_settings \
  --value-json '[{"name": "John Smith", "email": "john@mycompany.com", "role": "Senior Sales Rep"}]'
```

### Step 4: Run Sales Pipeline with Team Configuration

Now run a sales pipeline using your team's configuration:

```bash
python fusesell.py \
  --openai-api-key "sk-your-actual-api-key" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --team-id "team_mycompany_20241017_143022" \
  --full-input "Seller: My Company Inc, Customer: Target Corp, Communication: English" \
  --input-website "https://targetcorp.com"
```

The pipeline will now:
- Use only the products configured for this team during lead scoring
- Apply team-specific scheduling and content rules
- Use the team's organization and sales rep settings

## Command Reference

### Team Management Commands

#### Create Team
```bash
python fusesell.py team create \
  --name "<team_name>" \
  --description "<description>" \
  --org-id <org_id> \
  --org-name "<org_name>" \
  --plan-id <plan_id> \
  [--plan-name "<plan_name>"] \
  [--project-code "<project_code>"] \
  [--avatar "<avatar_url>"]
```

**Required Arguments:**
- `--name`: Team name
- `--org-id`: Organization identifier
- `--org-name`: Organization name  
- `--plan-id`: Plan identifier

**Optional Arguments:**
- `--description`: Team description
- `--plan-name`: Plan name
- `--project-code`: Project code
- `--avatar`: Avatar URL

#### Update Team
```bash
python fusesell.py team update <team_id> \
  [--name "<new_name>"] \
  [--description "<new_description>"] \
  [--plan-name "<new_plan_name>"] \
  [--project-code "<new_project_code>"] \
  [--avatar "<new_avatar_url>"]
```

#### List Teams
```bash
python fusesell.py team list --org-id <org_id>
```

#### Describe Team
```bash
python fusesell.py team describe <team_id>
```

### Product Management Commands

#### Create Product
```bash
python fusesell.py product create \
  --name "<product_name>" \
  --org-id <org_id> \
  --org-name "<org_name>" \
  [--description "<description>"] \
  [--category "<category>"] \
  [--subcategory "<subcategory>"] \
  [--project-code "<project_code>"] \
  [--product-data '<json_data>']
```

**Required Arguments:**
- `--name`: Product name
- `--org-id`: Organization identifier
- `--org-name`: Organization name

**Optional Arguments:**
- `--description`: Product description
- `--category`: Product category
- `--subcategory`: Product subcategory
- `--project-code`: Project code
- `--product-data`: Additional product data as JSON

**Example with detailed product data:**
```bash
python fusesell.py product create \
  --name "Advanced CRM" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --category "Software" \
  --product-data '{
    "pricing": {"model": "subscription", "starting_price": "$199/month"},
    "keyFeatures": ["Contact Management", "Pipeline Tracking", "Analytics"],
    "targetUsers": ["Sales Teams", "Marketing Teams"],
    "painPointsSolved": ["Manual lead tracking", "Poor sales visibility"]
  }'
```

#### Update Product
```bash
python fusesell.py product update <product_id> \
  [--name "<new_name>"] \
  [--description "<new_description>"] \
  [--category "<new_category>"] \
  [--subcategory "<new_subcategory>"] \
  [--product-data '<updated_json_data>']
```

#### List Products
```bash
python fusesell.py product list --org-id <org_id>
```

### Settings Management Commands

#### Set Team Setting
```bash
python fusesell.py settings set <team_id> \
  --setting-name <setting_name> \
  --value-json '<json_value>'
```

#### View Team Setting
```bash
python fusesell.py settings view <team_id> \
  --setting-name <setting_name>
```

### Available Settings

FuseSell Local supports 9 different team settings:

#### 1. gs_team_organization
Organization-level configuration:
```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_organization \
  --value-json '[{
    "org_name": "My Company Inc",
    "description": "Leading software company",
    "address": "123 Main St, City, State",
    "website": "https://mycompany.com",
    "primary_email": "contact@mycompany.com",
    "primary_phone": "+1-555-0123",
    "industry": "Software",
    "logo": "https://mycompany.com/logo.png",
    "primary_color": "#0066cc",
    "social_media_links": ["https://linkedin.com/company/mycompany"],
    "is_active": true
  }]'
```

#### 2. gs_team_rep
Sales representative configuration:
```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_rep \
  --value-json '[
    {
      "name": "John Smith",
      "email": "john@company.com",
      "phone": "+1-555-0123",
      "position": "Senior Sales Rep",
      "website": "https://mycompany.com",
      "primary_phone": "+1-555-0123",
      "primary_color": "#0066cc",
      "logo": null,
      "username": null,
      "is_primary": true
    }
  ]'
```

#### 3. gs_team_product (Critical)
Product associations for the team:
```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_product \
  --value-json '[
    {
      "product_id": "prod-123",
      "product_name": "Enterprise CRM",
      "image_url": "https://example.com/product.jpg"
    },
    {
      "product_id": "prod-456", 
      "product_name": "Analytics Suite",
      "image_url": "https://example.com/analytics.jpg"
    }
  ]'
```

#### 4. gs_team_schedule_time
Email scheduling preferences:
```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_schedule_time \
  --value-json '{
    "business_hours_start": "09:00",
    "business_hours_end": "17:00",
    "timezone": "America/New_York",
    "default_delay_hours": 2,
    "follow_up_delay_hours": 120,
    "avoid_weekends": true
  }'
```

#### 5. gs_team_initial_outreach (Use `configure` command)
Initial email configuration - **Use the simplified configure command**:

**Option A: Simple Instructions (No Examples)**
```bash
python fusesell.py settings configure <team_id> \
  --setting-type initial_outreach \
  --user-input "Use a consultative approach focusing on industry pain points. Keep emails under 150 words and always include social proof."
```

**Option B: With Example Files (AI Enhancement Mode)**
```bash
python fusesell.py settings configure <team_id> \
  --setting-type initial_outreach \
  --user-input "Make emails more personalized and include specific ROI benefits" \
  --examples-files "examples/email1.txt" "examples/email2.txt" \
  --template-mode ai_enhancement
```

**Option C: Strict Template Mode (Exact Copy)**
```bash
python fusesell.py settings configure <team_id> \
  --setting-type initial_outreach \
  --user-input "Use for enterprise software sales" \
  --examples-files "templates/enterprise_template.txt" \
  --template-mode strict_template
```

**Advanced: Direct JSON Setting (Not Recommended)**
```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_initial_outreach \
  --value-json '{
    "fewshots": false,
    "fewshots_location": [],
    "fewshots_strict_follow": false,
    "prompt": "Create professional initial outreach emails for ##customer_name## on behalf of ##staff_name##. Use a consultative approach.",
    "prompt_in_template": ""
  }'
```

#### 6. gs_team_follow_up (Use `configure` command)
Follow-up email configuration - **Use the simplified configure command**:

**Option A: Simple Instructions**
```bash
python fusesell.py settings configure <team_id> \
  --setting-type follow_up \
  --user-input "Use a friendly but persistent tone. Reference previous conversation and add new value in each follow-up."
```

**Option B: With Example Files**
```bash
python fusesell.py settings configure <team_id> \
  --setting-type follow_up \
  --user-input "Make follow-ups more value-focused with industry insights" \
  --examples-files "examples/followup1.txt" "examples/followup2.txt"
```

**Advanced: Direct JSON Setting (Not Recommended)**
```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_follow_up \
  --value-json '{
    "fewshots": false,
    "fewshots_location": [],
    "fewshots_strict_follow": false,
    "prompt": "Create follow-up emails that add value and reference previous interactions.",
    "prompt_in_template": ""
  }'
```

#### 7. gs_team_auto_interaction
**Purpose:** Configure how your team sends emails, including sender information and email CC/BCC settings.

**What This Controls:**
- Who appears as the sender in emails (name and email address)
- CC recipients (manager visibility, team coordination)
- BCC recipients (archiving, compliance tracking)
- Phone number for future SMS/Autocall features
- Communication channel type (Email, SMS, Autocall, Notif)

**When to Use:** Configure this when you want to:
- Use a specific sender email address (e.g., sales@mycompany.com instead of generic)
- Automatically CC your manager on all outreach emails
- Archive all sent emails by BCC to a central mailbox
- Prepare for multi-channel communication (SMS, voice calls)

---

**Basic Email Configuration (Most Common):**
```bash
# Replace <team_id> with your actual team ID (e.g., team_mycompany_20241017_143022)
python fusesell.py settings set <team_id> \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "John Smith",
      "from_number": "+1-555-0123",
      "tool_type": "Email",
      "email_cc": "manager@mycompany.com",
      "email_bcc": "archive@mycompany.com"
    }
  ]'
```

**Real Example:**
```bash
# Configure auto interaction for enterprise sales team
python fusesell.py settings set team_mycompany_20241017_143022 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "john.smith@mycompany.com",
      "from_name": "John Smith",
      "from_number": "+1-555-0123",
      "tool_type": "Email",
      "email_cc": "sales-manager@mycompany.com",
      "email_bcc": "crm-archive@mycompany.com"
    }
  ]'
```

---

**Field Reference:**

| Field | Required | Example | Description | When to Use |
|-------|----------|---------|-------------|-------------|
| `from_email` | Yes | `"sales@company.com"` | Sender email address | Always - this is who the email comes from |
| `from_name` | Yes | `"John Smith"` | Sender display name | Always - recipient sees this name |
| `from_number` | Yes | `"+1-555-0123"` | Sender phone number | Required field (use `""` if not applicable) |
| `tool_type` | Yes | `"Email"` | Must be: `Email`, `Autocall`, `Notif`, or `SMS` | Always use `"Email"` for email sending |
| `email_cc` | Yes | `"boss@co.com,team@co.com"` | Comma-separated CC emails | Use when manager/team needs visibility |
| `email_bcc` | Yes | `"archive@co.com"` | Comma-separated BCC emails | Use for archiving/compliance |

**Important Notes:**
- All fields are **required** but can be empty strings (`""`) if not used
- For email sending, `tool_type` should be `"Email"`
- CC/BCC should be `""` (empty string) if you don't need them, not omitted
- Multiple emails in CC/BCC: separate with commas, no spaces: `"a@co.com,b@co.com"`

---

**Common Scenarios:**

**Scenario 1: Simple Email (No CC/BCC)**
```bash
python fusesell.py settings set team_sales_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "Sales Team",
      "from_number": "",
      "tool_type": "Email",
      "email_cc": "",
      "email_bcc": ""
    }
  ]'
```

**Scenario 2: CC Manager on All Emails**
```bash
python fusesell.py settings set team_sales_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "john@mycompany.com",
      "from_name": "John Smith",
      "from_number": "+1-555-0123",
      "tool_type": "Email",
      "email_cc": "sales-manager@mycompany.com",
      "email_bcc": ""
    }
  ]'
```

**Scenario 3: Archive All Emails (BCC)**
```bash
python fusesell.py settings set team_sales_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "Sales Team",
      "from_number": "",
      "tool_type": "Email",
      "email_cc": "",
      "email_bcc": "archive@mycompany.com"
    }
  ]'
```

**Scenario 4: CC Manager + BCC Archive**
```bash
python fusesell.py settings set team_sales_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "john@mycompany.com",
      "from_name": "John Smith",
      "from_number": "+1-555-0123",
      "tool_type": "Email",
      "email_cc": "manager@mycompany.com",
      "email_bcc": "archive@mycompany.com,crm@mycompany.com"
    }
  ]'
```

**Scenario 5: Multiple CC Recipients**
```bash
python fusesell.py settings set team_sales_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "Jane Doe",
      "from_number": "+1-555-0456",
      "tool_type": "Email",
      "email_cc": "manager@mycompany.com,team-lead@mycompany.com,support@mycompany.com",
      "email_bcc": "archive@mycompany.com"
    }
  ]'
```

---

**Advanced: Multiple Communication Channels**

If you want to prepare for future SMS or voice call features, you can configure multiple channels:

```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "John Smith",
      "from_number": "+1-555-0123",
      "tool_type": "Email",
      "email_cc": "manager@mycompany.com",
      "email_bcc": "archive@mycompany.com"
    },
    {
      "from_email": "",
      "from_name": "Sales Team",
      "from_number": "+1-555-0199",
      "tool_type": "SMS",
      "email_cc": "",
      "email_bcc": ""
    }
  ]'
```

**Note:** Currently, only `Email` type is actively used. The system will automatically use the first `Email` configuration it finds.

---

**How to View Your Current Settings:**
```bash
python fusesell.py settings view <team_id> --setting-name gs_team_auto_interaction
```

**Windows Users - Important:**

On Windows Command Prompt, you need to escape the quotes:
```cmd
python fusesell.py settings set team_001 --setting-name gs_team_auto_interaction --value-json "[{\"from_email\": \"sales@co.com\", \"from_name\": \"Sales\", \"from_number\": \"+1-555-0100\", \"tool_type\": \"Email\", \"email_cc\": \"\", \"email_bcc\": \"\"}]"
```

Or use PowerShell (easier):
```powershell
python fusesell.py settings set team_001 `
  --setting-name gs_team_auto_interaction `
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "Sales Team",
      "from_number": "",
      "tool_type": "Email",
      "email_cc": "",
      "email_bcc": ""
    }
  ]'
```

---

**Common Errors and Solutions:**

❌ **Error:** "Auto interaction settings must be a list"
```bash
# WRONG - Missing square brackets
--value-json '{"from_email": "sales@co.com", ...}'

# CORRECT - Wrapped in array brackets
--value-json '[{"from_email": "sales@co.com", ...}]'
```

❌ **Error:** "Item 0 missing required field: email_cc"
```bash
# WRONG - Missing email_cc field
{"from_email": "sales@co.com", "from_name": "Sales", "from_number": "", "tool_type": "Email", "email_bcc": ""}

# CORRECT - All 6 fields present
{"from_email": "sales@co.com", "from_name": "Sales", "from_number": "", "tool_type": "Email", "email_cc": "", "email_bcc": ""}
```

❌ **Error:** "Invalid tool_type 'email'"
```bash
# WRONG - Lowercase
"tool_type": "email"

# CORRECT - Capitalized
"tool_type": "Email"
```

❌ **Error:** "Invalid email in email_cc"
```bash
# WRONG - Spaces after commas
"email_cc": "a@co.com, b@co.com"

# CORRECT - No spaces
"email_cc": "a@co.com,b@co.com"
```

---

**What Happens When You Configure This:**

When you send emails through Initial Outreach or Follow-up stages:

1. **From Email:** Recipients see the email coming from your configured `from_email`
2. **From Name:** Recipients see your configured `from_name` in their inbox
3. **CC:** All CC recipients receive a copy of the email (visible to everyone)
4. **BCC:** All BCC recipients receive a copy (hidden from other recipients)
5. **Action Type:** Email sending uses the configured communication channel

**Before Configuration:**
```
From: (empty or generic)
To: customer@company.com
```

**After Configuration:**
```
From: John Smith <john@mycompany.com>
To: customer@company.com
CC: sales-manager@mycompany.com
BCC: archive@mycompany.com
```

#### 8. gs_team_followup_schedule_time
Follow-up scheduling rules:
```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_followup_schedule_time \
  --value-json '{
    "hours_after_initial": 120,
    "first_followup_days": 3,
    "second_followup_days": 7,
    "final_followup_days": 14,
    "respect_business_hours": true
  }'
```

#### 9. gs_team_birthday_email
Birthday email automation configuration:
```bash
python fusesell.py settings set <team_id> \
  --setting-name gs_team_birthday_email \
  --value-json '{
    "mail_tone": "Friendly",
    "extra_guide": "Send personalized birthday greetings to customers with friendly tone, max 200 words, timezone UTC+07",
    "org_timezone": "UTC+07",
    "maximum_words": 200,
    "birthday_email_check": {
      "is_enabled": true,
      "is_complete_prompt": false
    },
    "fewshots_strict_follow": false
  }'
```

## Simplified Settings Configuration

For complex settings like `initial_outreach` and `follow_up`, use the new **`configure`** command instead of manually crafting JSON. This tool intelligently processes your input according to the flowchart logic:

### Configuration Flowchart Logic

```
User Input → Has Examples? 
├─ No Examples → Message Type?
│  ├─ Complete Prompt → Use directly as prompt
│  └─ Instructions → Combine with appropriate default prompt*
└─ Has Examples → Template Mode?
   ├─ AI Enhancement → Use examples + guidance for AI modifications  
   └─ Strict Template → Extract exact templates, replace only placeholders

*Default Prompts:
- initial_outreach: "Create professional initial outreach emails for ##customer_name## on behalf of ##staff_name##."
- follow_up: "Create professional follow-up emails for ##customer_name## on behalf of ##staff_name##. Reference previous interactions and add new value."
```

### Configuration Examples

**Simple Instructions (Most Common)**
```bash
python fusesell.py settings configure team_id \
  --setting-type initial_outreach \
  --user-input "Use consultative tone, focus on ROI, keep under 150 words"
```

**Complete Custom Prompt**
```bash
python fusesell.py settings configure team_id \
  --setting-type initial_outreach \
  --user-input "Create professional emails for ##customer_name## from ##staff_name##. Focus on industry challenges and provide specific solutions with measurable benefits."
```

**With Example Files (AI Enhancement)**
```bash
python fusesell.py settings configure team_id \
  --setting-type follow_up \
  --user-input "Make more personalized, add industry insights" \
  --examples-files "templates/followup1.txt" "templates/followup2.txt" \
  --template-mode ai_enhancement
```

**Strict Template Mode (Exact Copy)**
```bash
python fusesell.py settings configure team_id \
  --setting-type initial_outreach \
  --user-input "Enterprise software sales context" \
  --examples-files "templates/enterprise.txt" \
  --template-mode strict_template
```

### Generated Settings Structure

The configure command automatically creates the correct JSON structure:

```json
{
  "fewshots": false,
  "fewshots_location": [],
  "fewshots_strict_follow": false,
  "prompt": "Generated prompt based on your input and setting type",
  "prompt_in_template": "Template instructions (if applicable)"
}
```

**Note:** The system uses different default prompts for each setting type:
- **initial_outreach**: Focuses on creating initial contact emails
- **follow_up**: Emphasizes referencing previous interactions and adding new value

## Team-Based Pipeline Execution

Once you have configured a team with products and settings, you can run pipelines that use the team's specific configuration:

```bash
python fusesell.py \
  --openai-api-key "sk-your-api-key" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --team-id "team_mycompany_20241017_143022" \
  --full-input "Seller: My Company Inc, Customer: Target Corp, Communication: English" \
  --input-website "https://targetcorp.com"
```

### What Happens with Team Configuration:

1. **Lead Scoring**: Only evaluates against products configured for the team
2. **Email Scheduling**: Uses team's schedule_time_settings for optimal timing
3. **Content Generation**: Applies team's initial_outreach_settings and follow_up_settings
4. **Organization Context**: Uses team's organization_settings for company information
5. **Sales Rep Info**: Uses team's sales_rep_settings for email signatures and contact info

## Advanced Usage Examples

### Complete Team Setup Script

Here's a complete example that sets up a team with full configuration:

```bash
#!/bin/bash

# 1. Create team
TEAM_ID=$(python fusesell.py team create \
  --name "Enterprise Sales Team" \
  --description "Focused on large enterprise deals" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --plan-id "plan-enterprise-2024" | grep "Team created successfully:" | cut -d' ' -f4)

echo "Created team: $TEAM_ID"

# 2. Create products
PRODUCT1_ID=$(python fusesell.py product create \
  --name "Enterprise CRM" \
  --description "Full-featured CRM for enterprises" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --category "CRM" | grep "Product created successfully:" | cut -d' ' -f4)

PRODUCT2_ID=$(python fusesell.py product create \
  --name "Analytics Suite" \
  --description "Advanced sales analytics" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --category "Analytics" | grep "Product created successfully:" | cut -d' ' -f4)

echo "Created products: $PRODUCT1_ID, $PRODUCT2_ID"

# 3. Configure team settings
python fusesell.py settings set $TEAM_ID \
  --setting-name product_settings \
  --value-json "[{\"product_id\": \"$PRODUCT1_ID\"}, {\"product_id\": \"$PRODUCT2_ID\"}]"

python fusesell.py settings set $TEAM_ID \
  --setting-name organization_settings \
  --value-json '{"company_name": "My Company Inc", "industry": "Software"}'

python fusesell.py settings set $TEAM_ID \
  --setting-name schedule_time_settings \
  --value-json '{"business_hours_start": "09:00", "business_hours_end": "17:00", "timezone": "America/New_York"}'

echo "Team configuration complete!"

# 4. Run pipeline with team
python fusesell.py \
  --openai-api-key "sk-your-api-key" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --team-id "$TEAM_ID" \
  --full-input "Seller: My Company Inc, Customer: Target Corp, Communication: English" \
  --input-website "https://targetcorp.com"
```

### Managing Multiple Teams

You can create multiple teams for different purposes:

```bash
# Sales team for SMB customers
python fusesell.py team create \
  --name "SMB Sales Team" \
  --description "Small and medium business focus" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --plan-id "plan-smb-2024"

# Sales team for enterprise customers  
python fusesell.py team create \
  --name "Enterprise Sales Team" \
  --description "Large enterprise focus" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --plan-id "plan-enterprise-2024"

# List all teams
python fusesell.py team list --org-id "mycompany"
```

## Data Storage

All team, product, and settings data is stored locally in the SQLite database at `fusesell_data/fusesell.db`. The schema is fully compatible with the server-side FuseSell architecture, ensuring seamless data portability.

### Database Tables

- **teams**: Team information and metadata
- **products**: Product catalog and specifications  
- **team_settings**: Team-specific configuration settings
- **llm_worker_task**: Pipeline execution records
- **llm_worker_operation**: Stage execution tracking

## Troubleshooting

### Common Issues

#### 1. "Team not found" errors
Make sure you're using the correct team ID returned from the create command.

#### 2. "Invalid JSON" errors  
Ensure JSON values are properly escaped, especially on Windows:
```bash
# Use double quotes and escape inner quotes
--value-json "[{\"product_id\": \"prod-123\"}]"
```

#### 3. Pipeline not using team settings
Verify that:
- The team ID exists: `python fusesell.py team describe <team_id>`
- Products are linked: `python fusesell.py settings view <team_id> --setting-name product_settings`
- You're passing `--team-id` to the pipeline command

#### 4. No products found for team
Check that product_settings is configured:
```bash
python fusesell.py settings view <team_id> --setting-name product_settings
```

### Debug Mode

Enable debug logging to troubleshoot issues:
```bash
python fusesell.py --log-level DEBUG [other arguments...]
```

## Integration with Server Architecture

The local management system is designed to be fully compatible with the server-side FuseSell workflows:

- **fusesell_plan_team_clone.yaml**: Team creation logic
- **fusesell_product_ai.yaml**: Product management logic  
- **fusesell_team_setting_*.yaml**: Settings management logic

This ensures that teams, products, and settings created locally can be seamlessly migrated to or synchronized with a server deployment.

## Step-by-Step Tutorial: Setting Up Auto Interaction for a New Team

This tutorial shows you exactly how to set up email sender configuration for a new sales team from start to finish.

### Prerequisites
- FuseSell Local installed
- OpenAI API key (if using AI features)
- Your team's sender email address and name

### Step 1: Create Your Team (If Not Already Created)

```bash
# Create a new team
python fusesell.py team create \
  --name "Enterprise Sales Team" \
  --description "Team focused on enterprise customers" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --plan-id "plan-enterprise-2024"
```

**Output Example:**
```
Team created successfully: team_mycompany_20241220_143022
```

**Save this team ID!** You'll need it for the next steps. Let's say it's: `team_mycompany_20241220_143022`

### Step 2: Configure Auto Interaction Settings

Now configure how emails from this team will be sent:

```bash
# Replace team_mycompany_20241220_143022 with YOUR actual team ID from Step 1
python fusesell.py settings set team_mycompany_20241220_143022 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "John Smith",
      "from_number": "+1-555-0123",
      "tool_type": "Email",
      "email_cc": "sales-manager@mycompany.com",
      "email_bcc": "archive@mycompany.com"
    }
  ]'
```

**What to customize:**
- `from_email`: Your actual sales email address
- `from_name`: The sales person's name or team name
- `from_number`: Your phone number (or use `""` if none)
- `email_cc`: Manager's email to CC (or use `""` if not needed)
- `email_bcc`: Archive email for BCC (or use `""` if not needed)

**Output if successful:**
```
Setting 'gs_team_auto_interaction' updated for team team_mycompany_20241220_143022
```

### Step 3: Verify Your Configuration

Check that your settings were saved correctly:

```bash
python fusesell.py settings view team_mycompany_20241220_143022 \
  --setting-name gs_team_auto_interaction
```

**Expected Output:**
```json
[
  {
    "from_email": "sales@mycompany.com",
    "from_name": "John Smith",
    "from_number": "+1-555-0123",
    "tool_type": "Email",
    "email_cc": "sales-manager@mycompany.com",
    "email_bcc": "archive@mycompany.com"
  }
]
```

### Step 4: Test Email Sending (Optional)

Now when you run a sales pipeline with this team, all emails will use your configured settings:

```bash
python fusesell.py \
  --openai-api-key "sk-your-api-key" \
  --org-id "mycompany" \
  --org-name "My Company Inc" \
  --team-id "team_mycompany_20241220_143022" \
  --input-website "https://testcompany.com" \
  --dry-run
```

The `--dry-run` flag lets you test without actually sending emails or making API calls.

### Step 5: Update Settings (If Needed)

If you need to change your settings later:

```bash
# Example: Change the sender name
python fusesell.py settings set team_mycompany_20241220_143022 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "Jane Doe",
      "from_number": "+1-555-0123",
      "tool_type": "Email",
      "email_cc": "sales-manager@mycompany.com",
      "email_bcc": "archive@mycompany.com"
    }
  ]'
```

**Note:** When updating, you must provide the complete configuration again, not just the fields you want to change.

---

## Common Real-World Scenarios

### Scenario A: Sales Team with Manager Oversight

**Use Case:** Sales reps send emails, manager gets CC'd on everything

```bash
python fusesell.py settings set team_sales_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "rep@company.com",
      "from_name": "Sarah Johnson",
      "from_number": "+1-555-0100",
      "tool_type": "Email",
      "email_cc": "sales-manager@company.com",
      "email_bcc": ""
    }
  ]'
```

**Result:**
- Customer sees: "From: Sarah Johnson <rep@company.com>"
- Manager gets CC: Every email to customers
- Archive: No BCC archiving

---

### Scenario B: Compliance-Heavy Industry

**Use Case:** Legal department requires all outbound communications archived

```bash
python fusesell.py settings set team_legal_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "compliance@company.com",
      "from_name": "Compliance Team",
      "from_number": "",
      "tool_type": "Email",
      "email_cc": "",
      "email_bcc": "legal-archive@company.com,audit@company.com"
    }
  ]'
```

**Result:**
- Customer sees: "From: Compliance Team <compliance@company.com>"
- No CC: Customer doesn't see any other recipients
- BCC Archive: legal-archive and audit both get copies (hidden)

---

### Scenario C: Multiple Team Leads

**Use Case:** Two team leads want to see all outreach from their team

```bash
python fusesell.py settings set team_enterprise_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "enterprise-sales@company.com",
      "from_name": "Enterprise Team",
      "from_number": "+1-555-0200",
      "tool_type": "Email",
      "email_cc": "lead1@company.com,lead2@company.com",
      "email_bcc": "crm@company.com"
    }
  ]'
```

**Result:**
- Customer sees: "From: Enterprise Team <enterprise-sales@company.com>"
- CC: Both team leads (lead1 and lead2) see the email
- BCC: CRM system archives it (hidden from customer and team leads)

---

### Scenario D: Simple Configuration

**Use Case:** Just want a professional sender name, no CC/BCC needed

```bash
python fusesell.py settings set team_smb_001 \
  --setting-name gs_team_auto_interaction \
  --value-json '[
    {
      "from_email": "hello@startup.com",
      "from_name": "The Startup Team",
      "from_number": "",
      "tool_type": "Email",
      "email_cc": "",
      "email_bcc": ""
    }
  ]'
```

**Result:**
- Customer sees: "From: The Startup Team <hello@startup.com>"
- No CC/BCC: Simple, clean email

---

## Troubleshooting Guide

### Problem 1: "Invalid JSON in --value-json"

**Symptoms:** Error when trying to set the configuration

**Common Causes:**
1. Missing comma between fields
2. Missing quotes around values
3. Wrong bracket type `{}` vs `[]`

**Solution:** Copy one of the exact examples above and modify only the values inside the quotes.

**Quick Fix:**
```bash
# Use this template and ONLY change the values in quotes
python fusesell.py settings set YOUR_TEAM_ID \
  --setting-name gs_team_auto_interaction \
  --value-json '[{"from_email": "YOUR_EMAIL", "from_name": "YOUR_NAME", "from_number": "YOUR_PHONE", "tool_type": "Email", "email_cc": "CC_EMAIL_OR_EMPTY", "email_bcc": "BCC_EMAIL_OR_EMPTY"}]'
```

---

### Problem 2: "Team not found"

**Symptoms:** Error saying team doesn't exist

**Solution:**
```bash
# First, list all your teams to find the correct team ID
python fusesell.py team list --org-id mycompany

# Use the exact team_id from the output
```

---

### Problem 3: Settings Don't Seem to Apply

**Symptoms:** Emails still show old sender information

**Checklist:**
1. ✓ Did you use the correct team_id when running the pipeline?
2. ✓ Did you verify settings with `settings view`?
3. ✓ Did you include `--team-id` flag when running fusesell.py?

**Verification:**
```bash
# 1. Verify settings are saved
python fusesell.py settings view YOUR_TEAM_ID --setting-name gs_team_auto_interaction

# 2. Make sure you use --team-id when running pipeline
python fusesell.py \
  --team-id YOUR_TEAM_ID \
  --openai-api-key "sk-..." \
  --org-id "mycompany" \
  --org-name "My Company" \
  --input-website "https://test.com"
```

---

### Problem 4: Windows Command Line Issues

**Symptoms:** Errors about quotes or JSON format on Windows

**Solution for Windows Command Prompt:**
```cmd
python fusesell.py settings set team_001 --setting-name gs_team_auto_interaction --value-json "[{\"from_email\": \"sales@co.com\", \"from_name\": \"Sales\", \"from_number\": \"\", \"tool_type\": \"Email\", \"email_cc\": \"\", \"email_bcc\": \"\"}]"
```

**Better Solution - Use PowerShell:**
```powershell
python fusesell.py settings set team_001 `
  --setting-name gs_team_auto_interaction `
  --value-json '[
    {
      "from_email": "sales@mycompany.com",
      "from_name": "Sales Team",
      "from_number": "",
      "tool_type": "Email",
      "email_cc": "",
      "email_bcc": ""
    }
  ]'
```

**Best Solution - Create a Script:**
Create a file `setup_team.ps1`:
```powershell
$teamId = "team_mycompany_20241220_143022"
$config = @'
[
  {
    "from_email": "sales@mycompany.com",
    "from_name": "Sales Team",
    "from_number": "",
    "tool_type": "Email",
    "email_cc": "",
    "email_bcc": ""
  }
]
'@

python fusesell.py settings set $teamId `
  --setting-name gs_team_auto_interaction `
  --value-json $config
```

Run it:
```powershell
.\setup_team.ps1
```

---

## Quick Reference Card

### Basic Command Structure
```bash
python fusesell.py settings set <TEAM_ID> \
  --setting-name gs_team_auto_interaction \
  --value-json '[{<CONFIGURATION>}]'
```

### Minimum Required Configuration
```json
[
  {
    "from_email": "email@company.com",
    "from_name": "Name",
    "from_number": "",
    "tool_type": "Email",
    "email_cc": "",
    "email_bcc": ""
  }
]
```

### Field Quick Reference
- `from_email` → Who sends the email
- `from_name` → Name shown to recipient
- `from_number` → Phone (use `""` if none)
- `tool_type` → Always `"Email"` for emails
- `email_cc` → Visible copies (or `""`)
- `email_bcc` → Hidden copies (or `""`)

### Common Commands
```bash
# View settings
python fusesell.py settings view <TEAM_ID> --setting-name gs_team_auto_interaction

# List all teams
python fusesell.py team list --org-id <ORG_ID>

# Test with dry run
python fusesell.py --team-id <TEAM_ID> --dry-run [other options...]
```

---

## Next Steps

After completing this guide, you should be able to:

1. ✅ Create and manage teams locally
2. ✅ Create and manage products locally
3. ✅ Configure team-specific settings (especially auto interaction)
4. ✅ Run team-based sales pipelines with custom sender configurations
5. ✅ Troubleshoot common issues

For advanced customization and development, see:
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Extending the system
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Technical API reference
- [DATABASE.md](DATABASE.md) - Database schema details