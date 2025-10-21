"""
Lead Scoring Stage - Evaluate customer-product fit using weighted scoring
Converted from fusesell_lead_scoring.yml
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_stage import BaseStage


class LeadScoringStage(BaseStage):
    """
    Lead Scoring stage for evaluating customer-product fit using weighted criteria.
    Converts YAML workflow logic to Python implementation.
    """
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute lead scoring stage.
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result
        """
        try:
            # Get data from previous stage (data preparation)
            prep_data = self._get_preparation_data(context)
            
            # Get scoring criteria
            scoring_criteria = self._get_scoring_criteria()
            
            # Get products to evaluate
            products = self._get_products_for_evaluation()
            
            # Score each product against the customer
            lead_scores = []
            for product in products:
                # Enhanced product evaluation with multiple analysis methods
                score_result = self._comprehensive_product_evaluation(prep_data, product, scoring_criteria)
                if score_result:
                    lead_scores.append(score_result)
            
            # Analyze and rank results
            scoring_analysis = self._analyze_scoring_results(lead_scores)
            
            # Add product comparison analysis
            product_comparison = self._compare_products(lead_scores)
            scoring_analysis['product_comparison'] = product_comparison
            
            # Save results to database
            self._save_scoring_results(context, lead_scores)
            
            # Prepare final output
            scoring_data = {
                'lead_scoring': lead_scores,
                'analysis': scoring_analysis,
                'total_products_evaluated': len(products),
                'customer_id': context.get('execution_id'),
                'scoring_timestamp': datetime.now().isoformat()
            }
            
            # Save to database
            self.save_stage_result(context, scoring_data)
            
            result = self.create_success_result(scoring_data, context)
            return result
            
        except Exception as e:
            self.log_stage_error(context, e)
            return self.handle_stage_error(e, context)

    def _get_preparation_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get data from the data preparation stage.
        
        Args:
            context: Execution context
            
        Returns:
            Data preparation results
        """
        # Try to get from stage results first
        stage_results = context.get('stage_results', {})
        if 'data_preparation' in stage_results:
            return stage_results['data_preparation'].get('data', {})
        
        # Fallback: create mock data for testing
        return self._get_mock_preparation_data(context)

    def _get_mock_preparation_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get mock preparation data for testing.
        
        Args:
            context: Execution context
            
        Returns:
            Mock preparation data
        """
        input_data = context.get('input_data', {})
        return {
            'companyInfo': {
                'name': input_data.get('customer_name', 'Test Company'),
                'industry': 'Technology',
                'size': 'Medium (50-200 employees)',
                'annualRevenue': '$2-5M',
                'address': input_data.get('customer_address', ''),
                'website': input_data.get('customer_website', '')
            },
            'painPoints': [
                {
                    'category': 'Operational Efficiency',
                    'description': 'Manual processes causing delays',
                    'impact': 'High'
                }
            ],
            'primaryContact': {
                'name': input_data.get('contact_name', ''),
                'email': input_data.get('contact_email', ''),
                'phone': input_data.get('contact_phone', '')
            }
        }

    def _get_scoring_criteria(self) -> List[Dict[str, Any]]:
        """
        Get scoring criteria configuration.
        
        Returns:
            List of scoring criteria
        """
        try:
            # Get org ID from config
            org_id = self.config.get('org_id')
            
            if org_id:
                # Try to get criteria from gs_company_criteria table (matching original YAML logic)
                criteria = self.data_manager.get_gs_company_criteria(org_id)
                if criteria:
                    self.logger.info(f"Loaded {len(criteria)} scoring criteria from gs_company_criteria table for org: {org_id}")
                    return criteria
                else:
                    self.logger.warning(f"No scoring criteria found in gs_company_criteria for organization: {org_id}")
                
                # Fallback: try local scoring criteria
                local_criteria = self.data_manager.get_scoring_criteria(org_id)
                if local_criteria:
                    self.logger.info(f"Loaded {len(local_criteria)} scoring criteria from local config for org: {org_id}")
                    return local_criteria
            
            # Final fallback: use default criteria
            self.logger.info("Using default scoring criteria")
            return self._get_default_scoring_criteria()
            
        except Exception as e:
            self.logger.warning(f"Failed to load scoring criteria: {str(e)}")
            return self._get_default_scoring_criteria()

    def _get_default_scoring_criteria(self) -> List[Dict[str, Any]]:
        """
        Get default scoring criteria based on original YAML logic.
        
        Returns:
            Default scoring criteria
        """
        return [
            {
                'name': 'industry_fit',
                'weight': 25,
                'definition': 'How well the customer\'s industry aligns with the product\'s target market',
                'guidelines': 'Score based on industry match and market penetration',
                'scoring_factors': [
                    'Direct industry match: 80-100',
                    'Related industry: 60-79',
                    'Adjacent market: 40-59',
                    'Different industry: 0-39'
                ]
            },
            {
                'name': 'company_size',
                'weight': 20,
                'definition': 'How well the customer\'s company size fits the product\'s target segment',
                'guidelines': 'Score based on employee count and revenue alignment',
                'scoring_factors': [
                    'Perfect size match: 80-100',
                    'Good size match: 60-79',
                    'Acceptable size: 40-59',
                    'Size mismatch: 0-39'
                ]
            },
            {
                'name': 'pain_points',
                'weight': 30,
                'definition': 'How well the product addresses the customer\'s identified pain points',
                'guidelines': 'Score based on pain point alignment and solution fit',
                'scoring_factors': [
                    'Direct pain point solution: 80-100',
                    'Partial pain point solution: 60-79',
                    'Indirect solution: 40-59',
                    'No pain point match: 0-39'
                ]
            },
            {
                'name': 'product_fit',
                'weight': 15,
                'definition': 'Overall product-customer compatibility',
                'guidelines': 'Score based on feature alignment and use case match',
                'scoring_factors': [
                    'Excellent feature match: 80-100',
                    'Good feature match: 60-79',
                    'Basic feature match: 40-59',
                    'Poor feature match: 0-39'
                ]
            },
            {
                'name': 'geographic_market_fit',
                'weight': 10,
                'definition': 'Geographic alignment between customer location and product availability',
                'guidelines': 'Score based on market presence and localization',
                'scoring_factors': [
                    'Strong market presence: 80-100',
                    'Moderate presence: 60-79',
                    'Limited presence: 40-59',
                    'No market presence: 0-39'
                ]
            }
        ]

    def _get_products_for_evaluation(self) -> List[Dict[str, Any]]:
        """
        Get products to evaluate against the customer.
        
        Returns:
            List of products for evaluation
        """
        try:
            # Get team ID from config
            team_id = self.config.get('team_id')
            org_id = self.config.get('org_id')
            
            if team_id:
                # Try to get products from team settings (matching original YAML logic)
                products = self.data_manager.get_products_by_team(team_id)
                if products:
                    self.logger.info(f"Loaded {len(products)} products from team settings for team: {team_id}")
                    return products
                else:
                    self.logger.warning(f"No products found for team: {team_id}")
            
            if org_id:
                # Fallback: get all products for the organization
                products = self.data_manager.get_products_by_org(org_id)
                if products:
                    self.logger.info(f"Loaded {len(products)} products from organization: {org_id}")
                    return products
                else:
                    self.logger.warning(f"No products found for organization: {org_id}")
            
            # Final fallback: use mock products
            self.logger.warning("No team or org products found, using mock products")
            return self._get_mock_products()
            
        except Exception as e:
            self.logger.warning(f"Failed to load products: {str(e)}")
            return self._get_mock_products()

    def _load_products_from_config(self) -> Optional[List[Dict[str, Any]]]:
        """
        Load products from configuration files.
        
        Returns:
            List of products or None if not available
        """
        try:
            # This would load from local configuration files
            # For now, return None to use mock data
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load products from config: {str(e)}")
            return None

    def _get_mock_products(self) -> List[Dict[str, Any]]:
        """
        Get mock products for testing and dry run.
        
        Returns:
            List of mock products
        """
        return [
            {
                'id': 'prod-12345678-1234-1234-1234-123456789012',
                'productName': 'FuseSell AI Pro',
                'shortDescription': 'AI-powered sales automation platform',
                'longDescription': 'Comprehensive sales automation solution with AI-driven lead scoring, email generation, and customer analysis',
                'painPointsSolved': [
                    'Manual lead qualification processes',
                    'Inconsistent email outreach',
                    'Poor lead prioritization',
                    'Time-consuming customer research'
                ],
                'targetUsers': [
                    'Sales teams',
                    'Marketing professionals',
                    'Business development managers'
                ],
                'keyFeatures': [
                    'AI lead scoring',
                    'Automated email generation',
                    'Customer data analysis',
                    'Pipeline management'
                ],
                'competitiveAdvantages': [
                    'Advanced AI algorithms',
                    'Local data processing',
                    'Customizable workflows',
                    'Integration capabilities'
                ],
                'localization': [
                    'North America',
                    'Europe',
                    'Asia-Pacific'
                ],
                'marketInsights': {
                    'targetIndustries': ['Technology', 'SaaS', 'Professional Services'],
                    'idealCompanySize': '50-500 employees',
                    'averageDealSize': '$10,000-$50,000'
                }
            },
            {
                'id': 'prod-87654321-4321-4321-4321-210987654321',
                'productName': 'FuseSell Starter',
                'shortDescription': 'Entry-level sales automation tool',
                'longDescription': 'Basic sales automation features for small teams getting started with sales technology',
                'painPointsSolved': [
                    'Manual contact management',
                    'Basic email automation needs',
                    'Simple lead tracking'
                ],
                'targetUsers': [
                    'Small sales teams',
                    'Startups',
                    'Solo entrepreneurs'
                ],
                'keyFeatures': [
                    'Contact management',
                    'Email templates',
                    'Basic reporting',
                    'Lead tracking'
                ],
                'competitiveAdvantages': [
                    'Easy to use',
                    'Affordable pricing',
                    'Quick setup',
                    'Essential features'
                ],
                'localization': [
                    'Global'
                ],
                'marketInsights': {
                    'targetIndustries': ['All industries'],
                    'idealCompanySize': '1-50 employees',
                    'averageDealSize': '$1,000-$5,000'
                }
            }
        ]

    def _comprehensive_product_evaluation(self, customer_data: Dict[str, Any], product: Dict[str, Any], criteria: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Comprehensive product evaluation with multiple analysis methods.
        
        Args:
            customer_data: Customer information from data preparation
            product: Product information
            criteria: Scoring criteria
            
        Returns:
            Enhanced scoring result with additional analysis
        """
        try:
            # Primary LLM-based scoring
            primary_score = self._score_customer_product_fit(customer_data, product, criteria)
            if not primary_score:
                return None
            
            # Add product-specific analysis
            product_analysis = self._analyze_product_specifics(customer_data, product)
            primary_score['product_analysis'] = product_analysis
            
            # Add competitive positioning
            competitive_position = self._evaluate_competitive_position(customer_data, product)
            primary_score['competitive_position'] = competitive_position
            
            # Add implementation feasibility
            implementation_analysis = self._assess_implementation_feasibility(customer_data, product)
            primary_score['implementation_feasibility'] = implementation_analysis
            
            # Add ROI estimation
            roi_analysis = self._estimate_roi_potential(customer_data, product)
            primary_score['roi_analysis'] = roi_analysis
            
            return primary_score
            
        except Exception as e:
            self.logger.error(f"Comprehensive product evaluation failed: {str(e)}")
            return self._score_customer_product_fit(customer_data, product, criteria)

    def _analyze_product_specifics(self, customer_data: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze product-specific factors for the customer.
        
        Args:
            customer_data: Customer information
            product: Product information
            
        Returns:
            Product-specific analysis
        """
        try:
            company_info = customer_data.get('companyInfo', {})
            pain_points = customer_data.get('painPoints', [])
            
            analysis = {
                'feature_alignment': self._assess_feature_alignment(pain_points, product),
                'scalability_match': self._assess_scalability_match(company_info, product),
                'integration_complexity': self._assess_integration_complexity(customer_data, product),
                'customization_needs': self._assess_customization_needs(customer_data, product)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Product specifics analysis failed: {str(e)}")
            return {
                'feature_alignment': 'Unable to assess',
                'scalability_match': 'Unable to assess',
                'integration_complexity': 'Unable to assess',
                'customization_needs': 'Unable to assess'
            }

    def _assess_feature_alignment(self, pain_points: List[Dict[str, Any]], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess how well product features align with customer pain points.
        
        Args:
            pain_points: Customer pain points
            product: Product information
            
        Returns:
            Feature alignment assessment
        """
        try:
            product_features = product.get('keyFeatures', [])
            pain_points_solved = product.get('painPointsSolved', [])
            
            # Count pain point matches
            matched_pain_points = 0
            total_pain_points = len(pain_points)
            
            for pain_point in pain_points:
                pain_category = pain_point.get('category', '').lower()
                pain_description = pain_point.get('description', '').lower()
                
                # Check if any product features address this pain point
                for solved_pain in pain_points_solved:
                    if (pain_category in solved_pain.lower() or 
                        any(word in solved_pain.lower() for word in pain_description.split()[:3])):
                        matched_pain_points += 1
                        break
            
            alignment_score = (matched_pain_points / total_pain_points * 100) if total_pain_points > 0 else 0
            
            return {
                'alignment_score': round(alignment_score, 1),
                'matched_pain_points': matched_pain_points,
                'total_pain_points': total_pain_points,
                'key_feature_matches': product_features[:3]  # Top 3 relevant features
            }
            
        except Exception as e:
            self.logger.error(f"Feature alignment assessment failed: {str(e)}")
            return {
                'alignment_score': 0,
                'matched_pain_points': 0,
                'total_pain_points': len(pain_points),
                'key_feature_matches': []
            }

    def _assess_scalability_match(self, company_info: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess how well the product scales with the company.
        
        Args:
            company_info: Company information
            product: Product information
            
        Returns:
            Scalability assessment
        """
        try:
            company_size = company_info.get('size', '').lower()
            market_insights = product.get('marketInsights', {})
            ideal_company_size = market_insights.get('idealCompanySize', '').lower()
            
            # Simple scalability assessment
            scalability_rating = 'Good'
            if 'small' in company_size and 'small' in ideal_company_size:
                scalability_rating = 'Excellent'
            elif 'large' in company_size and 'large' in ideal_company_size:
                scalability_rating = 'Excellent'
            elif ('medium' in company_size and 'medium' in ideal_company_size) or ('50' in ideal_company_size and 'medium' in company_size):
                scalability_rating = 'Excellent'
            elif 'startup' in company_size and ('small' in ideal_company_size or 'startup' in ideal_company_size):
                scalability_rating = 'Excellent'
            
            return {
                'scalability_rating': scalability_rating,
                'company_size': company_size,
                'ideal_size_match': ideal_company_size,
                'growth_potential': 'High' if scalability_rating == 'Excellent' else 'Medium'
            }
            
        except Exception as e:
            self.logger.error(f"Scalability assessment failed: {str(e)}")
            return {
                'scalability_rating': 'Unknown',
                'company_size': company_info.get('size', 'Unknown'),
                'ideal_size_match': 'Unknown',
                'growth_potential': 'Unknown'
            }

    def _assess_integration_complexity(self, customer_data: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess integration complexity for the customer.
        
        Args:
            customer_data: Customer information
            product: Product information
            
        Returns:
            Integration complexity assessment
        """
        try:
            current_tech_stack = customer_data.get('currentTechStack', [])
            installation_requirements = product.get('installationRequirements', '')
            
            # Simple complexity assessment based on tech stack
            complexity_level = 'Medium'
            if len(current_tech_stack) == 0:
                complexity_level = 'High'  # No existing tech stack
            elif len(current_tech_stack) > 5:
                complexity_level = 'Low'   # Sophisticated tech stack
            
            return {
                'complexity_level': complexity_level,
                'current_tech_stack_size': len(current_tech_stack),
                'integration_time_estimate': self._estimate_integration_time(complexity_level),
                'technical_requirements': installation_requirements[:200] if installation_requirements else 'Standard requirements'
            }
            
        except Exception as e:
            self.logger.error(f"Integration complexity assessment failed: {str(e)}")
            return {
                'complexity_level': 'Unknown',
                'current_tech_stack_size': 0,
                'integration_time_estimate': 'Unknown',
                'technical_requirements': 'Unknown'
            }

    def _estimate_integration_time(self, complexity_level: str) -> str:
        """
        Estimate integration time based on complexity.
        
        Args:
            complexity_level: Complexity level (Low/Medium/High)
            
        Returns:
            Time estimate string
        """
        time_estimates = {
            'Low': '2-4 weeks',
            'Medium': '4-8 weeks',
            'High': '8-12 weeks',
            'Unknown': '4-8 weeks'
        }
        return time_estimates.get(complexity_level, '4-8 weeks')

    def _assess_customization_needs(self, customer_data: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess customization needs for the customer.
        
        Args:
            customer_data: Customer information
            product: Product information
            
        Returns:
            Customization needs assessment
        """
        try:
            company_info = customer_data.get('companyInfo', {})
            industry = company_info.get('industry', '').lower()
            
            # Assess customization needs based on industry and company specifics
            customization_level = 'Standard'
            if 'healthcare' in industry or 'finance' in industry or 'legal' in industry:
                customization_level = 'High'  # Regulated industries
            elif 'manufacturing' in industry or 'retail' in industry:
                customization_level = 'Medium'  # Industry-specific needs
            
            return {
                'customization_level': customization_level,
                'industry_specific_needs': industry,
                'estimated_customization_effort': self._estimate_customization_effort(customization_level),
                'standard_features_coverage': '70-90%' if customization_level == 'Standard' else '50-70%'
            }
            
        except Exception as e:
            self.logger.error(f"Customization needs assessment failed: {str(e)}")
            return {
                'customization_level': 'Unknown',
                'industry_specific_needs': 'Unknown',
                'estimated_customization_effort': 'Unknown',
                'standard_features_coverage': 'Unknown'
            }

    def _estimate_customization_effort(self, customization_level: str) -> str:
        """
        Estimate customization effort based on level.
        
        Args:
            customization_level: Customization level
            
        Returns:
            Effort estimate string
        """
        effort_estimates = {
            'Standard': 'Minimal (configuration only)',
            'Medium': 'Moderate (some custom development)',
            'High': 'Significant (extensive customization)',
            'Unknown': 'To be determined'
        }
        return effort_estimates.get(customization_level, 'To be determined')

    def _evaluate_competitive_position(self, customer_data: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate competitive positioning for this customer.
        
        Args:
            customer_data: Customer information
            product: Product information
            
        Returns:
            Competitive position analysis
        """
        try:
            competitive_advantages = product.get('competitiveAdvantages', [])
            
            return {
                'key_differentiators': competitive_advantages[:3],
                'competitive_strength': 'Strong' if len(competitive_advantages) > 3 else 'Moderate',
                'market_position': self._assess_market_position(product),
                'customer_value_props': self._identify_customer_value_props(customer_data, competitive_advantages)
            }
            
        except Exception as e:
            self.logger.error(f"Competitive position evaluation failed: {str(e)}")
            return {
                'key_differentiators': [],
                'competitive_strength': 'Unknown',
                'market_position': 'Unknown',
                'customer_value_props': []
            }

    def _assess_market_position(self, product: Dict[str, Any]) -> str:
        """
        Assess market position of the product.
        
        Args:
            product: Product information
            
        Returns:
            Market position assessment
        """
        market_insights = product.get('marketInsights', {})
        if market_insights:
            return 'Established'
        else:
            return 'Emerging'

    def _identify_customer_value_props(self, customer_data: Dict[str, Any], competitive_advantages: List[str]) -> List[str]:
        """
        Identify customer-specific value propositions.
        
        Args:
            customer_data: Customer information
            competitive_advantages: Product competitive advantages
            
        Returns:
            Customer-specific value propositions
        """
        try:
            pain_points = customer_data.get('painPoints', [])
            value_props = []
            
            for advantage in competitive_advantages[:3]:
                # Match advantages to pain points
                for pain_point in pain_points:
                    if any(word in advantage.lower() for word in pain_point.get('description', '').lower().split()[:3]):
                        value_props.append(f"{advantage} - addresses {pain_point.get('category', 'business')} challenges")
                        break
                else:
                    value_props.append(advantage)
            
            return value_props[:3]
            
        except Exception as e:
            self.logger.error(f"Value proposition identification failed: {str(e)}")
            return competitive_advantages[:3]

    def _assess_implementation_feasibility(self, customer_data: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess implementation feasibility for the customer.
        
        Args:
            customer_data: Customer information
            product: Product information
            
        Returns:
            Implementation feasibility assessment
        """
        try:
            company_info = customer_data.get('companyInfo', {})
            financial_info = customer_data.get('financialInfo', {})
            
            # Assess budget alignment
            market_insights = product.get('marketInsights', {})
            average_deal_size = market_insights.get('averageDealSize', '')
            
            budget_alignment = self._assess_budget_alignment(financial_info, average_deal_size)
            
            return {
                'feasibility_rating': self._calculate_feasibility_rating(budget_alignment, company_info),
                'budget_alignment': budget_alignment,
                'implementation_timeline': self._estimate_implementation_timeline(company_info),
                'success_probability': self._estimate_success_probability(customer_data, product),
                'key_success_factors': self._identify_success_factors(customer_data, product)
            }
            
        except Exception as e:
            self.logger.error(f"Implementation feasibility assessment failed: {str(e)}")
            return {
                'feasibility_rating': 'Unknown',
                'budget_alignment': 'Unknown',
                'implementation_timeline': 'Unknown',
                'success_probability': 'Unknown',
                'key_success_factors': []
            }

    def _assess_budget_alignment(self, financial_info: Dict[str, Any], average_deal_size: str) -> str:
        """
        Assess budget alignment with product pricing.
        
        Args:
            financial_info: Customer financial information
            average_deal_size: Product average deal size
            
        Returns:
            Budget alignment assessment
        """
        try:
            annual_revenue = financial_info.get('estimatedAnnualRevenue', '')
            
            if not annual_revenue or not average_deal_size:
                return 'Unknown'
            
            # Simple budget assessment logic
            if '$10,000' in average_deal_size and ('$2-5M' in annual_revenue or '$5-10M' in annual_revenue):
                return 'Good'
            elif '$1,000' in average_deal_size:
                return 'Excellent'
            else:
                return 'Moderate'
                
        except Exception as e:
            self.logger.error(f"Budget alignment assessment failed: {str(e)}")
            return 'Unknown'

    def _calculate_feasibility_rating(self, budget_alignment: str, company_info: Dict[str, Any]) -> str:
        """
        Calculate overall feasibility rating.
        
        Args:
            budget_alignment: Budget alignment assessment
            company_info: Company information
            
        Returns:
            Feasibility rating
        """
        if budget_alignment == 'Excellent':
            return 'High'
        elif budget_alignment == 'Good':
            return 'Medium-High'
        elif budget_alignment == 'Moderate':
            return 'Medium'
        else:
            return 'Low-Medium'

    def _estimate_implementation_timeline(self, company_info: Dict[str, Any]) -> str:
        """
        Estimate implementation timeline based on company size.
        
        Args:
            company_info: Company information
            
        Returns:
            Timeline estimate
        """
        company_size = company_info.get('size', '').lower()
        
        if 'small' in company_size or 'startup' in company_size:
            return '1-3 months'
        elif 'large' in company_size:
            return '6-12 months'
        else:
            return '3-6 months'

    def _estimate_success_probability(self, customer_data: Dict[str, Any], product: Dict[str, Any]) -> str:
        """
        Estimate probability of successful implementation.
        
        Args:
            customer_data: Customer information
            product: Product information
            
        Returns:
            Success probability estimate
        """
        # Simple success probability based on pain point alignment
        pain_points = customer_data.get('painPoints', [])
        pain_points_solved = product.get('painPointsSolved', [])
        
        if len(pain_points_solved) >= len(pain_points):
            return 'High (80-90%)'
        elif len(pain_points_solved) >= len(pain_points) * 0.5:
            return 'Medium-High (70-80%)'
        else:
            return 'Medium (60-70%)'

    def _identify_success_factors(self, customer_data: Dict[str, Any], product: Dict[str, Any]) -> List[str]:
        """
        Identify key success factors for implementation.
        
        Args:
            customer_data: Customer information
            product: Product information
            
        Returns:
            List of success factors
        """
        return [
            'Strong executive sponsorship',
            'Dedicated implementation team',
            'Clear success metrics definition',
            'Adequate training and change management',
            'Phased rollout approach'
        ]

    def _estimate_roi_potential(self, customer_data: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate ROI potential for the customer.
        
        Args:
            customer_data: Customer information
            product: Product information
            
        Returns:
            ROI analysis
        """
        try:
            pain_points = customer_data.get('painPoints', [])
            company_info = customer_data.get('companyInfo', {})
            
            # Estimate ROI based on pain points addressed
            roi_factors = []
            estimated_savings = 0
            
            for pain_point in pain_points:
                category = pain_point.get('category', '').lower()
                impact = pain_point.get('impact', '').lower()
                
                if 'operational' in category or 'efficiency' in category:
                    if 'high' in impact:
                        estimated_savings += 15  # 15% efficiency gain
                        roi_factors.append('Operational efficiency improvements')
                    else:
                        estimated_savings += 8
                        roi_factors.append('Process optimization')
                
                elif 'technology' in category:
                    if 'high' in impact:
                        estimated_savings += 12
                        roi_factors.append('Technology modernization benefits')
                    else:
                        estimated_savings += 6
                        roi_factors.append('System integration improvements')
            
            # Calculate payback period estimate
            payback_period = self._estimate_payback_period(estimated_savings)
            
            return {
                'estimated_roi_percentage': f"{estimated_savings}%",
                'payback_period': payback_period,
                'roi_factors': roi_factors[:3],
                'confidence_level': 'Medium' if estimated_savings > 10 else 'Low',
                'annual_benefit_estimate': self._estimate_annual_benefits(company_info, estimated_savings)
            }
            
        except Exception as e:
            self.logger.error(f"ROI estimation failed: {str(e)}")
            return {
                'estimated_roi_percentage': 'Unknown',
                'payback_period': 'Unknown',
                'roi_factors': [],
                'confidence_level': 'Unknown',
                'annual_benefit_estimate': 'Unknown'
            }

    def _estimate_payback_period(self, roi_percentage: float) -> str:
        """
        Estimate payback period based on ROI percentage.
        
        Args:
            roi_percentage: Estimated ROI percentage
            
        Returns:
            Payback period estimate
        """
        if roi_percentage >= 20:
            return '6-12 months'
        elif roi_percentage >= 10:
            return '12-18 months'
        elif roi_percentage >= 5:
            return '18-24 months'
        else:
            return '24+ months'

    def _estimate_annual_benefits(self, company_info: Dict[str, Any], roi_percentage: float) -> str:
        """
        Estimate annual benefits based on company size and ROI.
        
        Args:
            company_info: Company information
            roi_percentage: Estimated ROI percentage
            
        Returns:
            Annual benefits estimate
        """
        try:
            annual_revenue = company_info.get('annualRevenue', '').lower()
            
            if '$10m' in annual_revenue or '$5-10m' in annual_revenue:
                base_benefit = 500000  # $500K base for $5-10M revenue
            elif '$2-5m' in annual_revenue:
                base_benefit = 200000  # $200K base for $2-5M revenue
            elif '$1-2m' in annual_revenue:
                base_benefit = 100000  # $100K base for $1-2M revenue
            else:
                base_benefit = 50000   # $50K base for smaller companies
            
            estimated_benefit = base_benefit * (roi_percentage / 100)
            
            if estimated_benefit >= 100000:
                return f"${estimated_benefit/1000:.0f}K+"
            else:
                return f"${estimated_benefit:.0f}+"
                
        except Exception as e:
            self.logger.error(f"Annual benefits estimation failed: {str(e)}")
            return "To be determined"

    def _compare_products(self, lead_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare products and provide recommendations.
        
        Args:
            lead_scores: List of scoring results
            
        Returns:
            Product comparison analysis
        """
        try:
            if len(lead_scores) <= 1:
                return {
                    'comparison_available': False,
                    'reason': 'Only one product evaluated'
                }
            
            # Sort by total weighted score
            sorted_scores = sorted(lead_scores, key=lambda x: x['total_weighted_score'], reverse=True)
            
            top_product = sorted_scores[0]
            second_product = sorted_scores[1] if len(sorted_scores) > 1 else None
            
            comparison = {
                'comparison_available': True,
                'top_recommendation': {
                    'product_name': top_product['product_name'],
                    'score': top_product['total_weighted_score'],
                    'key_strengths': self._extract_top_criteria(top_product['scores'])
                },
                'alternative_option': None,
                'score_gap': 0,
                'recommendation_confidence': 'High'
            }
            
            if second_product:
                score_gap = top_product['total_weighted_score'] - second_product['total_weighted_score']
                comparison['alternative_option'] = {
                    'product_name': second_product['product_name'],
                    'score': second_product['total_weighted_score'],
                    'key_strengths': self._extract_top_criteria(second_product['scores'])
                }
                comparison['score_gap'] = score_gap
                
                if score_gap < 10:
                    comparison['recommendation_confidence'] = 'Medium'
                    comparison['recommendation_note'] = 'Close scores - consider other factors'
                elif score_gap > 30:
                    comparison['recommendation_confidence'] = 'Very High'
                    comparison['recommendation_note'] = 'Clear winner identified'
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Product comparison failed: {str(e)}")
            return {
                'comparison_available': False,
                'reason': 'Comparison analysis failed'
            }

    def _extract_top_criteria(self, scores: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Extract top scoring criteria for a product.
        
        Args:
            scores: Criteria scores dictionary
            
        Returns:
            List of top criteria names
        """
        try:
            # Sort criteria by score
            sorted_criteria = sorted(scores.items(), key=lambda x: x[1].get('score', 0), reverse=True)
            
            # Return top 2 criteria names
            return [criterion[0].replace('_', ' ').title() for criterion in sorted_criteria[:2]]
            
        except Exception as e:
            self.logger.error(f"Top criteria extraction failed: {str(e)}")
            return []

    def _score_customer_product_fit(self, customer_data: Dict[str, Any], product: Dict[str, Any], criteria: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Score customer-product fit using LLM analysis.
        
        Args:
            customer_data: Customer information from data preparation
            product: Product information
            criteria: Scoring criteria
            
        Returns:
            Scoring result or None if failed
        """
        try:
            if self.is_dry_run():
                return self._get_mock_scoring_result(product)
            
            # Create the LLM prompt based on original YAML instruction
            prompt = self._create_scoring_prompt(customer_data, product, criteria)
            
            # Call LLM with specific parameters from original YAML
            response = self.call_llm(prompt, temperature=0.3)
            
            # Parse the JSON response
            scoring_result = self.parse_json_response(response)
            
            # Validate and clean the scoring result
            validated_result = self._validate_scoring_result(scoring_result, product)
            
            self.logger.info(f"Successfully scored product {product.get('productName', 'Unknown')}")
            return validated_result
            
        except Exception as e:
            self.logger.error(f"Product scoring failed for {product.get('productName', 'Unknown')}: {str(e)}")
            return self._get_fallback_scoring_result(product)

    def _create_scoring_prompt(self, customer_data: Dict[str, Any], product: Dict[str, Any], criteria: List[Dict[str, Any]]) -> str:
        """
        Create the LLM scoring prompt based on original YAML instruction.
        
        Args:
            customer_data: Customer information
            product: Product information
            criteria: Scoring criteria
            
        Returns:
            Formatted prompt string
        """
        # Extract customer address for geographic scoring
        company_info = customer_data.get('companyInfo', {})
        customer_address = company_info.get('address', '')
        
        prompt = f"""Role: You are a lead scoring expert. 

Objective: Your task is to evaluate the potential fit between a customer and a specific product based on the provided criteria. Use the following data to perform lead scoring.  

## Instructions  
1. **Evaluate Criteria**:  
  - Assess the customer against the **5 criteria** provided.  
  - Assign a score (0–100) for each criterion based on the scoring guidelines in the criteria JSON.  

2. **Special Handling for Geographic Market Fit**:  
  - Use the `localization` field from the product info and the customer's address
  - If the customer address is **not provided**, assign a default score of 50.  

3. **Output Structure**: Return the analysis as a JSON object with the following format:  
  {{  
    "product_name": "productName",  
    "product_id": "Get ID from 'id' of product info, ensure exactly 36 characters",  
    "scores": {{  
      "industry_fit": {{ "score": 0–100, "justification": "Brief explanation" }},  
      "company_size": {{ "score": 0–100, "justification": "Brief explanation" }},  
      "pain_points": {{ "score": 0–100, "justification": "Brief explanation" }},  
      "product_fit": {{ "score": 0–100, "justification": "Brief explanation" }},  
      "geographic_market_fit": {{ "score": 0–100, "justification": "Brief explanation" }}  
    }},  
    "total_weighted_score": 0–100  
  }}  
4. Scoring Rules:
  - If information is not provided, assign a score of 0 for that criterion.
  - Ensure the product_id is exactly 36 characters long and matches the id field in the product info.
  - Do not include any explanations or comments outside of the JSON structure.
  - Do not use keyword ```json in response

The Input Data: 
Product Information: {json.dumps(product, indent=2)}
Scoring Criteria: {json.dumps(criteria, indent=2)}
Customer Information: {json.dumps(customer_data, indent=2)}
Customer address: {customer_address}"""

        return prompt

    def _get_mock_scoring_result(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get mock scoring result for dry run mode.
        
        Args:
            product: Product information
            
        Returns:
            Mock scoring result
        """
        product_name = product.get('productName', 'Unknown Product')
        product_id = product.get('id', 'mock-product-id-1234-5678-9012-345678901234')
        
        # Ensure product_id is exactly 36 characters
        if len(product_id) != 36:
            product_id = f"mock-{product_id[:31]}" if len(product_id) > 31 else f"mock-{product_id}-{'0' * (31 - len(product_id))}"
        
        return {
            'product_name': product_name,
            'product_id': product_id,
            'scores': {
                'industry_fit': {
                    'score': 75,
                    'justification': 'Good industry alignment with technology sector'
                },
                'company_size': {
                    'score': 80,
                    'justification': 'Company size fits well within target segment'
                },
                'pain_points': {
                    'score': 85,
                    'justification': 'Product directly addresses identified operational efficiency challenges'
                },
                'product_fit': {
                    'score': 70,
                    'justification': 'Strong feature alignment with customer needs'
                },
                'geographic_market_fit': {
                    'score': 90,
                    'justification': 'Strong market presence in customer location'
                }
            },
            'total_weighted_score': 78
        }

    def _validate_scoring_result(self, scoring_result: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean the scoring result.
        
        Args:
            scoring_result: Raw scoring result from LLM
            product: Product information
            
        Returns:
            Validated scoring result
        """
        try:
            # Ensure required fields exist
            if 'product_name' not in scoring_result:
                scoring_result['product_name'] = product.get('productName', 'Unknown')
            
            if 'product_id' not in scoring_result:
                scoring_result['product_id'] = product.get('id', 'unknown-product-id')
            
            # Ensure product_id is exactly 36 characters
            product_id = scoring_result['product_id']
            if len(product_id) != 36:
                # Try to use the original product ID
                original_id = product.get('id', '')
                if len(original_id) == 36:
                    scoring_result['product_id'] = original_id
                else:
                    # Generate a valid 36-character ID
                    scoring_result['product_id'] = f"prod-{product_id[:31]}" if len(product_id) > 31 else f"prod-{product_id}-{'0' * (31 - len(product_id))}"
            
            # Validate scores
            scores = scoring_result.get('scores', {})
            required_criteria = ['industry_fit', 'company_size', 'pain_points', 'product_fit', 'geographic_market_fit']
            
            for criterion in required_criteria:
                if criterion not in scores:
                    scores[criterion] = {'score': 0, 'justification': 'No data available'}
                elif not isinstance(scores[criterion], dict):
                    scores[criterion] = {'score': 0, 'justification': 'Invalid data format'}
                else:
                    # Ensure score is within valid range
                    score_value = scores[criterion].get('score', 0)
                    if not isinstance(score_value, (int, float)) or score_value < 0 or score_value > 100:
                        scores[criterion]['score'] = 0
                    
                    # Ensure justification exists
                    if 'justification' not in scores[criterion]:
                        scores[criterion]['justification'] = 'No justification provided'
            
            # Calculate total weighted score if not provided or invalid
            if 'total_weighted_score' not in scoring_result or not isinstance(scoring_result['total_weighted_score'], (int, float)):
                scoring_result['total_weighted_score'] = self._calculate_weighted_score(scores)
            
            return scoring_result
            
        except Exception as e:
            self.logger.error(f"Scoring result validation failed: {str(e)}")
            return self._get_fallback_scoring_result(product)

    def _calculate_weighted_score(self, scores: Dict[str, Dict[str, Any]]) -> float:
        """
        Calculate weighted total score based on criteria weights.
        
        Args:
            scores: Individual criterion scores
            
        Returns:
            Weighted total score
        """
        try:
            criteria = self._get_default_scoring_criteria()
            total_weighted = 0
            total_weight = 0
            
            for criterion in criteria:
                criterion_name = criterion['name']
                weight = criterion['weight']
                
                if criterion_name in scores:
                    score = scores[criterion_name].get('score', 0)
                    total_weighted += score * (weight / 100)
                    total_weight += weight
            
            if total_weight > 0:
                return round(total_weighted, 1)
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Weighted score calculation failed: {str(e)}")
            return 0.0

    def _get_fallback_scoring_result(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get fallback scoring result when LLM scoring fails.
        
        Args:
            product: Product information
            
        Returns:
            Fallback scoring result
        """
        product_name = product.get('productName', 'Unknown Product')
        product_id = product.get('id', 'fallback-product-id-1234-5678-9012-345678901234')
        
        return {
            'product_name': product_name,
            'product_id': product_id,
            'scores': {
                'industry_fit': {'score': 0, 'justification': 'Unable to evaluate due to processing error'},
                'company_size': {'score': 0, 'justification': 'Unable to evaluate due to processing error'},
                'pain_points': {'score': 0, 'justification': 'Unable to evaluate due to processing error'},
                'product_fit': {'score': 0, 'justification': 'Unable to evaluate due to processing error'},
                'geographic_market_fit': {'score': 50, 'justification': 'Default score assigned due to processing error'}
            },
            'total_weighted_score': 10
        }

    def _analyze_scoring_results(self, lead_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze scoring results and provide insights.
        
        Args:
            lead_scores: List of scoring results
            
        Returns:
            Analysis insights
        """
        try:
            if not lead_scores:
                return {
                    'highest_score': 0,
                    'lowest_score': 0,
                    'average_score': 0,
                    'recommended_product': None,
                    'insights': ['No products were evaluated']
                }
            
            scores = [score['total_weighted_score'] for score in lead_scores]
            highest_score = max(scores)
            lowest_score = min(scores)
            average_score = sum(scores) / len(scores)
            
            # Find recommended product (highest scoring)
            recommended_product = None
            for score in lead_scores:
                if score['total_weighted_score'] == highest_score:
                    recommended_product = {
                        'product_name': score['product_name'],
                        'product_id': score['product_id'],
                        'score': score['total_weighted_score']
                    }
                    break
            
            # Generate insights
            insights = []
            if highest_score >= 80:
                insights.append('Excellent product-customer fit identified')
            elif highest_score >= 60:
                insights.append('Good product-customer fit with some optimization opportunities')
            elif highest_score >= 40:
                insights.append('Moderate fit - consider addressing key gaps before outreach')
            else:
                insights.append('Low fit scores - may need different products or customer qualification')
            
            if len(lead_scores) > 1:
                score_range = highest_score - lowest_score
                if score_range > 30:
                    insights.append('Significant variation in product fit - focus on highest scoring options')
                else:
                    insights.append('Similar fit scores across products - consider other factors for selection')
            
            return {
                'highest_score': highest_score,
                'lowest_score': lowest_score,
                'average_score': round(average_score, 1),
                'recommended_product': recommended_product,
                'insights': insights,
                'total_products_evaluated': len(lead_scores)
            }
            
        except Exception as e:
            self.logger.error(f"Scoring analysis failed: {str(e)}")
            return {
                'highest_score': 0,
                'lowest_score': 0,
                'average_score': 0,
                'recommended_product': None,
                'insights': ['Analysis failed due to processing error'],
                'total_products_evaluated': len(lead_scores) if lead_scores else 0
            }

    def _save_scoring_results(self, context: Dict[str, Any], lead_scores: List[Dict[str, Any]]) -> None:
        """
        Save scoring results to local database.
        
        Args:
            context: Execution context
            lead_scores: List of scoring results
        """
        try:
            execution_id = context.get('execution_id')
            
            for score_result in lead_scores:
                # Save to lead_scores table
                score_data = {
                    'execution_id': execution_id,
                    'customer_id': execution_id,  # Using execution_id as customer_id
                    'product_id': score_result.get('product_id'),
                    'score': score_result.get('total_weighted_score', 0),
                    'criteria_breakdown': json.dumps(score_result.get('scores', {}))
                }
                
                # Save to database using data manager
                self.data_manager.save_lead_score(
                    execution_id=score_data['execution_id'],
                    customer_id=score_data['customer_id'],
                    product_id=score_data['product_id'],
                    score=score_data['score'],
                    criteria_breakdown=json.loads(score_data['criteria_breakdown'])
                )
                self.logger.info(f"Scoring data saved to database: {score_result.get('product_name')}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save scoring results: {str(e)}")

    def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        Validate input data for lead scoring stage.

        Args:
            context: Execution context

        Returns:
            True if input is valid
        """
        # Check if we have data from data preparation stage
        stage_results = context.get('stage_results', {})
        if 'data_preparation' in stage_results:
            return True
        
        # Fallback: check if we have basic input data
        input_data = context.get('input_data', {})
        return bool(input_data.get('customer_name') or input_data.get('customer_website'))

    def get_required_fields(self) -> List[str]:
        """
        Get list of required input fields for this stage.
        
        Returns:
            List of required field names
        """
        return []  # This stage depends on data_preparation stage output