# Birthday Email Management Guide

This guide covers the birthday email functionality in FuseSell Local, which provides automated birthday email template generation and management based on the server-side birthday email processing logic.

## Overview

The birthday email system consists of:

1. **Birthday Email Settings Configuration** - Team-specific settings for birthday emails
2. **Template Generation** - AI-powered birthday email template creation
3. **Validation Logic** - Prompt analysis and validation
4. **Template Management** - Storage and retrieval of birthday email templates

## Birthday Email Settings Structure

Based on the server implementation (gs_scheduler.py), birthday email settings include:

```json
{
  "mail_tone": "Friendly",
  "extra_guide": "Comprehensive guidance text with tone, word limits, timezone info",
  "org_timezone": "UTC+07",
  "maximum_words": 200,
  "birthday_email_check": {
    "is_enabled": true,
    "is_complete_prompt": false
  },
  "fewshots_strict_follow": false
}
```

### Field Descriptions

- **`mail_tone`**: Email tone (e.g., "Friendly", "Professional", "Warm")
- **`extra_guide`**: Comprehensive guidance text including tone, word limits, and timezone
- **`org_timezone`**: Organization timezone in UTC format (e.g., "UTC+07", "UTC-04")
- **`maximum_words`**: Maximum word count for birthday emails
- **`birthday_email_check`**: Object containing:
  - `is_enabled`: Whether birthday email functionality is enabled
  - `is_complete_prompt`: Whether the input is a complete prompt for writing content
- **`fewshots_strict_follow`**: Whether to strictly follow example templates

## CLI Commands

### Configure Birthday Email Settings

Configure birthday email settings for a team using AI-powered analysis:

```bash
python fusesell.py --openai-api-key "sk-your-key" settings birthday configure <team_id> \
  --org-id <org_id> \
  --prompt "Send friendly birthday greetings to customers, keep it under 200 words, use UTC+07 timezone, tone should be warm and professional"
```

**Parameters:**
- `team_id`: Team identifier
- `--org-id`: Organization identifier
- `--prompt`: Natural language prompt describing birthday email requirements

**Example:**
```bash
python fusesell.py --openai-api-key "sk-proj-abc123" settings birthday configure team_rta_20251017_175017 \
  --org-id rta \
  --prompt "Send warm birthday wishes, maximum 150 words, friendly tone, UTC+07 timezone"
```

### List Birthday Email Templates

List all birthday email templates:

```bash
python fusesell.py settings birthday list-templates [--team-id <team_id>] [--org-id <org_id>]
```

**Parameters:**
- `--team-id` (optional): Filter by team ID
- `--org-id` (optional): Filter by organization ID

**Example:**
```bash
python fusesell.py settings birthday list-templates --team-id team_rta_20251017_175017
```

### View Birthday Email Template

View a specific birthday email template:

```bash
python fusesell.py settings birthday view-template <template_id>
```

**Parameters:**
- `template_id`: Template identifier (e.g., "uuid:123e4567-e89b-12d3-a456-426614174000")

**Example:**
```bash
python fusesell.py settings birthday view-template uuid:123e4567-e89b-12d3-a456-426614174000
```

## Processing Logic

### 1. Prompt Validation

The system analyzes user input to determine:
- Whether it's a complete prompt for writing birthday email content
- Whether birthday email functionality should be enabled
- Configuration vs. content creation instructions

### 2. Settings Rule Generation

Based on the prompt, the system extracts:
- Email tone and style preferences
- Word limits and length constraints
- Timezone information
- Personalization requirements

### 3. Template Generation

If the prompt contains complete content instructions, the system:
- Generates a birthday email template using AI
- Creates placeholders for personalization
- Stores the template in the local database

## Template Structure

Generated birthday email templates include:

```json
{
  "template_id": "uuid:123e4567-e89b-12d3-a456-426614174000",
  "subject": "Happy Birthday from {{company_name}}!",
  "content": "Dear {{customer_name}},\n\nOn behalf of everyone at {{company_name}}...",
  "placeholders": ["customer_name", "company_name", "sender_name"],
  "tone": "professional_warm",
  "template_type": "birthday_email",
  "team_id": "uuid:987fcdeb-51a2-43d1-b456-426614174000",
  "org_id": "org_id",
  "created_at": "2025-10-17T10:50:17",
  "created_by": "username"
}
```

### Available Placeholders

Common placeholders for personalization:
- `{{customer_name}}`: Customer's name
- `{{company_name}}`: Your company name
- `{{sender_name}}`: Sender's name
- `{{customer_company}}`: Customer's company name

## Integration with Server Architecture

The birthday email system is designed to be compatible with the server-side flows:

### Related Server Flows
- `flowai/auto_interaction_generate_email_template.yml` - Template generation
- `flowai/customer_birthday_email_sender.yml` - Email sending
- `flowai/customer_birthday_reminder_task.yml` - Birthday reminders

### Server Compatibility
- Uses same settings structure as gs_scheduler.py
- Generates compatible template IDs
- Maintains same validation logic
- Supports same timezone formats

## Database Schema

The birthday email system creates the following table:

```sql
CREATE TABLE birthday_templates (
    template_id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    template_type TEXT DEFAULT 'birthday_email',
    subject TEXT,
    content TEXT,
    placeholders TEXT, -- JSON array
    tone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    prompt TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
```

## Usage Examples

### Example 1: Basic Birthday Email Configuration

```bash
python fusesell.py --openai-api-key "sk-proj-abc123" settings birthday configure team_sales_001 \
  --org-id mycompany \
  --prompt "Send friendly birthday greetings, keep under 200 words, UTC+07 timezone"
```

**Generated Settings:**
```json
{
  "mail_tone": "Friendly",
  "extra_guide": "Send friendly birthday greetings, keep under 200 words, UTC+07 timezone",
  "org_timezone": "UTC+07",
  "maximum_words": 200,
  "birthday_email_check": {
    "is_enabled": true,
    "is_complete_prompt": false
  },
  "fewshots_strict_follow": false
}
```

### Example 2: Complete Template Generation

```bash
python fusesell.py --openai-api-key "sk-proj-abc123" settings birthday configure team_sales_001 \
  --org-id mycompany \
  --prompt "Create a warm birthday email template. Start with 'Happy Birthday!' and mention our appreciation for their business. Keep it under 150 words, use a friendly but professional tone. Include a small gift or discount offer."
```

This will generate both settings and a complete email template.

### Example 3: Template Management

```bash
# List all templates
python fusesell.py settings birthday list-templates

# View specific template
python fusesell.py settings birthday view-template birthday_email__team_sales_001
```

## Best Practices

### 1. Prompt Writing
- Be specific about tone and style requirements
- Include word limits and timezone information
- Specify personalization requirements
- Mention any special offers or content to include

### 2. Template Management
- Use descriptive prompts for better template generation
- Review generated templates before use
- Keep templates updated with current branding

### 3. Settings Configuration
- Configure timezone based on your customer base
- Set appropriate word limits for your communication style
- Enable/disable features based on your needs

## Troubleshooting

### Common Issues

#### 1. "LLM API call failed"
**Cause**: Invalid API key or API quota exceeded
**Solution**: Verify API key and check OpenAI account status

#### 2. "Template generation failed"
**Cause**: Prompt too vague or API issues
**Solution**: Provide more specific prompt with clear requirements

#### 3. "Settings not saved"
**Cause**: Database connection issues or invalid team ID
**Solution**: Verify team exists and database is accessible

### Debug Mode

Enable debug logging for troubleshooting:
```bash
python fusesell.py --log-level DEBUG settings birthday configure ...
```

## Advanced Configuration

### Custom Timezone Formats
The system supports various timezone formats:
- `UTC+07`, `UTC-04` (preferred)
- `GMT+7`, `GMT-5`
- `+7`, `-4`
- `Asia/Bangkok`, `America/New_York`

### Multi-language Support
Configure birthday emails for different languages by specifying in the prompt:
```bash
--prompt "Create birthday email in Vietnamese, friendly tone, 200 words max, UTC+07"
```

This birthday email management system provides comprehensive functionality for creating, managing, and configuring birthday email templates while maintaining compatibility with the server-side FuseSell architecture.