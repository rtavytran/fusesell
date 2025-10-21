# FuseSell Local - Troubleshooting Guide

## Quick Diagnostics

### Health Check Commands

```bash
# Test basic functionality
python fusesell.py --help

# Test with dry run
python fusesell.py --openai-api-key "test" --org-id "test" --org-name "Test" \
  --full-input "Test input" --input-website "https://example.com" --dry-run

# Check scheduler status
python scheduler_service.py status

# Test database connectivity
python -c "from fusesell_local.utils.data_manager import DataManager; dm = DataManager(); print('Database OK')"
```

## Common Issues and Solutions

### 1. Installation and Setup Issues

#### Issue: "ModuleNotFoundError: No module named 'fusesell_local'"
**Symptoms:**
```
Traceback (most recent call last):
  File "fusesell.py", line 14, in <module>
    from fusesell_local.pipeline import FuseSellPipeline
ModuleNotFoundError: No module named 'fusesell_local'
```

**Causes:**
- Not running from the correct directory
- Python path issues
- Missing package installation

**Solutions:**
1. **Check directory**: Ensure you're in the `fusesell-local` directory
   ```bash
   cd fusesell-local
   ls -la  # Should see fusesell.py and fusesell_local/ directory
   ```

2. **Install in development mode**:
   ```bash
   pip install -e .
   ```

3. **Add to Python path**:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

#### Issue: "ImportError: No module named 'requests'"
**Symptoms:**
```
ImportError: No module named 'requests'
```

**Solution:**
```bash
pip install -r requirements.txt
```

#### Issue: Permission denied errors on Windows
**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: 'fusesell_data/fusesell.db'
```

**Solutions:**
1. **Run as administrator** (not recommended for regular use)
2. **Change data directory**:
   ```bash
   python fusesell.py --data-dir "C:\Users\%USERNAME%\fusesell_data" ...
   ```
3. **Fix permissions**:
   ```bash
   icacls fusesell_data /grant %USERNAME%:F /T
   ```

### 2. API and External Service Issues

#### Issue: "OpenAI API call failed"
**Symptoms:**
```
ExternalServiceError: OpenAI API call failed: Invalid API key
```

**Causes:**
- Invalid or expired API key
- Insufficient API credits
- Rate limiting
- Network connectivity issues

**Solutions:**
1. **Verify API key**:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        https://api.openai.com/v1/models
   ```

2. **Check API credits**: Visit OpenAI dashboard to verify billing

3. **Test with different model**:
   ```bash
   python fusesell.py --llm-model "gpt-3.5-turbo" ...
   ```

4. **Reduce request frequency**:
   ```bash
   python fusesell.py --max-retries 5 --temperature 0.3 ...
   ```

#### Issue: "Website scraping failed"
**Symptoms:**
```
WARNING: Could not scrape website https://example.com - no Serper API key available
```

**Causes:**
- Website blocking requests
- Network connectivity issues
- Missing Serper API key
- Invalid URL

**Solutions:**
1. **Test URL accessibility**:
   ```bash
   curl -I https://example.com
   ```

2. **Add Serper API key**:
   ```bash
   python fusesell.py --serper-api-key "your-serper-key" ...
   ```

3. **Try different URL format**:
   ```bash
   # Ensure URL includes protocol
   python fusesell.py --input-website "https://example.com" ...
   ```

4. **Use alternative data source**:
   ```bash
   python fusesell.py --input-description "Company info here" ...
   ```

### 3. OCR and Image Processing Issues

#### Issue: "Tesseract OCR not available"
**Symptoms:**
```
DEBUG: Tesseract OCR not available. Install with: pip install pytesseract pillow
```

**Solutions:**
1. **Install Python packages**:
   ```bash
   pip install pytesseract pillow
   ```

2. **Install Tesseract binary**:
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - **macOS**: `brew install tesseract`
   - **Ubuntu**: `sudo apt-get install tesseract-ocr`

3. **Configure Tesseract path** (Windows):
   ```python
   import pytesseract
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

#### Issue: "Business card processing failed"
**Symptoms:**
```
ERROR: Business card processing failed: HTTP Error 404: Not Found
```

**Causes:**
- Invalid image URL
- Image format not supported
- Network issues
- OCR engine failures

**Solutions:**
1. **Verify image URL**:
   ```bash
   curl -I https://example.com/business-card.jpg
   ```

2. **Check supported formats**: JPG, PNG, PDF are supported

3. **Try different OCR engine**:
   ```bash
   pip install easyocr  # Alternative OCR engine
   ```

4. **Test with local file**:
   ```bash
   # Copy image to local server and use local URL
   python -m http.server 8000
   # Then use http://localhost:8000/image.jpg
   ```

### 4. Database Issues

#### Issue: "Database connection failed"
**Symptoms:**
```
ERROR: Failed to initialize database: database is locked
```

**Causes:**
- Database file locked by another process
- Insufficient permissions
- Corrupted database file
- Disk space issues

**Solutions:**
1. **Check for running processes**:
   ```bash
   # Windows
   tasklist | findstr python
   
   # Linux/macOS
   ps aux | grep python
   ```

2. **Kill hanging processes**:
   ```bash
   # Kill specific process
   kill -9 <process_id>
   ```

3. **Reset database**:
   ```bash
   # Backup first
   cp fusesell_data/fusesell.db fusesell_data/fusesell.db.backup
   
   # Remove and recreate
   rm fusesell_data/fusesell.db
   python fusesell.py --dry-run  # This will recreate the database
   ```

4. **Check disk space**:
   ```bash
   df -h .  # Linux/macOS
   dir     # Windows
   ```

#### Issue: "SQLite version incompatibility"
**Symptoms:**
```
sqlite3.OperationalError: no such function: JSON_EXTRACT
```

**Solution:**
```bash
# Update SQLite
pip install --upgrade sqlite3

# Or use alternative approach without JSON functions
```

### 5. Email Scheduling Issues

#### Issue: "Email scheduling failed"
**Symptoms:**
```
ERROR: Email scheduling failed: No module named 'apscheduler'
```

**Solution:**
```bash
pip install APScheduler pytz
```

#### Issue: "Scheduler service won't start"
**Symptoms:**
```
ERROR: Failed to initialize scheduler: [Errno 98] Address already in use
```

**Causes:**
- Another scheduler instance running
- Port conflicts
- Permission issues

**Solutions:**
1. **Check running schedulers**:
   ```bash
   ps aux | grep scheduler_service
   ```

2. **Kill existing scheduler**:
   ```bash
   pkill -f scheduler_service
   ```

3. **Use different data directory**:
   ```bash
   python scheduler_service.py start --data-dir ./scheduler_data
   ```

#### Issue: "Timezone detection failed"
**Symptoms:**
```
WARNING: Unknown timezone 'Invalid/Timezone', using default
```

**Solutions:**
1. **Use standard timezone names**:
   ```bash
   python fusesell.py --customer-timezone "America/New_York" ...
   ```

2. **Check available timezones**:
   ```python
   import pytz
   print(pytz.all_timezones)
   ```

3. **Let system auto-detect**:
   ```bash
   # Don't specify timezone, let system detect from address
   python fusesell.py --input-description "Company in New York" ...
   ```

### 6. Memory and Performance Issues

#### Issue: "Memory error during processing"
**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Causes:**
- Large image files
- Insufficient RAM
- Memory leaks

**Solutions:**
1. **Reduce image size**:
   ```python
   # Images are automatically resized, but you can pre-process
   from PIL import Image
   img = Image.open('large_image.jpg')
   img.thumbnail((1024, 1024))
   img.save('smaller_image.jpg')
   ```

2. **Process in batches**:
   ```bash
   # Process one customer at a time instead of batch processing
   ```

3. **Increase virtual memory** (Windows):
   - Control Panel  System  Advanced  Performance Settings  Advanced  Virtual Memory

#### Issue: "Slow LLM responses"
**Symptoms:**
- Long wait times for API responses
- Timeout errors

**Solutions:**
1. **Reduce prompt length**:
   ```bash
   # Use more concise prompts in config/prompts.json
   ```

2. **Lower temperature**:
   ```bash
   python fusesell.py --temperature 0.3 ...
   ```

3. **Use faster model**:
   ```bash
   python fusesell.py --llm-model "gpt-3.5-turbo" ...
   ```

4. **Increase timeout**:
   ```bash
   python fusesell.py --max-retries 5 ...
   ```

### 7. Configuration Issues

#### Issue: "Invalid configuration format"
**Symptoms:**
```
json.JSONDecodeError: Expecting ',' delimiter
```

**Causes:**
- Malformed JSON in configuration files
- Missing commas or brackets
- Invalid escape characters

**Solutions:**
1. **Validate JSON**:
   ```bash
   python -m json.tool fusesell_data/config/prompts.json
   ```

2. **Reset to defaults**:
   ```bash
   # Backup current config
   cp fusesell_data/config/prompts.json fusesell_data/config/prompts.json.backup
   
   # Remove and let system recreate defaults
   rm fusesell_data/config/prompts.json
   python fusesell.py --dry-run
   ```

3. **Use JSON validator**: Online tools like jsonlint.com

#### Issue: "Team configuration not found"
**Symptoms:**
```
WARNING: No team configuration found for team_id: sales_team_1
```

**Solution:**
```bash
# Create team-specific configuration
python -c "
from fusesell_local.utils.event_scheduler import EventScheduler
scheduler = EventScheduler()
scheduler.create_scheduling_rule('your_org_id', 'sales_team_1', 
                                business_hours_start='09:00',
                                business_hours_end='17:00')
"
```

### 8. Action-Based Workflow Issues

#### Issue: "Draft not found for rewrite"
**Symptoms:**
```
ValueError: Draft not found: draft_abc123_1
```

**Causes:**
- Invalid draft ID
- Draft was deleted
- Database corruption

**Solutions:**
1. **List available drafts**:
   ```python
   from fusesell_local.utils.data_manager import DataManager
   dm = DataManager()
   drafts = dm.list_email_drafts()
   for draft in drafts:
       print(f"ID: {draft['draft_id']}, Subject: {draft['subject_lines'][0]}")
   ```

2. **Generate new drafts**:
   ```bash
   python fusesell.py --action draft_write ...
   ```

#### Issue: "Send action requires recipient address"
**Symptoms:**
```
ValueError: recipient_address is required for send action
```

**Solution:**
```bash
python fusesell.py --action send --selected-draft-id "draft_123" \
  --recipient-address "customer@company.com" --recipient-name "John Doe"
```

## Debug Mode and Logging

### Enable Debug Logging

```bash
# Maximum verbosity
python fusesell.py --log-level DEBUG --verbose

# Save logs to file
python fusesell.py --log-level DEBUG --log-file debug.log

# Monitor logs in real-time
tail -f fusesell_data/logs/fusesell.log
```

### Debug Information to Collect

When reporting issues, include:

1. **Command used**:
   ```bash
   python fusesell.py --your-command-here
   ```

2. **Error message** (full traceback)

3. **System information**:
   ```bash
   python --version
   pip list | grep -E "(openai|requests|beautifulsoup4|pytesseract|apscheduler)"
   ```

4. **Log files**:
   ```bash
   # Last 50 lines of log
   tail -50 fusesell_data/logs/fusesell.log
   ```

5. **Configuration** (sanitized, no API keys):
   ```bash
   ls -la fusesell_data/config/
   ```

## Performance Optimization

### Speed Up Processing

1. **Use dry-run for testing**:
   ```bash
   python fusesell.py --dry-run
   ```

2. **Skip unnecessary stages**:
   ```bash
   python fusesell.py --skip-stages follow_up
   ```

3. **Stop after specific stage**:
   ```bash
   python fusesell.py --stop-after lead_scoring
   ```

4. **Use faster LLM settings**:
   ```bash
   python fusesell.py --temperature 0.2 --llm-model "gpt-3.5-turbo"
   ```

### Reduce API Costs

1. **Use lower temperature**: `--temperature 0.3`
2. **Shorter prompts**: Edit `config/prompts.json`
3. **Cache results**: Results are automatically cached in database
4. **Use dry-run for development**: `--dry-run`

## Recovery Procedures

### Recover from Failed Execution

1. **Check execution status**:
   ```python
   from fusesell_local.utils.data_manager import DataManager
   dm = DataManager()
   executions = dm.get_recent_executions(limit=10)
   for exec in executions:
       print(f"ID: {exec['execution_id']}, Status: {exec['status']}")
   ```

2. **Continue from last successful stage**:
   ```bash
   python fusesell.py --continue-execution "exec_id_here"
   ```

3. **Restart with same data**:
   ```bash
   # Use same execution ID to overwrite
   python fusesell.py --execution-id "exec_id_here" --input-website "..."
   ```

### Database Recovery

1. **Backup database**:
   ```bash
   cp fusesell_data/fusesell.db fusesell_data/fusesell.db.backup
   ```

2. **Check database integrity**:
   ```bash
   sqlite3 fusesell_data/fusesell.db "PRAGMA integrity_check;"
   ```

3. **Repair database**:
   ```bash
   sqlite3 fusesell_data/fusesell.db ".recover" | sqlite3 fusesell_data/fusesell_recovered.db
   ```

## Getting Help

### Self-Help Resources

1. **Built-in help**: `python fusesell.py --help`
2. **API Documentation**: `API_DOCUMENTATION.md`
3. **User Guide**: `README.md` and `HELP.md`
4. **Status Information**: `STATUS.md`

### Diagnostic Commands

```bash
# System health check
python -c "
import sys
print(f'Python: {sys.version}')
try:
    import openai
    print('OpenAI: OK')
except ImportError:
    print('OpenAI: Missing')
try:
    import requests
    print('Requests: OK')
except ImportError:
    print('Requests: Missing')
try:
    from fusesell_local.pipeline import FuseSellPipeline
    print('FuseSell: OK')
except ImportError as e:
    print(f'FuseSell: Error - {e}')
"

# Database check
python -c "
from fusesell_local.utils.data_manager import DataManager
try:
    dm = DataManager()
    print('Database: OK')
    print(f'Tables: {dm.get_table_names()}')
except Exception as e:
    print(f'Database: Error - {e}')
"

# Scheduler check
python -c "
try:
    from fusesell_local.utils.event_scheduler import EventScheduler
    scheduler = EventScheduler()
    print('Event Scheduler: OK')
    events = scheduler.get_scheduled_events()
    print(f'Scheduled jobs: {len(jobs)}')
    scheduler.shutdown()
except Exception as e:
    print(f'Scheduler: Error - {e}')
"
```

### When to Seek Additional Help

- Persistent errors after following troubleshooting steps
- Performance issues that can't be resolved with optimization
- Integration questions for specific use cases
- Custom development requirements

Remember to sanitize any logs or error messages before sharing - remove API keys, personal information, and sensitive data.