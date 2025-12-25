# Initial Outreach Template Usage Guide

This guide explains how to use custom email templates for initial outreach in FuseSell.

## Overview

FuseSell now supports using custom email templates for initial outreach. You can provide template files that will be used either as:
1. **Strict Templates**: The LLM will mirror the exact content and structure
2. **AI Enhancement Mode**: The LLM will use templates as inspiration while applying customization

## Configuration Modes

### Mode 1: No Templates (Default)
The system uses the default prompt from `prompts.json` without any template examples.

### Mode 2: AI Enhancement Mode (Recommended)
Templates are used as inspiration while incorporating best practices and customization.

### Mode 3: Strict Template Mode
Templates are mirrored exactly with only placeholders replaced.

## Step-by-Step Setup

### Step 1: Create Template Files

Create template files with your desired email format. Save them in your `fusesell_data` directory or any accessible location.

**Example Template** (`fusesell_data/templates/enterprise_outreach.txt`):
```
Subject: Solving [Pain Point] for [Industry] Leaders

Hi [Contact Name],

I noticed [Company Name] is doing great work in the [industry] space. Many companies we work with in this sector face challenges with [specific pain point].

We've helped organizations like [Similar Company] achieve [specific result] through our [product/service].

Would you be interested in a brief conversation about how we might help [Company Name] achieve similar results?

Best regards,
[Your Name]
[Your Title]
[Your Company]
```

### Step 2: Configure Team Settings

#### Option A: Using CLI (Recommended)

**For AI Enhancement Mode:**
```bash
python fusesell.py settings configure <team_id> \
  --setting-type initial_outreach \
  --user-input "Use professional tone, focus on value proposition, keep under 150 words" \
  --examples-files "templates/enterprise_outreach.txt" "templates/casual_outreach.txt" \
  --template-mode ai_enhancement
```

**For Strict Template Mode:**
```bash
python fusesell.py settings configure <team_id> \
  --setting-type initial_outreach \
  --user-input "Use for enterprise software sales" \
  --examples-files "templates/enterprise_outreach.txt" \
  --template-mode strict_template
```

#### Option B: Direct Python API

```python
from fusesell_local.utils.data_manager import LocalDataManager

data_manager = LocalDataManager('./fusesell_data')

# For AI Enhancement Mode
data_manager.save_team_settings(
    team_id='team123',
    org_id='org456',
    plan_id='plan789',
    team_name='Sales Team',
    gs_team_initial_outreach={
        "fewshots": True,
        "fewshots_location": [
            "templates/enterprise_outreach.txt",
            "templates/casual_outreach.txt"
        ],
        "fewshots_strict_follow": False,
        "prompt": "Create professional initial outreach emails for ##customer_name## on behalf of ##staff_name##.",
        "prompt_in_template": "Use the provided examples as inspiration. Adapt tone and style to customer context."
    }
)

# For Strict Template Mode
data_manager.save_team_settings(
    team_id='team123',
    org_id='org456',
    plan_id='plan789',
    team_name='Sales Team',
    gs_team_initial_outreach={
        "fewshots": True,
        "fewshots_location": ["templates/enterprise_outreach.txt"],
        "fewshots_strict_follow": True,
        "prompt": "Use exact templates from examples for initial_outreach.",
        "prompt_in_template": "Mirror the EXACT CONTENT of provided examples. Only replace placeholders with customer data."
    }
)
```

### Step 3: Run Pipeline with Template Configuration

Once configured, the pipeline will automatically use the templates:

```bash
python fusesell.py --openai-api-key sk-xxx \
  --org-id rta \
  --org-name "RTA Corp" \
  --team-id team123 \
  --full-input "Seller: RTA Corp, Customer: Example Company, Communication: English" \
  --input-website "https://example.com"
```

### Step 4: Programmatic Template Override (Advanced)

You can also override templates programmatically when calling the stage directly:

```python
from fusesell_local.stages.initial_outreach import InitialOutreachStage

stage = InitialOutreachStage(config, data_manager)

# Override with custom template files
custom_templates = [
    "/path/to/custom_template1.txt",
    "/path/to/custom_template2.txt"
]

# The stage will use these templates instead of team settings
context = {
    'input_data': {...},
    'customer_data': {...},
    # ... other context
}

result = stage._generate_email_drafts_from_prompt(
    customer_data,
    recommended_product,
    scoring_data,
    context,
    template_files=custom_templates  # Optional override
)
```

## Template File Paths

Template file paths can be:
- **Relative**: Searched in multiple locations in priority order:
  1. `workspace_dir/filename.txt` (where uploaded files are stored in RealtimeX)
  2. `fusesell_data/filename.txt` or `fusesell_data/path/filename.txt`
  3. `fusesell_data/templates/filename.txt`
- **Absolute**: Full system path (e.g., `"/home/user/templates/my_template.txt"`)

### RealtimeX Uploaded Files

When users upload files in RealtimeX, they are stored at the workspace root level. Simply use the filename:

```json
{
  "fewshots_location": ["my_uploaded_template.txt"]
}
```

This will be found at: `<workspace_slug>/my_uploaded_template.txt`

### Organized Template Files

For better organization, you can create a templates subdirectory:

```json
{
  "fewshots_location": ["templates/enterprise.txt", "templates/casual.txt"]
}
```

These will be found at: `<workspace_slug>/fusesell_data/templates/enterprise.txt`

## Available Placeholders

When creating templates, you can use these placeholders that will be **automatically replaced** with customer-specific data:

| Placeholder | Description | Example Value |
|------------|-------------|---------------|
| `##customer_name##` | Customer contact full name | "John Smith" |
| `##customer_first_name##` | Customer's first name (language-aware) | "John" |
| `##company_name##` | Customer company name | "Acme Corp" |
| `##staff_name##` | Your sales rep name | "Jane Doe" |
| `##org_name##` | Your organization name | "TechCorp" |
| `##selected_product##` | Recommended product name | "Enterprise CRM Platform" |
| `##language##` | Communication language | "English" |
| `##action_type##` | Type of action | "email drafts" |
| `##company_info##` | Detailed company summary | "Company: Acme Corp\nIndustry: Software\n..." |
| `##selected_product_info##` | Detailed product information | "Product: CRM Platform\nPrice: $99/mo\n..." |
| `##first_name_guide##` | Guidance for first name usage | "(Use 'John' as first name)" |

### Example Template with Placeholders

```text
Subject: Quick question about ##company_name##

Hi ##customer_first_name##,

I noticed ##company_name## is doing great work in the industry. Many companies we work with face similar challenges.

We've helped organizations like yours achieve significant results through our ##selected_product##.

Would you be interested in a brief conversation about how we might help ##company_name## achieve similar outcomes?

Best regards,
##staff_name##
##org_name##
```

**After placeholder replacement** (with actual customer data):

```text
Subject: Quick question about Acme Corp

Hi John,

I noticed Acme Corp is doing great work in the industry. Many companies we work with face similar challenges.

We've helped organizations like yours achieve significant results through our Enterprise CRM Platform.

Would you be interested in a brief conversation about how we might help Acme Corp achieve similar outcomes?

Best regards,
Jane Doe
TechCorp
```

## How It Works

### AI Enhancement Mode (`fewshots_strict_follow: false`)
1. Loads template files from specified paths
2. Includes templates as "inspiration examples" in the LLM prompt
3. LLM adapts templates to customer context while maintaining style
4. Applies customization guidance from `prompt_in_template`

### Strict Template Mode (`fewshots_strict_follow: true`)
1. Loads template files from specified paths
2. Instructs LLM to mirror exact content and structure
3. Only allows replacement of placeholders with customer data
4. Enforces strict rules (no invented info, no placeholder greetings, etc.)

## Configuration Schema

The `gs_team_initial_outreach` setting has this structure:

```json
{
  "fewshots": true,                    // Enable template mode
  "fewshots_location": [               // List of template file paths
    "templates/template1.txt",
    "templates/template2.txt"
  ],
  "fewshots_strict_follow": false,     // false = AI enhancement, true = strict
  "prompt": "Base prompt text...",     // Main prompt with placeholders
  "prompt_in_template": "Additional instructions..."  // Template-specific guidance
}
```

## Best Practices

### For AI Enhancement Mode:
- Provide 2-3 diverse template examples
- Include templates for different scenarios (cold outreach, warm intro, follow-up)
- Use `prompt_in_template` to specify tone, length, and style preferences
- Templates serve as style guides, not rigid structures

### For Strict Template Mode:
- Use when you have proven, tested email templates
- Provide templates with clear placeholder locations
- Ensure templates are compliant with your brand guidelines
- Test thoroughly to ensure placeholders are replaced correctly

### General Tips:
- Store templates in version control
- Use meaningful file names (e.g., `enterprise_cold_outreach.txt`)
- Keep templates focused and concise
- Test with sample customer data before production use
- Monitor LLM output to ensure quality

## Troubleshooting

### Templates Not Loading
- Check file paths are correct (relative to `data_dir`)
- Verify files exist and have read permissions
- Check logs for "Template file not found" warnings

### Templates Not Being Used
- Verify `fewshots: true` in team settings
- Confirm `team_id` is set in pipeline config
- Check logs for "Using team template configuration" message

### Poor Template Adherence
- For strict mode: Ensure `fewshots_strict_follow: true`
- For AI mode: Add more specific guidance in `prompt_in_template`
- Consider providing more example templates

### Empty Output
- Check template files are not empty
- Verify template format is compatible
- Review LLM prompt construction in logs

## Example Workflow

```bash
# 1. Create templates
mkdir -p fusesell_data/templates
cat > fusesell_data/templates/enterprise.txt << 'EOF'
Subject: Quick question about [Pain Point]

Hi [Contact Name],

I noticed [Company Name] is a leader in [industry]. Many of our clients in this space face challenges with [pain point].

We've helped companies achieve [result]. Would you be open to a brief call?

Best,
[Your Name]
EOF

# 2. Configure team
python fusesell.py settings configure team123 \
  --setting-type initial_outreach \
  --user-input "Professional, concise, value-focused" \
  --examples-files "templates/enterprise.txt" \
  --template-mode ai_enhancement

# 3. Run pipeline
python fusesell.py --openai-api-key sk-xxx \
  --team-id team123 \
  --org-id rta \
  --org-name "RTA Corp" \
  --full-input "Seller: RTA, Customer: Acme Corp, Communication: English" \
  --input-website "https://acme.com"

# 4. Review generated emails in output
```

## Migration from Previous Versions

If you were using prompt customization without templates:

**Before:**
```json
{
  "customization_request": "Make emails more casual and conversational..."
}
```

**After (AI Enhancement):**
```json
{
  "fewshots": true,
  "fewshots_location": ["templates/casual_style.txt"],
  "fewshots_strict_follow": false,
  "prompt": "Create initial outreach emails...",
  "prompt_in_template": "Make emails more casual and conversational..."
}
```

Or continue using without templates (backward compatible):
```json
{
  "fewshots": false,
  "prompt": "Create casual, conversational emails for ##customer_name##..."
}
```
