#!/usr/bin/env python3
"""
FuseSell Local - Sales Process Query Tool
Query and analyze sales processes and their stage results.
"""

import argparse
import json
import sys
from pathlib import Path
from fusesell_local.utils.data_manager import LocalDataManager


def list_sales_processes(data_manager: LocalDataManager, org_id: str = None, limit: int = 10):
    """List recent sales processes."""
    print("📋 Recent Sales Processes:")
    print("=" * 80)
    
    tasks = data_manager.list_tasks(org_id=org_id, limit=limit)
    
    if not tasks:
        print("No sales processes found.")
        return
    
    for i, task in enumerate(tasks, 1):
        customer_info = ""
        if task.get('request_body') and task['request_body'].get('customer_info'):
            customer_info = task['request_body']['customer_info'][:50] + "..."
        
        print(f"{i}. Task ID: {task['task_id']}")
        print(f"   Customer: {customer_info}")
        print(f"   Status: {task['status']}")
        print(f"   Runtime Index: {task['current_runtime_index']}")
        print(f"   Created: {task['created_at']}")
        print()


def find_by_customer(data_manager: LocalDataManager, customer_name: str):
    """Find sales processes by customer name."""
    print(f"🔍 Sales Processes for Customer: '{customer_name}'")
    print("=" * 80)
    
    processes = data_manager.find_sales_processes_by_customer(customer_name)
    
    if not processes:
        print(f"No sales processes found for customer '{customer_name}'.")
        return
    
    for i, process in enumerate(processes, 1):
        print(f"{i}. Task ID: {process['task_id']}")
        print(f"   Status: {process['status']}")
        print(f"   Runtime Index: {process['current_runtime_index']}")
        print(f"   Created: {process['created_at']}")
        print()


def show_process_details(data_manager: LocalDataManager, task_id: str):
    """Show detailed information about a specific sales process using server-compatible schema."""
    print(f"📊 Sales Process Details: {task_id}")
    print("=" * 80)
    
    # Use new server-compatible method
    task_with_ops = data_manager.get_task_with_operations(task_id)
    
    if not task_with_ops:
        print(f"Sales process '{task_id}' not found.")
        return
    
    # Task Info
    print("📋 Task Information:")
    print(f"   Task ID: {task_with_ops['task_id']}")
    print(f"   Organization: {task_with_ops['org_id']}")
    print(f"   Status: {task_with_ops['status']}")
    print(f"   Current Stage: {task_with_ops['current_runtime_index']}")
    print(f"   Created: {task_with_ops['created_at']}")
    
    if task_with_ops.get('request_body'):
        rb = task_with_ops['request_body']
        print(f"   Customer: {rb.get('customer_info', 'N/A')}")
        print(f"   Language: {rb.get('language', 'N/A')}")
    
    print()
    
    # Stage Executions (Operations)
    print("🔄 Stage Executions:")
    operations = task_with_ops['operations']
    
    if not operations:
        print("   No stage executions found.")
    else:
        for operation in operations:
            status_icon = "✅" if operation['execution_status'] == 'done' else "❌" if operation['execution_status'] == 'failed' else "⏳"
            print(f"   {status_icon} {operation['executor_name']} (Runtime Index: {operation['runtime_index']})")
            print(f"      Status: {operation['execution_status']}")
            print(f"      Executed: {operation['date_created']}")
            
            # Show output summary if available
            if operation.get('output_data') and operation['output_data'].get('status'):
                print(f"      Result: {operation['output_data']['status']}")
            
            print()
    
    # Summary Stats
    stats = task_with_ops['summary']
    print("📈 Summary:")
    print(f"   Total Operations: {stats['total_operations']}")
    print(f"   Completed: {stats['completed_operations']}")
    print(f"   Failed: {stats['failed_operations']}")
    print(f"   Running: {stats['running_operations']}")
    
    # Get additional data using backward compatibility methods
    try:
        # Try to get lead scores and email drafts using existing methods
        import sqlite3
        conn = sqlite3.connect(data_manager.db_path)
        cursor = conn.cursor()
        
        # Lead scores
        cursor.execute("SELECT COUNT(*) FROM lead_scores WHERE execution_id = ?", (task_id,))
        lead_count = cursor.fetchone()[0]
        print(f"   Lead Scores: {lead_count}")
        
        # Email drafts
        cursor.execute("SELECT COUNT(*) FROM email_drafts WHERE execution_id = ?", (task_id,))
        draft_count = cursor.fetchone()[0]
        print(f"   Email Drafts: {draft_count}")
        
        conn.close()
    except Exception as e:
        print(f"   Additional data: Error loading ({str(e)})")
    
    print()



def show_stage_result(data_manager: LocalDataManager, task_id: str, stage_name: str):
    """Show detailed result for a specific stage using server-compatible schema."""
    print(f"🔍 Stage Result: {stage_name} for Task {task_id}")
    print("=" * 80)
    
    # Get operations for the task
    operations = data_manager.get_operations_by_task(task_id)
    
    # Find the specific stage operation
    target_operation = None
    for operation in operations:
        if stage_name.lower() in operation['executor_name'].lower():
            target_operation = operation
            break
    
    if not target_operation:
        print(f"Stage '{stage_name}' not found for task '{task_id}'.")
        print("Available stages:")
        for operation in operations:
            print(f"  - {operation['executor_name']}")
        return
    
    print(f"Stage: {target_operation['executor_name']}")
    print(f"Status: {target_operation['execution_status']}")
    print(f"Runtime Index: {target_operation['runtime_index']}")
    print(f"Chain Index: {target_operation['chain_index']}")
    print(f"Executed: {target_operation['date_created']}")
    print()
    
    # Show input data
    if target_operation.get('input_data'):
        print("📥 Input Data:")
        print(json.dumps(target_operation['input_data'], indent=2))
        print()
    
    # Show output data
    if target_operation.get('output_data'):
        print("📤 Output Data:")
        print(json.dumps(target_operation['output_data'], indent=2))
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Query FuseSell Local sales processes and stage results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List recent sales processes
  python query_sales_processes.py --list
  
  # Find processes for a specific customer
  python query_sales_processes.py --customer "Toni Wiggins"
  
  # Show detailed info for a specific process
  python query_sales_processes.py --details fusesell_20251009_180449_9f08569c
  
  # Show result for a specific stage
  python query_sales_processes.py --stage-result fusesell_20251009_180449_9f08569c data_acquisition
        """
    )
    
    parser.add_argument(
        '--data-dir',
        default='./fusesell_data',
        help='Data directory path (default: ./fusesell_data)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List recent sales processes'
    )
    
    parser.add_argument(
        '--customer',
        help='Find sales processes for a specific customer'
    )
    
    parser.add_argument(
        '--details',
        help='Show detailed information for a specific sales process (task ID)'
    )
    
    parser.add_argument(
        '--stage-result',
        nargs=2,
        metavar=('TASK_ID', 'STAGE_NAME'),
        help='Show detailed result for a specific stage (task_id stage_name)'
    )
    
    parser.add_argument(
        '--org-id',
        help='Filter by organization ID'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit number of results (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Initialize data manager
    try:
        data_manager = LocalDataManager(args.data_dir)
    except Exception as e:
        print(f"Error: Failed to initialize data manager: {e}", file=sys.stderr)
        return 1
    
    # Execute requested action
    try:
        if args.list:
            list_sales_processes(data_manager, args.org_id, args.limit)
        elif args.customer:
            find_by_customer(data_manager, args.customer)
        elif args.details:
            show_process_details(data_manager, args.details)
        elif args.stage_result:
            task_id, stage_name = args.stage_result
            show_stage_result(data_manager, task_id, stage_name)
        else:
            parser.print_help()
            return 1
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())