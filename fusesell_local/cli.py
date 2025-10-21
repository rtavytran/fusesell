#!/usr/bin/env python3
"""
FuseSell Local - Command-line interface for local sales automation pipeline
"""

import argparse
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime

from .api import (
    build_config as build_pipeline_config,
    configure_logging as configure_pipeline_logging,
    prepare_data_directory,
    validate_config as validate_pipeline_config,
)
from .pipeline import FuseSellPipeline
from .utils.validators import InputValidator


class FuseSellCLI:
    """
    Command-line interface for FuseSell local execution.
    Handles argument parsing, validation, and pipeline orchestration.
    """

    def __init__(self):
        """Initialize CLI with argument parser."""
        self.parser = self._setup_argument_parser()
        self.logger = None  # Will be initialized after parsing args

    def _setup_argument_parser(self) -> argparse.ArgumentParser:
        """
        Set up command-line argument parser with subcommands.

        Returns:
            Configured ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            description='FuseSell Local - AI-powered sales automation pipeline',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # PIPELINE EXECUTION
  python fusesell.py pipeline --openai-api-key sk-xxx --org-id rta --org-name "RTA Corp" \\
                     --full-input "Seller: RTA Corp, Customer: Example Company, Communication: English" \\
                     --input-website "https://example.com"
  
  # TEAM MANAGEMENT
  python fusesell.py team create --name "Sales Team A" --description "Primary sales team" \\
                     --org-id rta --plan-id plan-123
  python fusesell.py team list --org-id rta
  python fusesell.py team describe team-456
  
  # PRODUCT MANAGEMENT
  python fusesell.py product create --name "FuseSell Pro" --description "Advanced sales automation" \\
                     --org-id rta --product-data '{"category":"Sales Automation"}'
  python fusesell.py product list --org-id rta
  
  # SETTINGS MANAGEMENT
  python fusesell.py settings set team-456 --setting-name product_settings \\
                     --value-json '[{"product_id": "prod-123"}]'
  python fusesell.py settings view team-456 --setting-name product_settings
  
  # BIRTHDAY EMAIL MANAGEMENT
  python fusesell.py settings birthday configure team-456 --org-id rta \\
                     --prompt "Send friendly birthday greetings, max 200 words, UTC+07"
  python fusesell.py settings birthday list-templates --team-id team-456
  python fusesell.py settings birthday view-template birthday_email__team-456
            """
        )

        # Add subcommands (optional for backward compatibility)
        subparsers = parser.add_subparsers(
            dest='command', help='Available commands', required=False)

        # Team management subcommand
        team_parser = subparsers.add_parser('team', help='Manage teams')
        self._add_team_arguments(team_parser)

        # Product management subcommand
        product_parser = subparsers.add_parser(
            'product', help='Manage products')
        self._add_product_arguments(product_parser)

        # Settings management subcommand
        settings_parser = subparsers.add_parser(
            'settings', help='Manage team settings')
        self._add_settings_arguments(settings_parser)

        # Add pipeline arguments directly to main parser for backward compatibility
        self._add_pipeline_arguments(parser)

        return parser

    def _add_pipeline_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add pipeline-specific arguments."""

        # Required arguments (for pipeline execution)
        required = parser.add_argument_group(
            'pipeline arguments (required for pipeline execution)')
        required.add_argument(
            '--openai-api-key',
            help='OpenAI API key for LLM processing'
        )
        required.add_argument(
            '--org-id',
            help='Organization ID (seller identifier)'
        )
        required.add_argument(
            '--org-name',
            help='Organization name (seller name)'
        )

        # Data source fields (at least one required) - matching executor schema
        data_sources = parser.add_argument_group(
            'data sources (at least one required)')
        data_sources.add_argument(
            '--input-website',
            help='The URL of the website. If no URL is provided, the return value will be empty (maps to input_website)'
        )
        data_sources.add_argument(
            '--input-description',
            help='Full information about the customer. Such as name, phone, email, address, taxcode, another info... (maps to input_description)'
        )
        data_sources.add_argument(
            '--input-business-card',
            help='The image URL of the business card. If no image URL is provided, the return value will be empty (maps to input_business_card)'
        )
        data_sources.add_argument(
            '--input-facebook-url',
            help='Valid URL pointing to a personal profile or business page on Facebook (maps to input_facebook_url)'
        )
        data_sources.add_argument(
            '--input-linkedin-url',
            help='Valid URL pointing to a personal profile or business page on LinkedIn (maps to input_linkedin_url)'
        )
        data_sources.add_argument(
            '--input-freetext',
            help='Free text input with customer information (maps to input_freetext from executor schema)'
        )

        # Required context fields (matching executor schema)
        context_group = parser.add_argument_group(
            'context fields (required for pipeline execution)')
        context_group.add_argument(
            '--full-input',
            help='Full information input. Includes: Seller, Customer and Communication information'
        )

        # Optional context fields
        optional_context = parser.add_argument_group('optional context')
        optional_context.add_argument(
            '--customer-id',
            help='ID of customer, if not provided, return null'
        )

        # Team and project settings
        team_group = parser.add_argument_group('team settings')
        team_group.add_argument(
            '--team-id',
            help='Team ID for team-specific configurations'
        )
        team_group.add_argument(
            '--team-name',
            help='Team name for team-specific configurations'
        )
        team_group.add_argument(
            '--project-code',
            help='Project code for organization'
        )
        team_group.add_argument(
            '--staff-name',
            default='Sales Team',
            help='Staff member name for email signatures (default: Sales Team)'
        )

        # Processing options
        processing_group = parser.add_argument_group('processing options')
        processing_group.add_argument(
            '--language',
            default='english',
            choices=['english', 'vietnamese', 'spanish', 'french', 'german'],
            help='Language for communication and processing (default: english)'
        )
        processing_group.add_argument(
            '--skip-stages',
            nargs='*',
            choices=['data_acquisition', 'data_preparation',
                     'lead_scoring', 'initial_outreach', 'follow_up'],
            help='Stages to skip during execution'
        )
        processing_group.add_argument(
            '--stop-after',
            choices=['data_acquisition', 'data_preparation',
                     'lead_scoring', 'initial_outreach', 'follow_up'],
            help='Stop pipeline after specified stage'
        )

        # Process continuation and action options (matching server executor schema)
        continuation_group = parser.add_argument_group(
            'process continuation and actions')
        continuation_group.add_argument(
            '--continue-execution',
            help='Continue an existing execution by providing execution ID'
        )
        continuation_group.add_argument(
            '--action',
            choices=['draft_write', 'draft_rewrite', 'send', 'close'],
            default='draft_write',
            help='Action to perform: draft_write (generate new drafts), draft_rewrite (modify existing), send (send approved draft), close (close outreach)'
        )
        continuation_group.add_argument(
            '--selected-draft-id',
            help='ID of existing draft to rewrite or send (required for draft_rewrite and send actions)'
        )
        continuation_group.add_argument(
            '--reason',
            help='Reason for the action (e.g., "customer requested more info", "make tone more casual")'
        )
        continuation_group.add_argument(
            '--recipient-address',
            help='Email address of the recipient (required for send action)'
        )
        continuation_group.add_argument(
            '--recipient-name',
            help='Name of the recipient (optional for send action)'
        )
        continuation_group.add_argument(
            '--interaction-type',
            default='email',
            help='Type of interaction (default: email)'
        )
        continuation_group.add_argument(
            '--send-immediately',
            action='store_true',
            help='Send email immediately instead of scheduling for optimal time'
        )
        continuation_group.add_argument(
            '--customer-timezone',
            help='Customer timezone (e.g., America/New_York, Europe/London). Auto-detected if not provided'
        )
        continuation_group.add_argument(
            '--business-hours-start',
            default='08:00',
            help='Business hours start time in HH:MM format (default: 08:00)'
        )
        continuation_group.add_argument(
            '--business-hours-end',
            default='20:00',
            help='Business hours end time in HH:MM format (default: 20:00)'
        )
        continuation_group.add_argument(
            '--delay-hours',
            type=int,
            default=2,
            help='Default delay in hours before sending (default: 2)'
        )
        continuation_group.add_argument(
            '--human-action-id',
            help='ID of the human action event (for server integration)'
        )

        # Output and storage options
        output_group = parser.add_argument_group('output options')
        output_group.add_argument(
            '--output-format',
            choices=['json', 'text', 'yaml'],
            default='json',
            help='Output format for results (default: json)'
        )
        output_group.add_argument(
            '--data-dir',
            default='./fusesell_data',
            help='Directory for local data storage (default: ./fusesell_data)'
        )
        output_group.add_argument(
            '--execution-id',
            help='Custom execution ID (auto-generated if not provided)'
        )
        output_group.add_argument(
            '--save-intermediate',
            action='store_true',
            help='Save intermediate results from each stage'
        )

        # Logging and debugging
        debug_group = parser.add_argument_group('logging and debugging')
        debug_group.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO',
            help='Logging level (default: INFO)'
        )
        debug_group.add_argument(
            '--log-file',
            help='Log file path (logs to console if not specified)'
        )
        debug_group.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        debug_group.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate inputs and show execution plan without running'
        )

        # Advanced options
        advanced_group = parser.add_argument_group('advanced options')
        advanced_group.add_argument(
            '--llm-model',
            default='gpt-4o-mini',
            help='LLM model to use (default: gpt-4o-mini)'
        )
        advanced_group.add_argument(
            '--llm-base-url',
            help='Custom LLM API base URL'
        )
        advanced_group.add_argument(
            '--temperature',
            type=float,
            default=0.7,
            help='LLM temperature for creativity (0.0-2.0, default: 0.7)'
        )
        advanced_group.add_argument(
            '--max-retries',
            type=int,
            default=3,
            help='Maximum retries for API calls (default: 3)'
        )
        advanced_group.add_argument(
            '--serper-api-key',
            help='Serper API key for enhanced web scraping and company research (optional)'
        )

    def _add_team_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add team management arguments."""
        team_subparsers = parser.add_subparsers(
            dest='team_action', help='Team actions')

        # Team create
        create_parser = team_subparsers.add_parser(
            'create', help='Create a new team')
        create_parser.add_argument('--name', required=True, help='Team name')
        create_parser.add_argument('--description', help='Team description')
        create_parser.add_argument(
            '--org-id', required=True, help='Organization ID')
        create_parser.add_argument(
            '--org-name', required=True, help='Organization name')
        create_parser.add_argument('--plan-id', required=True, help='Plan ID')
        create_parser.add_argument('--plan-name', help='Plan name')
        create_parser.add_argument('--project-code', help='Project code')
        create_parser.add_argument('--avatar', help='Avatar URL')

        # Team update
        update_parser = team_subparsers.add_parser(
            'update', help='Update an existing team')
        update_parser.add_argument('team_id', help='Team ID to update')
        update_parser.add_argument('--name', help='New team name')
        update_parser.add_argument(
            '--description', help='New team description')
        update_parser.add_argument('--plan-name', help='New plan name')
        update_parser.add_argument('--project-code', help='New project code')
        update_parser.add_argument('--avatar', help='New avatar URL')

        # Team list
        list_parser = team_subparsers.add_parser('list', help='List teams')
        list_parser.add_argument(
            '--org-id', required=True, help='Organization ID')

        # Team describe
        describe_parser = team_subparsers.add_parser(
            'describe', help='Show team details')
        describe_parser.add_argument('team_id', help='Team ID to describe')

    def _add_product_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add product management arguments."""
        product_subparsers = parser.add_subparsers(
            dest='product_action', help='Product actions')

        # Product create
        create_parser = product_subparsers.add_parser(
            'create', help='Create a new product')
        create_parser.add_argument(
            '--name', required=True, help='Product name')
        create_parser.add_argument('--description', help='Product description')
        create_parser.add_argument(
            '--org-id', required=True, help='Organization ID')
        create_parser.add_argument(
            '--org-name', required=True, help='Organization name')
        create_parser.add_argument(
            '--product-data', help='Additional product data as JSON')
        create_parser.add_argument('--category', help='Product category')
        create_parser.add_argument('--subcategory', help='Product subcategory')
        create_parser.add_argument('--project-code', help='Project code')

        # Product update
        update_parser = product_subparsers.add_parser(
            'update', help='Update an existing product')
        update_parser.add_argument('product_id', help='Product ID to update')
        update_parser.add_argument('--name', help='New product name')
        update_parser.add_argument(
            '--description', help='New product description')
        update_parser.add_argument(
            '--product-data', help='Updated product data as JSON')
        update_parser.add_argument('--category', help='New product category')
        update_parser.add_argument(
            '--subcategory', help='New product subcategory')

        # Product list
        list_parser = product_subparsers.add_parser(
            'list', help='List products')
        list_parser.add_argument(
            '--org-id', required=True, help='Organization ID')

    def _add_settings_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add settings management arguments."""
        settings_subparsers = parser.add_subparsers(
            dest='settings_action', help='Settings actions')

        # Settings set (for simple settings)
        set_parser = settings_subparsers.add_parser(
            'set', help='Set team setting (for simple settings)')
        set_parser.add_argument('team_id', help='Team ID')
        set_parser.add_argument('--setting-name', required=True,
                                choices=['gs_team_organization', 'gs_team_rep', 'gs_team_product',
                                         'gs_team_schedule_time', 'gs_team_auto_interaction',
                                         'gs_team_followup_schedule_time', 'gs_team_birthday_email'],
                                help='Setting name to update')
        set_parser.add_argument(
            '--value-json', required=True, help='Setting value as JSON')

        # Settings configure (for complex settings like initial_outreach and follow_up)
        configure_parser = settings_subparsers.add_parser(
            'configure', help='Configure complex team settings')
        configure_parser.add_argument('team_id', help='Team ID')
        configure_parser.add_argument('--setting-type', required=True,
                                      choices=[
                                          'initial_outreach', 'follow_up'],
                                      help='Type of setting to configure')
        configure_parser.add_argument('--user-input', required=True,
                                      help='User instructions, prompt, or guidance for the setting')
        configure_parser.add_argument('--examples-files', nargs='*',
                                      help='Paths to example email files (optional)')
        configure_parser.add_argument('--template-mode', choices=['ai_enhancement', 'strict_template'],
                                      default='ai_enhancement',
                                      help='Template processing mode (default: ai_enhancement)')

        # Settings view
        view_parser = settings_subparsers.add_parser(
            'view', help='View team setting')
        view_parser.add_argument('team_id', help='Team ID')
        view_parser.add_argument('--setting-name', required=True,
                                 choices=['gs_team_organization', 'gs_team_rep', 'gs_team_product',
                                          'gs_team_schedule_time', 'gs_team_initial_outreach', 'gs_team_follow_up',
                                          'gs_team_auto_interaction', 'gs_team_followup_schedule_time', 'gs_team_birthday_email'],
                                 help='Setting name to view')

        # Birthday email management
        birthday_parser = settings_subparsers.add_parser(
            'birthday', help='Manage birthday email settings and templates')
        birthday_subparsers = birthday_parser.add_subparsers(
            dest='birthday_action', help='Birthday email actions')

        # Birthday configure
        birthday_configure_parser = birthday_subparsers.add_parser(
            'configure', help='Configure birthday email settings')
        birthday_configure_parser.add_argument('team_id', help='Team ID')
        birthday_configure_parser.add_argument('--prompt', required=True,
                                             help='Birthday email configuration prompt')
        birthday_configure_parser.add_argument('--org-id', required=True,
                                             help='Organization ID')

        # Birthday template list
        birthday_list_parser = birthday_subparsers.add_parser(
            'list-templates', help='List birthday email templates')
        birthday_list_parser.add_argument('--team-id', help='Filter by team ID')
        birthday_list_parser.add_argument('--org-id', help='Filter by organization ID')

        # Birthday template view
        birthday_view_parser = birthday_subparsers.add_parser(
            'view-template', help='View birthday email template')
        birthday_view_parser.add_argument('template_id', help='Template ID to view')

    def parse_args(self, args: Optional[list] = None) -> argparse.Namespace:
        """
        Parse command-line arguments.

        Args:
            args: Optional list of arguments (uses sys.argv if None)

        Returns:
            Parsed arguments namespace
        """
        return self.parser.parse_args(args)

    def validate_args(self, args: argparse.Namespace) -> bool:
        """
        Validate parsed arguments.

        Args:
            args: Parsed arguments

        Returns:
            True if arguments are valid, False otherwise
        """
        validator = InputValidator()

        # Validate required fields
        if not validator.validate_api_key(args.openai_api_key):
            print("Error: Invalid OpenAI API key format", file=sys.stderr)
            return False

        # Different validation for new vs continuation processes
        if args.continue_execution:
            # Continuation mode - validate continuation parameters
            if not args.action:
                print(
                    "Error: --action is required when continuing an execution", file=sys.stderr)
                print(
                    "Available actions: draft_write, draft_rewrite, send, close", file=sys.stderr)
                return False

            if args.action in ['draft_rewrite', 'send'] and not args.selected_draft_id:
                print(
                    f"Error: --selected-draft-id is required for action '{args.action}'", file=sys.stderr)
                return False

            if args.action == 'send' and not args.recipient_address:
                print(
                    f"Error: --recipient-address is required for action '{args.action}'", file=sys.stderr)
                return False
        else:
            # New process mode - validate data sources (matching executor schema)
            data_sources = [
                args.input_website,
                args.input_description,
                args.input_business_card,
                args.input_linkedin_url,
                args.input_facebook_url,
                args.input_freetext
            ]

            if not any(data_sources):
                print(
                    "Error: At least one data source is required for new processes:", file=sys.stderr)
                print("  - Website URL (--input-website)", file=sys.stderr)
                print("  - Customer description (--input-description)",
                      file=sys.stderr)
                print("  - Business card URL (--input-business-card)",
                      file=sys.stderr)
                print("  - LinkedIn URL (--input-linkedin-url)", file=sys.stderr)
                print("  - Facebook URL (--input-facebook-url)", file=sys.stderr)
                print("  - Free text input (--input-freetext)", file=sys.stderr)
                print("", file=sys.stderr)
                print(
                    "To continue an existing process, use --continue-execution with --action", file=sys.stderr)
                return False

        # Validate URLs if provided
        if args.input_website and not validator.validate_url(args.input_website):
            print(
                f"Error: Invalid website URL: {args.input_website}", file=sys.stderr)
            return False

        if args.input_business_card and not validator.validate_url(args.input_business_card):
            print(
                f"Error: Invalid business card URL: {args.input_business_card}", file=sys.stderr)
            return False

        if args.input_linkedin_url and not validator.validate_url(args.input_linkedin_url):
            print(
                f"Error: Invalid LinkedIn URL: {args.input_linkedin_url}", file=sys.stderr)
            return False

        if args.input_facebook_url and not validator.validate_url(args.input_facebook_url):
            print(
                f"Error: Invalid Facebook URL: {args.input_facebook_url}", file=sys.stderr)
            return False

        # Validate recipient email if provided
        if hasattr(args, 'recipient_address') and args.recipient_address and not validator.validate_email(args.recipient_address):
            print(
                f"Error: Invalid recipient email: {args.recipient_address}", file=sys.stderr)
            return False

        # Validate temperature range
        if not (0.0 <= args.temperature <= 2.0):
            print(
                f"Error: Temperature must be between 0.0 and 2.0, got: {args.temperature}", file=sys.stderr)
            return False

        return True

    def create_config(self, args: argparse.Namespace) -> Dict[str, Any]:
        """
        Create configuration dictionary from parsed arguments.

        Args:
            args: Parsed arguments

        Returns:
            Configuration dictionary
        """
        return build_pipeline_config(args)

    def setup_logging(self, config: Dict[str, Any]) -> None:
        """
        Set up logging based on configuration.

        Args:
            config: Configuration dictionary
        """
        self.logger = configure_pipeline_logging(config)

    def validate_configuration(self, config: Dict[str, Any]) -> tuple[bool, list]:
        """
        Comprehensive configuration validation.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return validate_pipeline_config(config)

    def setup_output_directories(self, config: Dict[str, Any]) -> None:
        """
        Set up output directories based on configuration.

        Args:
            config: Configuration dictionary
        """
        try:
            data_dir = prepare_data_directory(config)
            print(f"Output directories set up in: {data_dir}")
        except Exception as e:
            print(
                f"Failed to set up output directories: {str(e)}", file=sys.stderr)
            raise

    def print_execution_plan(self, config: Dict[str, Any]) -> None:
        """
        Print execution plan for dry run.

        Args:
            config: Configuration dictionary
        """
        print("FuseSell Execution Plan")
        print("=" * 50)
        print(f"Execution ID: {config['execution_id']}")
        print(f"Organization: {config['org_name']} ({config['org_id']})")

        # Display data sources
        data_sources = []
        if config.get('input_website'):
            data_sources.append(f"Website: {config['input_website']}")
        if config.get('input_description'):
            data_sources.append(
                f"Description: {config['input_description'][:50]}...")
        if config.get('input_business_card'):
            data_sources.append(
                f"Business Card: {config['input_business_card']}")
        if config.get('input_linkedin_url'):
            data_sources.append(f"LinkedIn: {config['input_linkedin_url']}")
        if config.get('input_facebook_url'):
            data_sources.append(f"Facebook: {config['input_facebook_url']}")

        print(
            f"Data Sources: {'; '.join(data_sources) if data_sources else 'None'}")
        print(f"Language: {config['language']}")
        print(f"Data Directory: {config['data_dir']}")
        print(f"Output Format: {config['output_format']}")

        if config['team_id']:
            print(f"Team: {config['team_name']} ({config['team_id']})")

        print("\nPipeline Stages:")
        stages = ['data_acquisition', 'data_preparation',
                  'lead_scoring', 'initial_outreach', 'follow_up']
        skip_stages = config.get('skip_stages', [])
        stop_after = config.get('stop_after')

        for i, stage in enumerate(stages, 1):
            status = "SKIP" if stage in skip_stages else "RUN"
            print(f"  {i}. {stage.replace('_', ' ').title()}: {status}")

            if stop_after == stage:
                print(f"  Pipeline will stop after {stage}")
                break

        print(f"\nConfiguration saved to: {config['data_dir']}/config/")
        print("Run without --dry-run to execute the pipeline.")

    def format_output(self, results: Dict[str, Any], format_type: str) -> str:
        """
        Format execution results for output.

        Args:
            results: Execution results
            format_type: Output format (json, text, yaml)

        Returns:
            Formatted output string
        """
        if format_type == 'json':
            return json.dumps(results, indent=2, default=str)

        elif format_type == 'yaml':
            try:
                import yaml
                return yaml.dump(results, default_flow_style=False)
            except ImportError:
                self.logger.warning(
                    "PyYAML not installed, falling back to JSON")
                return json.dumps(results, indent=2, default=str)

        elif format_type == 'text':
            return self._format_text_output(results)

        else:
            return json.dumps(results, indent=2, default=str)

    def _format_text_output(self, results: Dict[str, Any]) -> str:
        """
        Format results as human-readable text.

        Args:
            results: Execution results

        Returns:
            Formatted text output
        """
        output = []
        output.append("FuseSell Execution Results")
        output.append("=" * 50)

        # Basic info
        output.append(f"Execution ID: {results.get('execution_id', 'N/A')}")
        output.append(f"Status: {results.get('status', 'N/A')}")
        output.append(f"Started: {results.get('started_at', 'N/A')}")
        output.append(f"Completed: {results.get('completed_at', 'N/A')}")
        output.append("")

        # Stage results
        stage_results = results.get('stage_results', {})
        if stage_results:
            output.append("Stage Results:")
            output.append("-" * 20)
            for stage, result in stage_results.items():
                status = result.get('status', 'unknown')
                output.append(
                    f"{stage.replace('_', ' ').title()}: {status.upper()}")

                if status == 'error' and result.get('error_message'):
                    output.append(f"  Error: {result['error_message']}")

        # Customer info
        customer_data = results.get('customer_data', {})
        if customer_data:
            output.append("\nCustomer Information:")
            output.append("-" * 20)
            output.append(
                f"Company: {customer_data.get('company_name', 'N/A')}")
            output.append(f"Industry: {customer_data.get('industry', 'N/A')}")
            output.append(f"Website: {customer_data.get('website', 'N/A')}")

        # Lead scores
        lead_scores = results.get('lead_scores', [])
        if lead_scores:
            output.append("\nLead Scores:")
            output.append("-" * 20)
            for score in lead_scores:
                output.append(
                    f"Product {score.get('product_id', 'N/A')}: {score.get('score', 0)}/100")

        # Email drafts
        email_drafts = results.get('email_drafts', [])
        if email_drafts:
            output.append("\nEmail Drafts Generated:")
            output.append("-" * 20)
            for draft in email_drafts:
                output.append(f"Subject: {draft.get('subject', 'N/A')}")
                output.append(f"Type: {draft.get('draft_type', 'N/A')}")

        return "\n".join(output)

    def run(self, args: Optional[list] = None) -> int:
        """
        Main execution method.

        Args:
            args: Optional command-line arguments

        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Parse arguments
            parsed_args = self.parse_args(args)

            # Handle different commands
            command = getattr(parsed_args, 'command', None)

            # If no command specified, default to pipeline for backward compatibility
            if command is None:
                # For backward compatibility, treat no subcommand as pipeline
                return self._run_pipeline(parsed_args)
            elif command == 'pipeline':
                return self._run_pipeline(parsed_args)
            elif command == 'team':
                return self._run_team_command(parsed_args)
            elif command == 'product':
                return self._run_product_command(parsed_args)
            elif command == 'settings':
                return self._run_settings_command(parsed_args)
            else:
                print(f"Unknown command: {command}", file=sys.stderr)
                return 1

        except KeyboardInterrupt:
            print("\nExecution interrupted by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return 1

    def _run_pipeline(self, args: argparse.Namespace) -> int:
        """Run the sales automation pipeline."""
        try:
            # Validate required pipeline arguments
            if not args.openai_api_key:
                print(
                    "Error: --openai-api-key is required for pipeline execution", file=sys.stderr)
                return 1
            if not args.org_id:
                print("Error: --org-id is required for pipeline execution",
                      file=sys.stderr)
                return 1
            if not args.org_name:
                print(
                    "Error: --org-name is required for pipeline execution", file=sys.stderr)
                return 1
            if not args.full_input:
                print(
                    "Error: --full-input is required for pipeline execution", file=sys.stderr)
                return 1

            if not self.validate_args(args):
                return 1

            # Create configuration
            config = self.create_config(args)

            # Set up output directories first
            self.setup_output_directories(config)

            # Set up logging (after log file path is configured)
            self.setup_logging(config)

            # Validate configuration
            config_valid, config_errors = self.validate_configuration(config)
            if not config_valid:
                print("Configuration validation failed:", file=sys.stderr)
                for error in config_errors:
                    print(f"  - {error}", file=sys.stderr)
                return 1

            self.logger.info(
                f"Starting FuseSell execution: {config['execution_id']}")

            # Handle dry run
            if config['dry_run']:
                self.print_execution_plan(config)
                return 0

            # Initialize and run pipeline
            pipeline = FuseSellPipeline(config)
            results = pipeline.execute()

            # Format and output results
            formatted_output = self.format_output(
                results, config['output_format'])
            print(formatted_output)

            # Return appropriate exit code
            if results.get('status') == 'completed':
                self.logger.info("FuseSell execution completed successfully")
                return 0
            else:
                self.logger.error("FuseSell execution failed")
                return 1

        except Exception as e:
            print(f"Pipeline error: {str(e)}", file=sys.stderr)
            return 1

    def _run_team_command(self, args: argparse.Namespace) -> int:
        """Handle team management commands."""
        from .utils.data_manager import LocalDataManager

        try:
            data_manager = LocalDataManager()
            action = getattr(args, 'team_action', None)

            if action == 'create':
                team_id = f"team_{args.org_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                data_manager.save_team(
                    team_id=team_id,
                    org_id=args.org_id,
                    org_name=args.org_name,
                    plan_id=args.plan_id,
                    name=args.name,
                    description=args.description,
                    plan_name=getattr(args, 'plan_name', None),
                    project_code=getattr(args, 'project_code', None),
                    avatar=getattr(args, 'avatar', None)
                )
                print(f"Team created successfully: {team_id}")
                return 0

            elif action == 'update':
                success = data_manager.update_team(
                    team_id=args.team_id,
                    name=getattr(args, 'name', None),
                    description=getattr(args, 'description', None),
                    plan_name=getattr(args, 'plan_name', None),
                    project_code=getattr(args, 'project_code', None),
                    avatar=getattr(args, 'avatar', None)
                )
                if success:
                    print(f"Team updated successfully: {args.team_id}")
                    return 0
                else:
                    print(f"Team not found: {args.team_id}", file=sys.stderr)
                    return 1

            elif action == 'list':
                teams = data_manager.list_teams(args.org_id)
                if teams:
                    print(f"Teams for organization {args.org_id}:")
                    for team in teams:
                        print(
                            f"  {team['team_id']}: {team['name']} - {team.get('description', 'No description')}")
                else:
                    print(f"No teams found for organization {args.org_id}")
                return 0

            elif action == 'describe':
                team = data_manager.get_team(args.team_id)
                if team:
                    print(json.dumps(team, indent=2, default=str))
                else:
                    print(f"Team not found: {args.team_id}", file=sys.stderr)
                    return 1
                return 0

            else:
                print(f"Unknown team action: {action}", file=sys.stderr)
                return 1

        except Exception as e:
            print(f"Team command error: {str(e)}", file=sys.stderr)
            return 1

    def _run_product_command(self, args: argparse.Namespace) -> int:
        """Handle product management commands."""
        from .utils.data_manager import LocalDataManager

        try:
            data_manager = LocalDataManager()
            action = getattr(args, 'product_action', None)

            if action == 'create':
                product_data = {
                    'org_id': args.org_id,
                    'org_name': args.org_name,
                    'productName': args.name,
                    'shortDescription': getattr(args, 'description', None),
                    'category': getattr(args, 'category', None),
                    'subcategory': getattr(args, 'subcategory', None),
                    'project_code': getattr(args, 'project_code', None)
                }

                # Parse additional product data if provided
                if hasattr(args, 'product_data') and args.product_data:
                    try:
                        additional_data = json.loads(args.product_data)
                        product_data.update(additional_data)
                    except json.JSONDecodeError:
                        print("Invalid JSON in --product-data", file=sys.stderr)
                        return 1

                product_id = data_manager.save_product(product_data)
                print(f"Product created successfully: {product_id}")
                return 0

            elif action == 'update':
                product_data = {}
                if hasattr(args, 'name') and args.name:
                    product_data['productName'] = args.name
                if hasattr(args, 'description') and args.description:
                    product_data['shortDescription'] = args.description
                if hasattr(args, 'category') and args.category:
                    product_data['category'] = args.category
                if hasattr(args, 'subcategory') and args.subcategory:
                    product_data['subcategory'] = args.subcategory

                # Parse additional product data if provided
                if hasattr(args, 'product_data') and args.product_data:
                    try:
                        additional_data = json.loads(args.product_data)
                        product_data.update(additional_data)
                    except json.JSONDecodeError:
                        print("Invalid JSON in --product-data", file=sys.stderr)
                        return 1

                success = data_manager.update_product(
                    args.product_id, product_data)
                if success:
                    print(f"Product updated successfully: {args.product_id}")
                    return 0
                else:
                    print(
                        f"Product not found: {args.product_id}", file=sys.stderr)
                    return 1

            elif action == 'list':
                products = data_manager.get_products_by_org(args.org_id)
                if products:
                    print(f"Products for organization {args.org_id}:")
                    for product in products:
                        print(
                            f"  {product['product_id']}: {product['product_name']} - {product.get('short_description', 'No description')}")
                else:
                    print(f"No products found for organization {args.org_id}")
                return 0

            else:
                print(f"Unknown product action: {action}", file=sys.stderr)
                return 1

        except Exception as e:
            print(f"Product command error: {str(e)}", file=sys.stderr)
            return 1

    def _run_settings_command(self, args: argparse.Namespace) -> int:
        """Handle settings management commands."""
        from .utils.data_manager import LocalDataManager

        try:
            data_manager = LocalDataManager()
            action = getattr(args, 'settings_action', None)

            if action == 'set':
                # Parse the JSON value
                try:
                    value = json.loads(args.value_json)
                except json.JSONDecodeError:
                    print("Invalid JSON in --value-json", file=sys.stderr)
                    return 1

                # Validate auto interaction settings format
                if args.setting_name == 'gs_team_auto_interaction':
                    validation_error = self._validate_auto_interaction_settings(value)
                    if validation_error:
                        print(f"Invalid auto interaction settings: {validation_error}", file=sys.stderr)
                        return 1

                # Get existing team settings or create new ones
                team_settings = data_manager.get_team_settings(args.team_id)
                if not team_settings:
                    # Get team info to create settings
                    team = data_manager.get_team(args.team_id)
                    if not team:
                        print(
                            f"Team not found: {args.team_id}", file=sys.stderr)
                        return 1

                    # Create new settings with all fields initialized
                    settings_kwargs = {
                        'team_id': args.team_id,
                        'org_id': team['org_id'],
                        'plan_id': team['plan_id'],
                        'team_name': team['name'],
                        'gs_team_organization': None,
                        'gs_team_rep': None,
                        'gs_team_product': None,
                        'gs_team_schedule_time': None,
                        'gs_team_initial_outreach': None,
                        'gs_team_follow_up': None,
                        'gs_team_auto_interaction': None,
                        'gs_team_followup_schedule_time': None,
                        'gs_team_birthday_email': None
                    }
                    # Set the specific setting being updated
                    settings_kwargs[args.setting_name] = value
                else:
                    # Update existing settings - preserve all existing values
                    settings_kwargs = {
                        'team_id': args.team_id,
                        'org_id': team_settings['org_id'],
                        'plan_id': team_settings['plan_id'],
                        'team_name': team_settings.get('team_name', ''),
                        'gs_team_organization': team_settings.get('gs_team_organization'),
                        'gs_team_rep': team_settings.get('gs_team_rep'),
                        'gs_team_product': team_settings.get('gs_team_product'),
                        'gs_team_schedule_time': team_settings.get('gs_team_schedule_time'),
                        'gs_team_initial_outreach': team_settings.get('gs_team_initial_outreach'),
                        'gs_team_follow_up': team_settings.get('gs_team_follow_up'),
                        'gs_team_auto_interaction': team_settings.get('gs_team_auto_interaction'),
                        'gs_team_followup_schedule_time': team_settings.get('gs_team_followup_schedule_time'),
                        'gs_team_birthday_email': team_settings.get('gs_team_birthday_email')
                    }
                    # Update only the specific setting being changed
                    settings_kwargs[args.setting_name] = value

                data_manager.save_team_settings(**settings_kwargs)
                print(
                    f"Setting '{args.setting_name}' updated for team {args.team_id}")
                return 0

            elif action == 'configure':
                # Handle complex settings configuration
                return self._configure_complex_setting(args, data_manager)

            elif action == 'view':
                team_settings = data_manager.get_team_settings(args.team_id)
                if team_settings and args.setting_name in team_settings:
                    setting_value = team_settings[args.setting_name]
                    print(json.dumps(setting_value, indent=2, default=str))
                else:
                    print(
                        f"Setting '{args.setting_name}' not found for team {args.team_id}", file=sys.stderr)
                    return 1
                return 0

            elif action == 'birthday':
                return self._run_birthday_email_command(args, data_manager)

            else:
                print(f"Unknown settings action: {action}", file=sys.stderr)
                return 1

        except Exception as e:
            print(f"Settings command error: {str(e)}", file=sys.stderr)
            return 1

    def _configure_complex_setting(self, args: argparse.Namespace, data_manager) -> int:
        """Configure complex settings like initial_outreach and follow_up."""
        try:
            # Determine if user input is a complete prompt or instructions
            user_input = args.user_input.strip()
            has_examples = bool(args.examples_files)

            # Process according to the flowchart logic
            if not has_examples:
                # Case 1: No Examples
                setting_value = self._process_no_examples_case(
                    user_input, args.setting_type)
            else:
                # Case 2 or 3: With Examples
                if args.template_mode == 'strict_template':
                    # Case 3: Strict Template Mode
                    setting_value = self._process_strict_template_case(
                        user_input, args.examples_files, args.setting_type)
                else:
                    # Case 2: AI Enhancement Mode
                    setting_value = self._process_ai_enhancement_case(
                        user_input, args.examples_files, args.setting_type)

            # Get team info for settings update
            team = data_manager.get_team(args.team_id)
            if not team:
                print(f"Team not found: {args.team_id}", file=sys.stderr)
                return 1

            # Get existing team settings or create new ones
            team_settings = data_manager.get_team_settings(args.team_id)

            # Determine the setting field name
            setting_field = f"gs_team_{args.setting_type}"

            if not team_settings:
                # Create new settings with all fields initialized
                settings_kwargs = {
                    'team_id': args.team_id,
                    'org_id': team['org_id'],
                    'plan_id': team['plan_id'],
                    'team_name': team['name'],
                    'gs_team_organization': None,
                    'gs_team_rep': None,
                    'gs_team_product': None,
                    'gs_team_schedule_time': None,
                    'gs_team_initial_outreach': None,
                    'gs_team_follow_up': None,
                    'gs_team_auto_interaction': None,
                    'gs_team_followup_schedule_time': None,
                    'gs_team_birthday_email': None
                }
                # Set the specific setting being updated
                settings_kwargs[setting_field] = setting_value
            else:
                # Update existing settings - preserve all existing values
                settings_kwargs = {
                    'team_id': args.team_id,
                    'org_id': team_settings['org_id'],
                    'plan_id': team_settings['plan_id'],
                    'team_name': team_settings.get('team_name', ''),
                    'gs_team_organization': team_settings.get('gs_team_organization'),
                    'gs_team_rep': team_settings.get('gs_team_rep'),
                    'gs_team_product': team_settings.get('gs_team_product'),
                    'gs_team_schedule_time': team_settings.get('gs_team_schedule_time'),
                    'gs_team_initial_outreach': team_settings.get('gs_team_initial_outreach'),
                    'gs_team_follow_up': team_settings.get('gs_team_follow_up'),
                    'gs_team_auto_interaction': team_settings.get('gs_team_auto_interaction'),
                    'gs_team_followup_schedule_time': team_settings.get('gs_team_followup_schedule_time'),
                    'gs_team_birthday_email': team_settings.get('gs_team_birthday_email')
                }
                # Update only the specific setting being changed
                settings_kwargs[setting_field] = setting_value

            data_manager.save_team_settings(**settings_kwargs)
            print(
                f"Complex setting '{args.setting_type}' configured for team {args.team_id}")
            print(
                f"Configuration: fewshots={setting_value.get('fewshots', False)}, strict_follow={setting_value.get('fewshots_strict_follow', False)}")
            return 0

        except Exception as e:
            print(f"Configuration error: {str(e)}", file=sys.stderr)
            return 1

    def _run_birthday_email_command(self, args: argparse.Namespace, data_manager) -> int:
        """Handle birthday email management commands."""
        from .utils.birthday_email_manager import BirthdayEmailManager

        try:
            birthday_manager = BirthdayEmailManager(self.create_config(args))
            birthday_action = getattr(args, 'birthday_action', None)

            if birthday_action == 'configure':
                # Configure birthday email settings
                result = birthday_manager.process_birthday_email_settings(
                    team_id=args.team_id,
                    prompt=args.prompt,
                    org_id=args.org_id
                )

                if result['success']:
                    # Save the generated settings to team settings
                    team = data_manager.get_team(args.team_id)
                    if not team:
                        print(f"Team not found: {args.team_id}", file=sys.stderr)
                        return 1

                    # Get existing team settings
                    team_settings = data_manager.get_team_settings(args.team_id)
                    
                    if not team_settings:
                        # Create new settings
                        settings_kwargs = {
                            'team_id': args.team_id,
                            'org_id': team['org_id'],
                            'plan_id': team['plan_id'],
                            'team_name': team['name'],
                            'gs_team_organization': None,
                            'gs_team_rep': None,
                            'gs_team_product': None,
                            'gs_team_schedule_time': None,
                            'gs_team_initial_outreach': None,
                            'gs_team_follow_up': None,
                            'gs_team_auto_interaction': None,
                            'gs_team_followup_schedule_time': None,
                            'gs_team_birthday_email': result['settings']
                        }
                    else:
                        # Update existing settings
                        settings_kwargs = {
                            'team_id': args.team_id,
                            'org_id': team_settings['org_id'],
                            'plan_id': team_settings['plan_id'],
                            'team_name': team_settings.get('team_name', ''),
                            'gs_team_organization': team_settings.get('gs_team_organization'),
                            'gs_team_rep': team_settings.get('gs_team_rep'),
                            'gs_team_product': team_settings.get('gs_team_product'),
                            'gs_team_schedule_time': team_settings.get('gs_team_schedule_time'),
                            'gs_team_initial_outreach': team_settings.get('gs_team_initial_outreach'),
                            'gs_team_follow_up': team_settings.get('gs_team_follow_up'),
                            'gs_team_auto_interaction': team_settings.get('gs_team_auto_interaction'),
                            'gs_team_followup_schedule_time': team_settings.get('gs_team_followup_schedule_time'),
                            'gs_team_birthday_email': result['settings']
                        }

                    data_manager.save_team_settings(**settings_kwargs)
                    
                    print(f"Birthday email settings configured for team {args.team_id}")
                    print(f"Settings: {json.dumps(result['settings'], indent=2)}")
                    
                    if result.get('template'):
                        print(f"Template generated: {result['template']['template_id']}")
                    
                    return 0
                else:
                    print(f"Birthday email configuration failed: {result.get('error', 'Unknown error')}", file=sys.stderr)
                    return 1

            elif birthday_action == 'list-templates':
                templates = birthday_manager.list_birthday_templates(
                    team_id=args.team_id,
                    org_id=args.org_id
                )
                
                if templates:
                    print("Birthday Email Templates:")
                    for template in templates:
                        print(f"  {template['template_id']}: {template.get('subject', 'No subject')} "
                              f"(Team: {template['team_id']}, Created: {template['created_at']})")
                else:
                    print("No birthday email templates found.")
                return 0

            elif birthday_action == 'view-template':
                template = birthday_manager.get_birthday_template(args.template_id)
                
                if template:
                    print(json.dumps(template, indent=2, default=str))
                else:
                    print(f"Template not found: {args.template_id}", file=sys.stderr)
                    return 1
                return 0

            else:
                print(f"Unknown birthday email action: {birthday_action}", file=sys.stderr)
                return 1

        except Exception as e:
            print(f"Birthday email command error: {str(e)}", file=sys.stderr)
            return 1

    def _process_no_examples_case(self, user_input: str, setting_type: str = "initial_outreach") -> dict:
        """Process Case 1: No Examples - determine if complete prompt or instructions."""
        # Simple heuristic to determine if it's a complete prompt or instructions
        is_complete_prompt = (
            len(user_input) > 100 and
            ('##' in user_input or 'create' in user_input.lower()
             or 'generate' in user_input.lower())
        )

        if is_complete_prompt:
            # Use message directly as prompt
            prompt = user_input
        else:
            # Use message + appropriate default prompt
            default_prompts = {
                "initial_outreach": "Create professional initial outreach emails for ##customer_name## on behalf of ##staff_name##.",
                "follow_up": "Create professional follow-up emails for ##customer_name## on behalf of ##staff_name##. Reference previous interactions and add new value."
            }
            default_prompt = default_prompts.get(
                setting_type, default_prompts["initial_outreach"])
            prompt = f"{default_prompt} Additional guidance: {user_input}"

        return {
            "fewshots": False,
            "fewshots_location": [],
            "fewshots_strict_follow": False,
            "prompt": prompt,
            "prompt_in_template": ""
        }

    def _process_ai_enhancement_case(self, user_input: str, examples_files: list, setting_type: str = "initial_outreach") -> dict:
        """Process Case 2: AI Enhancement Mode with examples."""
        email_type = "initial outreach" if setting_type == "initial_outreach" else "follow-up"
        return {
            "fewshots": True,
            "fewshots_location": examples_files,
            "fewshots_strict_follow": False,
            "prompt": f"Create {email_type} emails based on provided examples. Additional guidance: {user_input}",
            "prompt_in_template": "Use the provided examples as inspiration while incorporating the user guidance for improvements and customization."
        }

    def _process_strict_template_case(self, user_input: str, examples_files: list, setting_type: str = "initial_outreach") -> dict:
        """Process Case 3: Strict Template Mode with exact template following."""
        return {
            "fewshots": True,
            "fewshots_location": examples_files,
            "fewshots_strict_follow": True,
            "prompt": f"Use exact templates from examples for {setting_type}. Context: {user_input}",
            "prompt_in_template": "Mirror the EXACT CONTENT of provided examples with ZERO wording changes. Only replace the recipient to ##customer_name## from company ##company_name##.\n\nNO PLACEHOLDERS OR COMPANY NAMES AS GREETINGS:\n- Do not use [Contact Name], [Company], etc.\n- If recipient name is unclear, use \"Hi\" or \"Hello\" without a name\n- Never use company name as a greeting\n- No hyperlinks/attachments\n- No invented information\n\nReturn 1 JSON object which include these required fields: mail_tone, subject, body, priority_order, approach, product_mention, product_name, message_type, tags"
        }

    def _validate_auto_interaction_settings(self, value) -> str:
        """Validate auto interaction settings format.
        
        Expected format: [{"from_email": "value", "from_name": "value", "from_number": "value", 
                          "tool_type": "Email|Autocall|Notif|SMS", "email_cc": "comma,separated,emails", 
                          "email_bcc": "comma,separated,emails"}]
        
        Returns: Error message if invalid, None if valid
        """
        if not isinstance(value, list):
            return "Auto interaction settings must be a list"
        
        if len(value) == 0:
            return "Auto interaction settings list cannot be empty"
        
        valid_tool_types = ["Email", "Autocall", "Notif", "SMS"]
        required_fields = ["from_email", "from_name", "from_number", "tool_type", "email_cc", "email_bcc"]
        
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                return f"Item {i} must be an object/dictionary"
            
            # Check required fields
            for field in required_fields:
                if field not in item:
                    return f"Item {i} missing required field: {field}"
            
            # Validate tool_type
            if item["tool_type"] not in valid_tool_types:
                return f"Item {i} has invalid tool_type '{item['tool_type']}'. Must be one of: {', '.join(valid_tool_types)}"
            
            # Validate email format (basic check)
            if item["from_email"] and "@" not in item["from_email"]:
                return f"Item {i} has invalid from_email format"
            
            # Validate CC/BCC email lists (basic check)
            for email_field in ["email_cc", "email_bcc"]:
                if item[email_field]:  # Only validate if not empty
                    emails = [email.strip() for email in item[email_field].split(",")]
                    for email in emails:
                        if email and "@" not in email:
                            return f"Item {i} has invalid email in {email_field}: {email}"
        
        return None  # No errors


def main():
    """Main entry point for command-line execution."""
    cli = FuseSellCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
