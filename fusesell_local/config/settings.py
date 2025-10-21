"""
Configuration Manager for FuseSell Local
Handles team-specific settings, prompts, and business rules
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging


class ConfigManager:
    """
    Manages configuration settings for FuseSell Local.
    Handles team-specific prompts, scoring criteria, and business rules.
    """
    
    def __init__(self, data_dir: str = "./fusesell_data"):
        """
        Initialize configuration manager.
        
        Args:
            data_dir: Directory containing configuration files
        """
        self.data_dir = Path(data_dir)
        self.config_dir = self.data_dir / "config"
        self.logger = logging.getLogger("fusesell.config")
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for loaded configurations
        self._cache = {}
    
    def get_prompts(self, team_id: Optional[str] = None, language: str = "english") -> Dict[str, Any]:
        """
        Get LLM prompts for stages, with team and language customization.
        
        Args:
            team_id: Optional team ID for team-specific prompts
            language: Language for prompts
            
        Returns:
            Dictionary of prompts organized by stage
        """
        cache_key = f"prompts_{team_id}_{language}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Load base prompts
        base_prompts = self._load_json_config("prompts.json", {})
        
        # Apply team customizations if available
        if team_id:
            team_prompts = self._load_team_prompts(team_id, language)
            base_prompts = self._merge_configs(base_prompts, team_prompts)
        
        # Apply language customizations
        if language != "english":
            lang_prompts = self._load_language_prompts(language)
            base_prompts = self._merge_configs(base_prompts, lang_prompts)
        
        self._cache[cache_key] = base_prompts
        return base_prompts
    
    def get_scoring_criteria(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get lead scoring criteria with team customization.
        
        Args:
            team_id: Optional team ID for team-specific criteria
            
        Returns:
            Dictionary of scoring criteria and weights
        """
        cache_key = f"scoring_{team_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Load base scoring criteria
        base_criteria = self._load_json_config("scoring_criteria.json", {})
        
        # Apply team customizations if available
        if team_id:
            team_criteria = self._load_team_scoring(team_id)
            base_criteria = self._merge_configs(base_criteria, team_criteria)
        
        self._cache[cache_key] = base_criteria
        return base_criteria
    
    def get_email_templates(self, team_id: Optional[str] = None, language: str = "english") -> Dict[str, Any]:
        """
        Get email templates with team and language customization.
        
        Args:
            team_id: Optional team ID for team-specific templates
            language: Language for templates
            
        Returns:
            Dictionary of email templates
        """
        cache_key = f"templates_{team_id}_{language}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Load base templates
        base_templates = self._load_json_config("email_templates.json", {})
        
        # Apply team customizations if available
        if team_id:
            team_templates = self._load_team_templates(team_id, language)
            base_templates = self._merge_configs(base_templates, team_templates)
        
        # Apply language customizations
        if language != "english":
            lang_templates = self._load_language_templates(language)
            base_templates = self._merge_configs(base_templates, lang_templates)
        
        self._cache[cache_key] = base_templates
        return base_templates
    
    def get_business_rules(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get business rules and pipeline behavior settings.
        
        Args:
            team_id: Optional team ID for team-specific rules
            
        Returns:
            Dictionary of business rules
        """
        cache_key = f"rules_{team_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Default business rules based on original system
        default_rules = {
            "pipeline": {
                "stop_on_website_fail": True,
                "wait_after_draft_generation": True,
                "max_operations": 10,
                "max_simultaneous_operations": 1,
                "sequential_execution_only": True
            },
            "data_acquisition": {
                "min_execution_time_seconds": 100,
                "required_sources": ["website"],
                "optional_sources": ["business_card", "linkedin", "facebook"]
            },
            "initial_outreach": {
                "actions": ["draft_write", "draft_rewrite", "send", "close"],
                "default_action": "draft_write",
                "require_human_approval": True,
                "one_action_per_trigger": True
            },
            "follow_up": {
                "actions": ["draft_write", "draft_rewrite", "send"],
                "require_explicit_trigger": True,
                "analyze_previous_interactions": True
            }
        }
        
        # Apply team customizations if available
        if team_id:
            team_rules = self._load_team_rules(team_id)
            default_rules = self._merge_configs(default_rules, team_rules)
        
        self._cache[cache_key] = default_rules
        return default_rules
    
    def _load_json_config(self, filename: str, default: Dict[str, Any]) -> Dict[str, Any]:
        """Load JSON configuration file with fallback to default."""
        try:
            config_file = self.config_dir / filename
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load {filename}: {str(e)}")
        
        return default.copy()
    
    def _load_team_prompts(self, team_id: str, language: str) -> Dict[str, Any]:
        """Load team-specific prompts."""
        team_file = self.config_dir / f"team_{team_id}_prompts_{language}.json"
        return self._load_json_config(team_file.name, {})
    
    def _load_team_scoring(self, team_id: str) -> Dict[str, Any]:
        """Load team-specific scoring criteria."""
        team_file = self.config_dir / f"team_{team_id}_scoring.json"
        return self._load_json_config(team_file.name, {})
    
    def _load_team_templates(self, team_id: str, language: str) -> Dict[str, Any]:
        """Load team-specific email templates."""
        team_file = self.config_dir / f"team_{team_id}_templates_{language}.json"
        return self._load_json_config(team_file.name, {})
    
    def _load_team_rules(self, team_id: str) -> Dict[str, Any]:
        """Load team-specific business rules."""
        team_file = self.config_dir / f"team_{team_id}_rules.json"
        return self._load_json_config(team_file.name, {})
    
    def _load_language_prompts(self, language: str) -> Dict[str, Any]:
        """Load language-specific prompts."""
        lang_file = self.config_dir / f"prompts_{language}.json"
        return self._load_json_config(lang_file.name, {})
    
    def _load_language_templates(self, language: str) -> Dict[str, Any]:
        """Load language-specific email templates."""
        lang_file = self.config_dir / f"templates_{language}.json"
        return self._load_json_config(lang_file.name, {})
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge configuration dictionaries.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_team_config(self, team_id: str, config_type: str, config_data: Dict[str, Any], language: str = "english") -> None:
        """
        Save team-specific configuration.
        
        Args:
            team_id: Team identifier
            config_type: Type of config (prompts, scoring, templates, rules)
            config_data: Configuration data to save
            language: Language for prompts/templates
        """
        try:
            if config_type in ["prompts", "templates"]:
                filename = f"team_{team_id}_{config_type}_{language}.json"
            else:
                filename = f"team_{team_id}_{config_type}.json"
            
            config_file = self.config_dir / filename
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Clear cache for this team
            self._clear_team_cache(team_id)
            
            self.logger.info(f"Saved team configuration: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save team config {config_type} for {team_id}: {str(e)}")
            raise
    
    def _clear_team_cache(self, team_id: str) -> None:
        """Clear cached configurations for a specific team."""
        keys_to_remove = [key for key in self._cache.keys() if team_id in key]
        for key in keys_to_remove:
            del self._cache[key]
    
    def clear_cache(self) -> None:
        """Clear all cached configurations."""
        self._cache.clear()
        self.logger.debug("Configuration cache cleared")