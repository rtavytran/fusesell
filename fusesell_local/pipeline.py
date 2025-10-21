"""
FuseSell Pipeline Orchestrator
Manages the execution of all pipeline stages in sequence
"""

from typing import Dict, Any, List, Optional
import time
from datetime import datetime
import uuid

from .stages import (
    DataAcquisitionStage,
    DataPreparationStage,
    LeadScoringStage,
    InitialOutreachStage,
    FollowUpStage
)
from .utils.data_manager import LocalDataManager
from .utils.logger import get_logger, log_execution_start, log_execution_complete
from .utils.validators import InputValidator


class FuseSellPipeline:
    """
    Main pipeline orchestrator for FuseSell local execution.
    Manages stage execution, data flow, and error handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize pipeline with configuration.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.execution_id = config.get('execution_id') or self._generate_execution_id()
        self.logger = get_logger("pipeline")
        
        # Initialize components
        self.data_manager = LocalDataManager(config.get('data_dir', './fusesell_data'))
        self.validator = InputValidator()
        
        # Initialize stages
        self.stages = self._initialize_stages()
        
        # Execution state
        self.stage_results = {}
        self.start_time = None
        self.end_time = None
    
    def _initialize_stages(self) -> List:
        """
        Initialize all pipeline stages.
        
        Returns:
            List of initialized stage instances
        """
        stages = []
        
        # Only initialize stages that are not skipped
        skip_stages = self.config.get('skip_stages', [])
        stop_after = self.config.get('stop_after')
        
        stage_classes = [
            ('data_acquisition', DataAcquisitionStage),
            ('data_preparation', DataPreparationStage),
            ('lead_scoring', LeadScoringStage),
            ('initial_outreach', InitialOutreachStage),
            ('follow_up', FollowUpStage)
        ]
        
        for stage_name, stage_class in stage_classes:
            if stage_name not in skip_stages:
                try:
                    # Pass shared data_manager instance to avoid multiple database initializations
                    stage = stage_class(self.config, self.data_manager)
                    stages.append(stage)
                    self.logger.debug(f"Initialized {stage_name} stage with shared data manager")
                except Exception as e:
                    self.logger.error(f"Failed to initialize {stage_name} stage: {str(e)}")
                    raise
            
            # Stop adding stages if we've reached the stop point
            if stop_after == stage_name:
                break
        
        return stages
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute the complete pipeline or continue existing execution.
        
        Returns:
            Dictionary containing execution results
        """
        self.start_time = time.time()
        
        try:
            # Check if this is a continuation
            if self.config.get('continue_execution'):
                return self._continue_execution()
            
            # New execution flow
            # Validate configuration
            self._validate_configuration()
            
            # Log execution start
            log_execution_start(self.execution_id, self.config)
            
            # Save execution record
            self._save_execution_record()
            
            # Create execution context
            context = self._create_execution_context()
            
            # Execute stages sequentially
            runtime_index = 0
            for stage in self.stages:
                # Add runtime_index to context for operation tracking
                context['runtime_index'] = runtime_index
                
                stage_result = self._execute_stage(stage, context)
                
                # Update context with stage results
                context['stage_results'][stage.stage_name] = stage_result
                
                # Update task runtime index
                try:
                    self.data_manager.update_task_status(
                        task_id=self.execution_id,
                        status="running",
                        runtime_index=runtime_index
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to update task runtime index: {str(e)}")
                
                # Check if pipeline should stop
                if stage.should_stop_pipeline(stage_result):
                    self.logger.warning(f"Pipeline stopped after {stage.stage_name} stage")
                    break
                
                runtime_index += 1
            
            # Compile final results
            results = self._compile_results(context)
            
            # Note: executions is now a view - status updated via llm_worker_task
            
            # Update task status (correct schema)
            try:
                self.data_manager.update_task_status(
                    task_id=self.execution_id,
                    status="completed",
                    runtime_index=runtime_index
                )
            except Exception as e:
                self.logger.warning(f"Failed to update final task status: {str(e)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            
            # Update task status to failed
            try:
                self.data_manager.update_task_status(
                    task_id=self.execution_id,
                    status="failed",
                    runtime_index=0
                )
            except Exception as update_error:
                self.logger.warning(f"Failed to update task status to failed: {str(update_error)}")
            
            error_result = {
                'error': str(e),
                'error_type': type(e).__name__,
                'stage_results': self.stage_results
            }
            
            return error_result
            
        finally:
            self.end_time = time.time()
            duration = self.end_time - self.start_time if self.start_time else 0
            
            status = 'completed' if not hasattr(self, '_failed') else 'failed'
            log_execution_complete(self.execution_id, status, duration)
            
            # Generate performance analytics
            self._log_performance_analytics(duration)
    
    def _log_performance_analytics(self, total_duration: float) -> None:
        """
        Log detailed performance analytics for the pipeline execution.
        
        Args:
            total_duration: Total pipeline execution time in seconds
        """
        try:
            # Collect timing data from stage results
            stage_timings = []
            total_stage_time = 0.0
            
            for stage_name, result in self.stage_results.items():
                if isinstance(result, dict) and 'timing' in result:
                    timing = result['timing']
                    duration = timing.get('duration_seconds', 0.0)
                    stage_timings.append({
                        'stage': stage_name,
                        'duration': duration,
                        'percentage': (duration / total_duration * 100) if total_duration > 0 else 0
                    })
                    total_stage_time += duration
            
            # Log performance summary
            self.logger.info("=" * 60)
            self.logger.info(f"PERFORMANCE ANALYTICS - Execution {self.execution_id}")
            self.logger.info("=" * 60)
            self.logger.info(f"Total Pipeline Duration: {total_duration:.2f} seconds")
            self.logger.info(f"Total Stage Duration: {total_stage_time:.2f} seconds")
            
            if total_duration > 0:
                overhead = total_duration - total_stage_time
                overhead_pct = (overhead / total_duration * 100)
                self.logger.info(f"Pipeline Overhead: {overhead:.2f} seconds ({overhead_pct:.1f}%)")
            
            self.logger.info("-" * 40)
            self.logger.info("Stage Performance Breakdown:")
            
            for timing in sorted(stage_timings, key=lambda x: x['duration'], reverse=True):
                self.logger.info(f"  {timing['stage']:<20}: {timing['duration']:>6.2f}s ({timing['percentage']:>5.1f}%)")
            
            # Performance insights
            if stage_timings:
                slowest_stage = max(stage_timings, key=lambda x: x['duration'])
                fastest_stage = min(stage_timings, key=lambda x: x['duration'])
                
                self.logger.info("-" * 40)
                self.logger.info(f"Slowest Stage: {slowest_stage['stage']} ({slowest_stage['duration']:.2f}s)")
                self.logger.info(f"Fastest Stage: {fastest_stage['stage']} ({fastest_stage['duration']:.2f}s)")
                
                if slowest_stage['duration'] > 0 and fastest_stage['duration'] > 0:
                    ratio = slowest_stage['duration'] / fastest_stage['duration']
                    self.logger.info(f"Performance Ratio: {ratio:.1f}x difference")
            
            # Validation: Total time should roughly equal sum of stage durations
            if total_duration > 0:
                time_discrepancy = abs(total_duration - total_stage_time)
                discrepancy_percentage = (time_discrepancy / total_duration * 100)
                
                self.logger.info("-" * 40)
                self.logger.info("TIMING VALIDATION:")
                if discrepancy_percentage < 5.0:
                    self.logger.info(f"✅ Timing validation PASSED (discrepancy: {discrepancy_percentage:.1f}%)")
                else:
                    self.logger.warning(f"⚠️  Timing validation WARNING (discrepancy: {discrepancy_percentage:.1f}%)")
                    self.logger.warning(f"   Expected ~{total_stage_time:.2f}s, got {total_duration:.2f}s")
            
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.warning(f"Failed to generate performance analytics: {str(e)}")

    def _generate_performance_analytics(self, total_duration: float) -> Dict[str, Any]:
        """
        Generate performance analytics data for inclusion in results.
        
        Args:
            total_duration: Total pipeline execution time in seconds
            
        Returns:
            Performance analytics dictionary
        """
        try:
            # Collect timing data from stage results
            stage_timings = []
            total_stage_time = 0.0
            
            for stage_name, result in self.stage_results.items():
                if isinstance(result, dict) and 'timing' in result:
                    timing = result['timing']
                    duration = timing.get('duration_seconds', 0.0)
                    stage_timings.append({
                        'stage': stage_name,
                        'duration_seconds': duration,
                        'percentage_of_total': (duration / total_duration * 100) if total_duration > 0 else 0,
                        'start_time': timing.get('start_time'),
                        'end_time': timing.get('end_time')
                    })
                    total_stage_time += duration
            
            # Calculate overhead
            overhead = total_duration - total_stage_time
            overhead_percentage = (overhead / total_duration * 100) if total_duration > 0 else 0
            
            # Find performance insights
            insights = {}
            if stage_timings:
                slowest_stage = max(stage_timings, key=lambda x: x['duration_seconds'])
                fastest_stage = min(stage_timings, key=lambda x: x['duration_seconds'])
                
                insights = {
                    'slowest_stage': {
                        'name': slowest_stage['stage'],
                        'duration_seconds': slowest_stage['duration_seconds']
                    },
                    'fastest_stage': {
                        'name': fastest_stage['stage'],
                        'duration_seconds': fastest_stage['duration_seconds']
                    },
                    'performance_ratio': (slowest_stage['duration_seconds'] / fastest_stage['duration_seconds']) 
                                       if fastest_stage['duration_seconds'] > 0 else 0
                }
            
            return {
                'total_duration_seconds': total_duration,
                'total_stage_duration_seconds': total_stage_time,
                'pipeline_overhead_seconds': overhead,
                'pipeline_overhead_percentage': overhead_percentage,
                'stage_count': len(stage_timings),
                'average_stage_duration': total_stage_time / len(stage_timings) if stage_timings else 0,
                'stage_timings': stage_timings,
                'performance_insights': insights,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to generate performance analytics data: {str(e)}")
            return {
                'error': str(e),
                'total_duration_seconds': total_duration,
                'generated_at': datetime.now().isoformat()
            }

    def _validate_configuration(self) -> None:
        """
        Validate pipeline configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        errors = self.validator.validate_config(self.config)
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_msg)
    
    def _create_execution_context(self) -> Dict[str, Any]:
        """
        Create execution context for pipeline stages.
        
        Returns:
            Execution context dictionary
        """
        return {
            'execution_id': self.execution_id,
            'config': self.config,
            'input_data': self._extract_input_data(),
            'stage_results': {},
            'data_manager': self.data_manager,
            'start_time': self.start_time
        }
    
    def _extract_input_data(self) -> Dict[str, Any]:
        """
        Extract input data from configuration.
        
        Returns:
            Input data dictionary
        """
        return {
            'org_id': self.config['org_id'],
            'org_name': self.config['org_name'],
            'team_id': self.config.get('team_id'),
            'team_name': self.config.get('team_name'),
            'project_code': self.config.get('project_code'),
            'staff_name': self.config.get('staff_name', 'Sales Team'),
            'language': self.config.get('language', 'english'),
            # Data sources (matching executor schema)
            'input_website': self.config.get('input_website', ''),
            'input_description': self.config.get('input_description', ''),
            'input_business_card': self.config.get('input_business_card', ''),
            'input_linkedin_url': self.config.get('input_linkedin_url', ''),
            'input_facebook_url': self.config.get('input_facebook_url', ''),
            'input_freetext': self.config.get('input_freetext', ''),
            
            # Context fields
            'customer_id': self.config.get('customer_id', 'null'),
            'full_input': self.config.get('full_input'),
            
            # Action and continuation fields (for server executor compatibility)
            'action': self.config.get('action', 'draft_write'),
            'selected_draft_id': self.config.get('selected_draft_id', ''),
            'reason': self.config.get('reason', ''),
            'recipient_address': self.config.get('recipient_address', ''),
            'recipient_name': self.config.get('recipient_name', ''),
            'interaction_type': self.config.get('interaction_type', 'email'),
            'human_action_id': self.config.get('human_action_id', ''),

            # Scheduling preferences
            'send_immediately': self.config.get('send_immediately', False),
            'customer_timezone': self.config.get('customer_timezone', ''),
            'business_hours_start': self.config.get('business_hours_start', '08:00'),
            'business_hours_end': self.config.get('business_hours_end', '20:00'),
            'delay_hours': self.config.get('delay_hours', 2)
        }
    
    def _execute_stage(self, stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single pipeline stage with business logic validation.
        
        Args:
            stage: Stage instance to execute
            context: Execution context
            
        Returns:
            Stage execution result
        """
        stage_start_time = time.time()
        
        operation_id = None
        try:
            self.logger.info(f"Executing {stage.stage_name} stage")
            
            # Apply business logic pre-checks
            if not self._should_execute_stage(stage.stage_name, context):
                skip_result = {
                    'status': 'skipped',
                    'reason': 'Business logic condition not met',
                    'stage': stage.stage_name,
                    'timestamp': datetime.now().isoformat()
                }
                self.stage_results[stage.stage_name] = skip_result
                return skip_result
            
            # Prepare stage input
            stage_input = self._prepare_stage_input(stage.stage_name, context)
            validation_errors = self.validator.validate_stage_input(stage.stage_name, stage_input)
            
            if validation_errors:
                error_msg = f"Stage input validation failed: {'; '.join(validation_errors)}"
                raise ValueError(error_msg)
            
            # Create operation record (server-compatible tracking)
            try:
                runtime_index = context.get('runtime_index', 0)
                chain_index = len([s for s in self.stage_results.keys()])  # Current position in chain
                
                operation_id = self.data_manager.create_operation(
                    task_id=self.execution_id,
                    executor_name=stage.stage_name,
                    runtime_index=runtime_index,
                    chain_index=chain_index,
                    input_data=stage_input
                )
                
                # Add operation_id to context for stage use
                context['operation_id'] = operation_id
                
            except Exception as e:
                self.logger.warning(f"Failed to create operation record: {str(e)}")
                operation_id = None
            
            # Execute stage with timing
            result = stage.execute_with_timing(context)
            
            # Update operation with success result
            if operation_id:
                try:
                    self.data_manager.update_operation_status(
                        operation_id=operation_id,
                        execution_status='done',
                        output_data=result
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to update operation status: {str(e)}")
            
            # Apply business logic post-checks
            if self._should_stop_after_stage(stage.stage_name, result, context):
                result['pipeline_stop'] = True
                result['stop_reason'] = self._get_stop_reason(stage.stage_name, result)
            
            # Save stage result if configured (backward compatibility)
            if self.config.get('save_intermediate', True):
                stage.save_stage_result(context, result)
            
            # Store result
            self.stage_results[stage.stage_name] = result
            
            return result
            
        except Exception as e:
            stage.log_stage_error(context, e)
            
            error_result = stage.create_error_result(e, context)
            self.stage_results[stage.stage_name] = error_result
            
            # Update operation with failure result
            if operation_id:
                try:
                    error_output = {
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'stage': stage.stage_name,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.data_manager.update_operation_status(
                        operation_id=operation_id,
                        execution_status='failed',
                        output_data=error_output
                    )
                except Exception as update_error:
                    self.logger.warning(f"Failed to update operation failure status: {str(update_error)}")
            
            # Save error result (backward compatibility)
            if self.config.get('save_intermediate', True):
                stage.save_stage_result(context, error_result)
            
            raise
            
        finally:
            stage_duration = time.time() - stage_start_time
            self.logger.debug(f"Stage {stage.stage_name} completed in {stage_duration:.2f} seconds")
    
    def _prepare_stage_input(self, stage_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare input data for a specific stage.
        
        Args:
            stage_name: Name of the stage
            context: Execution context
            
        Returns:
            Stage-specific input data
        """
        base_input = context['input_data'].copy()
        stage_results = context['stage_results']
        
        # Add stage-specific data based on previous results
        if stage_name == 'data_preparation' and 'data_acquisition' in stage_results:
            acquisition_result = stage_results['data_acquisition']
            if acquisition_result.get('status') == 'success':
                base_input['raw_customer_data'] = acquisition_result.get('data', {})
        
        elif stage_name == 'lead_scoring' and 'data_preparation' in stage_results:
            prep_result = stage_results['data_preparation']
            if prep_result.get('status') == 'success':
                prep_data = prep_result.get('data', {})
                base_input.update(prep_data)
        
        elif stage_name == 'initial_outreach':
            # Combine data from previous stages
            if 'data_preparation' in stage_results:
                prep_data = stage_results['data_preparation'].get('data', {})
                base_input['customer_data'] = prep_data
            
            if 'lead_scoring' in stage_results:
                scoring_data = stage_results['lead_scoring'].get('data', {})
                base_input['lead_scores'] = scoring_data.get('scores', [])
        
        elif stage_name == 'follow_up':
            # Add interaction history from previous outreach
            if 'initial_outreach' in stage_results:
                outreach_data = stage_results['initial_outreach'].get('data', {})
                base_input['previous_interactions'] = [outreach_data]
        
        return base_input
    
    def _compile_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compile final execution results.
        
        Args:
            context: Execution context
            
        Returns:
            Compiled results dictionary
        """
        duration = time.time() - self.start_time if self.start_time else 0
        
        # Determine overall status
        status = 'completed'
        for stage_result in self.stage_results.values():
            if stage_result.get('status') in ['error', 'fail']:
                status = 'failed'
                break
        
        # Extract key data from stage results
        customer_data = {}
        lead_scores = []
        email_drafts = []
        
        for stage_name, result in self.stage_results.items():
            if result.get('status') == 'success':
                data = result.get('data', {})
                
                if stage_name == 'data_preparation':
                    customer_data = data
                elif stage_name == 'lead_scoring':
                    lead_scores = data.get('scores', [])
                elif stage_name == 'initial_outreach':
                    email_drafts.extend(data.get('drafts', []))
                elif stage_name == 'follow_up':
                    email_drafts.extend(data.get('drafts', []))
        
        # Generate performance analytics
        performance_analytics = self._generate_performance_analytics(duration)
        
        return {
            'execution_id': self.execution_id,
            'status': status,
            'started_at': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            'completed_at': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            'duration_seconds': duration,
            'performance_analytics': performance_analytics,
            'config': {
                'org_id': self.config['org_id'],
                'org_name': self.config['org_name'],
                'input_website': self.config.get('input_website'),
                'language': self.config.get('language', 'english')
            },
            'stage_results': self.stage_results,
            'customer_data': customer_data,
            'lead_scores': lead_scores,
            'email_drafts': email_drafts,
            'stages_executed': list(self.stage_results.keys()),
            'stages_successful': [
                name for name, result in self.stage_results.items() 
                if result.get('status') == 'success'
            ]
        }
    
    def _save_execution_record(self) -> None:
        """Save initial task record to database (server-compatible schema)."""
        try:
            # Create server-compatible request body
            request_body = {
                'org_id': self.config['org_id'],
                'org_name': self.config.get('org_name'),
                'team_id': self.config.get('team_id'),
                'team_name': self.config.get('team_name'),
                'project_code': self.config.get('project_code'),
                'staff_name': self.config.get('staff_name', 'Sales Team'),
                'language': self.config.get('language', 'english'),
                'customer_info': self.config.get('input_description', ''),
                'input_website': self.config.get('input_website', ''),
                'input_description': self.config.get('input_description', ''),
                'input_business_card': self.config.get('input_business_card', ''),
                'input_linkedin_url': self.config.get('input_linkedin_url', ''),
                'input_facebook_url': self.config.get('input_facebook_url', ''),
                'input_freetext': self.config.get('input_freetext', ''),
                'full_input': self.config.get('full_input', ''),
                'action': self.config.get('action', 'draft_write'),
                'execution_id': self.execution_id
            }
            
            # Save as task using server-compatible schema
            self.data_manager.create_task(
                task_id=self.execution_id,
                plan_id=self.config.get('plan_id', '569cdcbd-cf6d-4e33-b0b2-d2f6f15a0832'),
                org_id=self.config['org_id'],
                request_body=request_body,
                status="running"
            )
            
            # Note: executions is now a view that maps to llm_worker_task
            # No need for separate executions table save
                
        except Exception as e:
            self.logger.error(f"Failed to save task record: {str(e)}")
            raise
    
    def _update_execution_status(self, status: str, results: Dict[str, Any]) -> None:
        """
        Update execution status in database.
        
        Args:
            status: Execution status
            results: Execution results
        """
        try:
            self.data_manager.update_execution_status(
                execution_id=self.execution_id,
                status=status,
                results=results
            )
        except Exception as e:
            self.logger.warning(f"Failed to update execution status: {str(e)}")
    
    def _should_execute_stage(self, stage_name: str, context: Dict[str, Any]) -> bool:
        """
        Apply business logic to determine if a stage should execute.
        
        Args:
            stage_name: Name of the stage
            context: Execution context
            
        Returns:
            True if stage should execute, False otherwise
        """
        stage_results = context.get('stage_results', {})
        
        # Data Acquisition: Always execute if it's the first stage
        if stage_name == 'dataacquisition':
            return True
        
        # Data Preparation: Requires successful Data Acquisition
        if stage_name == 'datapreparation':
            acquisition_result = stage_results.get('dataacquisition', {})
            return acquisition_result.get('status') == 'success'
        
        # Lead Scoring: Requires successful Data Preparation
        if stage_name == 'leadscoring':
            prep_result = stage_results.get('datapreparation', {})
            return prep_result.get('status') == 'success'
        
        # Initial Outreach: Requires successful Lead Scoring
        if stage_name == 'initialoutreach':
            scoring_result = stage_results.get('leadscoring', {})
            return scoring_result.get('status') == 'success'
        
        # Follow Up: Requires successful Initial Outreach
        if stage_name == 'followup':
            outreach_result = stage_results.get('initialoutreach', {})
            return outreach_result.get('status') == 'success'
        
        return True
    
    def _should_stop_after_stage(self, stage_name: str, result: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Apply business logic to determine if pipeline should stop after a stage.
        
        Args:
            stage_name: Name of the completed stage
            result: Stage execution result
            context: Execution context
            
        Returns:
            True if pipeline should stop, False otherwise
        """
        # Critical stop condition: Data Acquisition website failure
        if stage_name == 'dataacquisition':
            if result.get('data', {}).get('status_info_website') == 'fail':
                self.logger.warning("Data Acquisition failed: website extraction failed")
                return True
        
        # Business rule: Stop after Initial Outreach draft generation (human-in-the-loop)
        if stage_name == 'initial_outreach':
            if result.get('status') == 'success':
                action = result.get('data', {}).get('action', 'draft_write')
                if action == 'draft_write':
                    self.logger.info("Stopping after Initial Outreach draft generation for human review")
                    return True
        
        # Stop on any error
        if result.get('status') in ['error', 'fail']:
            return True
        
        return False
    
    def _get_stop_reason(self, stage_name: str, result: Dict[str, Any]) -> str:
        """
        Get the reason for stopping the pipeline.
        
        Args:
            stage_name: Name of the stage that triggered the stop
            result: Stage execution result
            
        Returns:
            Human-readable stop reason
        """
        if stage_name == 'dataacquisition':
            if result.get('data', {}).get('status_info_website') == 'fail':
                return "Website extraction failed in Data Acquisition stage"
        
        if stage_name == 'initial_outreach':
            action = result.get('data', {}).get('action', 'draft_write')
            if action == 'draft_write':
                return "Draft generated in Initial Outreach - waiting for human review"
        
        if result.get('status') in ['error', 'fail']:
            return f"Stage {stage_name} failed with error: {result.get('error_message', 'Unknown error')}"
        
        return "Pipeline stopped due to business logic condition"
    
    def _continue_execution(self) -> Dict[str, Any]:
        """
        Continue an existing execution with a specific action.
        
        Returns:
            Dictionary containing execution results
        """
        continue_execution_id = self.config['continue_execution']
        action = self.config['action']
        
        self.logger.info(f"Continuing execution {continue_execution_id} with action: {action}")
        
        try:
            # Load existing execution data
            existing_execution = self.data_manager.get_execution(continue_execution_id)
            if not existing_execution:
                raise ValueError(f"Execution {continue_execution_id} not found")
            
            # Load previous stage results
            stage_results = self.data_manager.get_stage_results(continue_execution_id)
            
            # Create continuation context
            context = self._create_continuation_context(existing_execution, stage_results)
            
            # Determine which stage to execute based on action
            target_stage = self._get_target_stage_for_action(action)
            
            if not target_stage:
                raise ValueError(f"No suitable stage found for action: {action}")
            
            # Execute the specific action
            stage_result = self._execute_continuation_action(target_stage, context, action)
            
            # Update execution record
            self._update_execution_status('continued', {
                'action': action,
                'stage': target_stage.stage_name,
                'result': stage_result,
                'continued_from': continue_execution_id
            })
            
            return {
                'execution_id': self.execution_id,
                'continued_from': continue_execution_id,
                'action': action,
                'status': 'completed',
                'result': stage_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to continue execution: {str(e)}")
            error_result = {
                'execution_id': self.execution_id,
                'continued_from': continue_execution_id,
                'action': action,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self._update_execution_status('failed', error_result)
            return error_result
    
    def _create_continuation_context(self, existing_execution: Dict[str, Any], stage_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create execution context for continuation.
        
        Args:
            existing_execution: Previous execution record
            stage_results: Previous stage results
            
        Returns:
            Continuation context
        """
        # Reconstruct stage results dictionary
        results_dict = {}
        for result in stage_results:
            stage_name = result['stage_name']
            results_dict[stage_name] = result['output_data']
        
        return {
            'execution_id': self.execution_id,
            'original_execution_id': existing_execution['execution_id'],
            'config': self.config,
            'original_config': existing_execution.get('config', {}),
            'stage_results': results_dict,
            'continuation_action': self.config['action'],
            'draft_id': self.config.get('draft_id'),
            'reason': self.config.get('reason', ''),
            'start_time': self.start_time
        }
    
    def _get_target_stage_for_action(self, action: str):
        """
        Get the appropriate stage for the given action.
        
        Args:
            action: Action to perform
            
        Returns:
            Stage instance or None
        """
        # Map actions to stages
        action_stage_map = {
            'draft_write': 'initialoutreach',
            'draft_rewrite': 'initialoutreach', 
            'send': 'initialoutreach',
            'close': 'initialoutreach'
        }
        
        target_stage_name = action_stage_map.get(action)
        if not target_stage_name:
            return None
        
        # Find the stage instance
        for stage in self.stages:
            if stage.stage_name == target_stage_name:
                return stage
        
        return None
    
    def _execute_continuation_action(self, stage, context: Dict[str, Any], action: str) -> Dict[str, Any]:
        """
        Execute a specific continuation action.
        
        Args:
            stage: Stage instance to execute
            context: Continuation context
            action: Specific action to perform
            
        Returns:
            Action execution result
        """
        self.logger.info(f"Executing continuation action: {action}")
        
        # Add action-specific context
        context['action'] = action
        context['is_continuation'] = True
        
        # Execute the stage with continuation context and timing
        return stage.execute_with_timing(context)
    
    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"fusesell_{timestamp}_{unique_id}"
