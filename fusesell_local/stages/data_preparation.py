"""
Data Preparation Stage - Clean and structure customer data using AI
Converted from fusesell_data_preparation.yml
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_stage import BaseStage


class DataPreparationStage(BaseStage):
    """
    Data Preparation stage for cleaning and structuring customer data using LLM.
    Converts YAML workflow logic to Python implementation.
    """

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute data preparation stage.

        Args:
            context: Execution context

        Returns:
            Stage execution result
        """
        try:
            # Get data from previous stage (data acquisition)
            acquisition_data = self._get_acquisition_data(context)
            
            # Prepare customer information for LLM processing
            customer_info_text = self._prepare_customer_info_text(acquisition_data)
            
            # Extract structured customer information using LLM
            structured_data = self._extract_structured_customer_info(customer_info_text)
            
            # Enhance pain point identification
            enhanced_data = self._enhance_pain_point_analysis(structured_data, customer_info_text)
            
            # Add financial analysis
            financial_enhanced_data = self._enhance_financial_analysis(enhanced_data, customer_info_text)
            
            # Add company research and development analysis
            research_enhanced_data = self._enhance_research_analysis(financial_enhanced_data, customer_info_text)
            
            # Validate and clean the structured data
            validated_data = self._validate_and_clean_data(research_enhanced_data)
            
            # Save customer data to local database
            self._save_customer_data(context, validated_data)
            
            # Save to database
            self.save_stage_result(context, validated_data)
            
            result = self.create_success_result(validated_data, context)
            return result

        except Exception as e:
            self.log_stage_error(context, e)
            return self.handle_stage_error(e, context)

    def _get_acquisition_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get data from the data acquisition stage.
        
        Args:
            context: Execution context
            
        Returns:
            Data acquisition results
        """
        # Try to get from stage results first
        stage_results = context.get('stage_results', {})
        if 'data_acquisition' in stage_results:
            acquisition_data = stage_results['data_acquisition'].get('data', {})
            # Store for fallback use
            self._current_acquisition_data = acquisition_data
            return acquisition_data
        
        # Fallback: try to get from input_data (for testing)
        input_data = context.get('input_data', {})
        fallback_data = {
            'company_name': input_data.get('customer_name', ''),
            'company_website': input_data.get('customer_website', ''),
            'customer_description': input_data.get('customer_description', ''),
            'company_mini_search': input_data.get('company_mini_search', ''),
            'contact_name': input_data.get('contact_name')
                or input_data.get('recipient_name')
                or input_data.get('customer_name', ''),
            'customer_email': input_data.get('contact_email')
                or input_data.get('recipient_address')
                or input_data.get('customer_email', ''),
            'customer_phone': input_data.get('contact_phone')
                or input_data.get('customer_phone', ''),
            'customer_address': input_data.get('customer_address', ''),
            'customer_linkedin': input_data.get('linkedin_url')
                or input_data.get('input_linkedin_url', ''),
            'customer_facebook': input_data.get('facebook_url')
                or input_data.get('input_facebook_url', ''),
            'company_business': '',
            'company_industries': [],
            'founders': [],
            'branches': []
        }
        # Store for fallback use
        self._current_acquisition_data = fallback_data
        return fallback_data

    def _prepare_customer_info_text(self, acquisition_data: Dict[str, Any]) -> str:
        """
        Prepare customer information text for LLM processing.
        
        Args:
            acquisition_data: Data from acquisition stage
            
        Returns:
            Combined customer information text
        """
        info_parts = []
        
        # Add company mini search results
        mini_search = acquisition_data.get('company_mini_search', '')
        if mini_search:
            info_parts.append(f"Company Research: {mini_search}")
        
        # Add customer description
        description = acquisition_data.get('customer_description', '')
        if description:
            info_parts.append(f"Customer Description: {description}")
        
        # Add basic company info
        company_name = acquisition_data.get('company_name', '')
        if company_name:
            info_parts.append(f"Company Name: {company_name}")
        
        website = acquisition_data.get('company_website', '')
        if website:
            info_parts.append(f"Website: {website}")
        
        # Add contact information
        contact_name = acquisition_data.get('contact_name', '')
        if contact_name:
            info_parts.append(f"Contact: {contact_name}")
        
        # Add business information
        business = acquisition_data.get('company_business', '')
        if business:
            info_parts.append(f"Business: {business}")
        
        # Add industries
        industries = acquisition_data.get('company_industries', [])
        if industries:
            info_parts.append(f"Industries: {', '.join(industries)}")
        
        return '; '.join(info_parts)

    def _extract_structured_customer_info(self, customer_info_text: str) -> Dict[str, Any]:
        """
        Extract structured customer information using LLM.
        
        Args:
            customer_info_text: Combined customer information text
            
        Returns:
            Structured customer information dictionary
        """
        try:
            if self.is_dry_run():
                return self._get_mock_structured_data()
            
            # Get the LLM instruction from the original YAML
            instruction = self._get_llm_instruction()
            
            # Create the full prompt
            prompt = f"{instruction}\n\nThe customer information: {customer_info_text}"
            
            # Call LLM with specific parameters from original YAML
            response = self.call_llm(prompt, temperature=0.3)
            
            # Parse the JSON response
            structured_data = self.parse_json_response(response)
            
            self.logger.info("Successfully extracted structured customer information")
            return structured_data
            
        except Exception as e:
            self.logger.error(f"Structured data extraction failed: {str(e)}")
            # Return minimal structure to prevent complete failure
            return self._get_fallback_structured_data(customer_info_text)

    def _enhance_pain_point_analysis(self, structured_data: Dict[str, Any], customer_info_text: str) -> Dict[str, Any]:
        """
        Enhance pain point identification with additional analysis.
        
        Args:
            structured_data: Initial structured data from LLM
            customer_info_text: Original customer information text
            
        Returns:
            Enhanced structured data with better pain point analysis
        """
        try:
            current_pain_points = structured_data.get('painPoints', [])
            
            # If pain points are insufficient, enhance them
            if len(current_pain_points) < 2 or not self._are_pain_points_detailed(current_pain_points):
                enhanced_pain_points = self._generate_enhanced_pain_points(structured_data, customer_info_text)
                if enhanced_pain_points:
                    structured_data['painPoints'] = enhanced_pain_points
            
            # Categorize and prioritize pain points
            structured_data['painPoints'] = self._categorize_and_prioritize_pain_points(structured_data['painPoints'])
            
            return structured_data
            
        except Exception as e:
            self.logger.error(f"Pain point enhancement failed: {str(e)}")
            return structured_data

    def _are_pain_points_detailed(self, pain_points: List[Dict[str, Any]]) -> bool:
        """
        Check if pain points are detailed enough.
        
        Args:
            pain_points: List of pain point dictionaries
            
        Returns:
            True if pain points are sufficiently detailed
        """
        if not pain_points:
            return False
        
        for pain_point in pain_points:
            description = pain_point.get('description', '')
            if len(description) < 20:  # Too short to be meaningful
                return False
        
        return True

    def _generate_enhanced_pain_points(self, structured_data: Dict[str, Any], customer_info_text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Generate enhanced pain points using focused LLM analysis.
        
        Args:
            structured_data: Current structured data
            customer_info_text: Original customer information
            
        Returns:
            Enhanced pain points list or None if failed
        """
        try:
            if self.is_dry_run():
                return self._get_mock_pain_points()
            
            company_info = structured_data.get('companyInfo', {})
            industry = company_info.get('industry', '')
            company_size = company_info.get('size', '')
            
            pain_point_prompt = f"""Analyze the following company information and identify specific, actionable pain points:

Company Information: {customer_info_text}
Industry: {industry}
Company Size: {company_size}

Based on this information, identify 3-5 specific pain points this company likely faces. For each pain point, provide:
1. Category (e.g., "Operational Efficiency", "Technology", "Financial", "Market Competition", "Customer Experience")
2. Detailed description of the specific challenge
3. Impact level and explanation (High/Medium/Low with reasoning)

Return as JSON array:
[
  {{
    "category": "category name",
    "description": "detailed description of the pain point",
    "impact": "impact level with explanation"
  }}
]

Focus on realistic, industry-specific challenges that would resonate with the company."""

            response = self.call_llm(pain_point_prompt, temperature=0.4)
            pain_points = self.parse_json_response(response)
            
            if isinstance(pain_points, list) and len(pain_points) > 0:
                self.logger.info(f"Generated {len(pain_points)} enhanced pain points")
                return pain_points
            
            return None
            
        except Exception as e:
            self.logger.error(f"Enhanced pain point generation failed: {str(e)}")
            return None

    def _get_mock_pain_points(self) -> List[Dict[str, Any]]:
        """
        Get mock pain points for dry run mode.
        
        Returns:
            Mock pain points list
        """
        return [
            {
                'category': 'Operational Efficiency',
                'description': 'Manual processes and lack of automation leading to increased operational costs and slower response times',
                'impact': 'High - directly affects profitability and customer satisfaction'
            },
            {
                'category': 'Technology Infrastructure',
                'description': 'Outdated systems and lack of integration between different business tools',
                'impact': 'Medium - limiting scalability and data-driven decision making'
            },
            {
                'category': 'Market Competition',
                'description': 'Increasing competition from digital-first companies with more agile business models',
                'impact': 'High - threatening market share and pricing power'
            },
            {
                'category': 'Customer Experience',
                'description': 'Inconsistent customer touchpoints and limited self-service options',
                'impact': 'Medium - affecting customer retention and acquisition costs'
            }
        ]

    def _categorize_and_prioritize_pain_points(self, pain_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Categorize and prioritize pain points.
        
        Args:
            pain_points: List of pain point dictionaries
            
        Returns:
            Categorized and prioritized pain points
        """
        try:
            # Define priority mapping
            impact_priority = {
                'high': 3,
                'medium': 2,
                'low': 1
            }
            
            # Add priority scores and normalize categories
            for pain_point in pain_points:
                # Normalize impact to get priority
                impact = pain_point.get('impact', '').lower()
                if 'high' in impact:
                    pain_point['priority'] = 3
                elif 'medium' in impact:
                    pain_point['priority'] = 2
                else:
                    pain_point['priority'] = 1
                
                # Normalize category
                category = pain_point.get('category', '').strip()
                pain_point['category'] = self._normalize_pain_point_category(category)
            
            # Sort by priority (highest first)
            pain_points.sort(key=lambda x: x.get('priority', 0), reverse=True)
            
            return pain_points
            
        except Exception as e:
            self.logger.error(f"Pain point categorization failed: {str(e)}")
            return pain_points

    def _normalize_pain_point_category(self, category: str) -> str:
        """
        Normalize pain point category names.
        
        Args:
            category: Original category name
            
        Returns:
            Normalized category name
        """
        category_mapping = {
            'operational': 'Operational Efficiency',
            'operations': 'Operational Efficiency',
            'efficiency': 'Operational Efficiency',
            'technology': 'Technology Infrastructure',
            'tech': 'Technology Infrastructure',
            'it': 'Technology Infrastructure',
            'financial': 'Financial Management',
            'finance': 'Financial Management',
            'money': 'Financial Management',
            'market': 'Market Competition',
            'competition': 'Market Competition',
            'competitive': 'Market Competition',
            'customer': 'Customer Experience',
            'customers': 'Customer Experience',
            'service': 'Customer Experience',
            'sales': 'Sales & Marketing',
            'marketing': 'Sales & Marketing',
            'growth': 'Business Growth',
            'scaling': 'Business Growth',
            'compliance': 'Regulatory Compliance',
            'legal': 'Regulatory Compliance',
            'hr': 'Human Resources',
            'talent': 'Human Resources',
            'staff': 'Human Resources'
        }
        
        category_lower = category.lower().strip()
        
        # Check for exact matches first
        if category_lower in category_mapping:
            return category_mapping[category_lower]
        
        # Check for partial matches
        for key, value in category_mapping.items():
            if key in category_lower:
                return value
        
        # Return original if no match found
        return category.title() if category else 'General Business'

    def _enhance_financial_analysis(self, structured_data: Dict[str, Any], customer_info_text: str) -> Dict[str, Any]:
        """
        Enhance financial analysis with additional insights.
        
        Args:
            structured_data: Current structured data
            customer_info_text: Original customer information
            
        Returns:
            Enhanced structured data with better financial analysis
        """
        try:
            company_info = structured_data.get('companyInfo', {})
            current_financial = structured_data.get('financialInfo', {})
            
            # If financial info is sparse, enhance it
            if not current_financial.get('revenueLastThreeYears') and not current_financial.get('profit'):
                enhanced_financial = self._generate_financial_estimates(company_info, customer_info_text)
                if enhanced_financial:
                    structured_data['financialInfo'].update(enhanced_financial)
            
            # Add financial health assessment
            structured_data['financialInfo']['healthAssessment'] = self._assess_financial_health(
                structured_data['financialInfo'], company_info
            )
            
            return structured_data
            
        except Exception as e:
            self.logger.error(f"Financial analysis enhancement failed: {str(e)}")
            return structured_data

    def _generate_financial_estimates(self, company_info: Dict[str, Any], customer_info_text: str) -> Optional[Dict[str, Any]]:
        """
        Generate financial estimates using LLM analysis.
        
        Args:
            company_info: Company information
            customer_info_text: Original customer information
            
        Returns:
            Financial estimates or None if failed
        """
        try:
            if self.is_dry_run():
                return self._get_mock_financial_data()
            
            industry = company_info.get('industry', '')
            company_size = company_info.get('size', '')
            company_name = company_info.get('name', '')
            
            financial_prompt = f"""Based on the following company information, provide realistic financial estimates:

Company: {company_name}
Industry: {industry}
Size: {company_size}
Additional Info: {customer_info_text[:500]}

Provide financial estimates in JSON format:
{{
  "estimatedAnnualRevenue": "revenue range estimate",
  "revenueGrowthTrend": "growth trend analysis",
  "profitMarginEstimate": "estimated profit margin percentage",
  "fundingStage": "likely funding stage",
  "financialChallenges": ["list of likely financial challenges"],
  "revenueStreams": ["likely revenue streams"]
}}

Base estimates on industry standards and company size indicators. Be conservative and realistic."""

            response = self.call_llm(financial_prompt, temperature=0.3)
            financial_data = self.parse_json_response(response)
            
            if isinstance(financial_data, dict):
                self.logger.info("Generated financial estimates")
                return financial_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Financial estimate generation failed: {str(e)}")
            return None

    def _get_mock_financial_data(self) -> Dict[str, Any]:
        """
        Get mock financial data for dry run mode.
        
        Returns:
            Mock financial data
        """
        return {
            'estimatedAnnualRevenue': '$2-5M',
            'revenueGrowthTrend': 'Steady growth of 15-20% annually',
            'profitMarginEstimate': '12-18%',
            'fundingStage': 'Self-funded or Series A',
            'financialChallenges': [
                'Cash flow management during growth phases',
                'Balancing investment in growth vs profitability',
                'Managing operational costs as scale increases'
            ],
            'revenueStreams': [
                'Product sales',
                'Service contracts',
                'Recurring subscriptions'
            ]
        }

    def _assess_financial_health(self, financial_info: Dict[str, Any], company_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess financial health based on available information.
        
        Args:
            financial_info: Financial information
            company_info: Company information
            
        Returns:
            Financial health assessment
        """
        try:
            assessment = {
                'overallRating': 'Unknown',
                'strengths': [],
                'concerns': [],
                'recommendations': []
            }
            
            # Analyze revenue trend if available
            revenue_years = financial_info.get('revenueLastThreeYears', [])
            if len(revenue_years) >= 2:
                # Calculate growth trend
                recent_revenue = revenue_years[-1].get('revenue', 0)
                previous_revenue = revenue_years[-2].get('revenue', 0)
                
                if previous_revenue > 0:
                    growth_rate = ((recent_revenue - previous_revenue) / previous_revenue) * 100
                    
                    if growth_rate > 20:
                        assessment['strengths'].append('Strong revenue growth')
                        assessment['overallRating'] = 'Good'
                    elif growth_rate > 0:
                        assessment['strengths'].append('Positive revenue growth')
                        assessment['overallRating'] = 'Fair'
                    else:
                        assessment['concerns'].append('Declining revenue trend')
                        assessment['overallRating'] = 'Concerning'
            
            # Analyze profit margins
            profit = financial_info.get('profit', 0)
            if profit > 0:
                assessment['strengths'].append('Profitable operations')
            elif profit < 0:
                assessment['concerns'].append('Operating at a loss')
            
            # Industry-specific analysis
            industry = company_info.get('industry', '').lower()
            if 'technology' in industry or 'software' in industry:
                assessment['recommendations'].append('Focus on recurring revenue models')
                assessment['recommendations'].append('Invest in R&D for competitive advantage')
            elif 'manufacturing' in industry:
                assessment['recommendations'].append('Optimize supply chain efficiency')
                assessment['recommendations'].append('Consider automation investments')
            
            # General recommendations
            if not assessment['recommendations']:
                assessment['recommendations'] = [
                    'Diversify revenue streams',
                    'Improve operational efficiency',
                    'Build cash reserves for growth opportunities'
                ]
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Financial health assessment failed: {str(e)}")
            return {
                'overallRating': 'Unknown',
                'strengths': [],
                'concerns': [],
                'recommendations': ['Conduct detailed financial analysis']
            }

    def _enhance_research_analysis(self, structured_data: Dict[str, Any], customer_info_text: str) -> Dict[str, Any]:
        """
        Enhance research and development analysis.
        
        Args:
            structured_data: Current structured data
            customer_info_text: Original customer information
            
        Returns:
            Enhanced structured data with R&D analysis
        """
        try:
            company_info = structured_data.get('companyInfo', {})
            current_tech = structured_data.get('technologyAndInnovation', {})
            
            # Enhance technology stack analysis
            enhanced_tech = self._analyze_technology_stack(company_info, customer_info_text)
            if enhanced_tech:
                current_tech.update(enhanced_tech)
            
            # Enhance development plans
            enhanced_plans = self._analyze_development_plans(structured_data, customer_info_text)
            if enhanced_plans:
                structured_data['developmentPlans'].update(enhanced_plans)
            
            # Add competitive analysis
            structured_data['competitiveAnalysis'] = self._generate_competitive_analysis(
                company_info, customer_info_text
            )
            
            return structured_data
            
        except Exception as e:
            self.logger.error(f"Research analysis enhancement failed: {str(e)}")
            return structured_data

    def _analyze_technology_stack(self, company_info: Dict[str, Any], customer_info_text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze and estimate technology stack.
        
        Args:
            company_info: Company information
            customer_info_text: Original customer information
            
        Returns:
            Technology analysis or None if failed
        """
        try:
            if self.is_dry_run():
                return self._get_mock_technology_analysis()
            
            industry = company_info.get('industry', '')
            company_size = company_info.get('size', '')
            
            tech_prompt = f"""Analyze the likely technology stack and innovation needs for this company:

Industry: {industry}
Company Size: {company_size}
Company Info: {customer_info_text[:400]}

Provide analysis in JSON format:
{{
  "likelyTechStack": ["list of technologies they probably use"],
  "technologyGaps": ["areas where they might need technology improvements"],
  "innovationOpportunities": ["potential areas for innovation"],
  "digitalMaturityLevel": "assessment of digital maturity (Basic/Intermediate/Advanced)",
  "recommendedTechnologies": ["technologies that could benefit them"]
}}

Focus on realistic, industry-appropriate technology assessments."""

            response = self.call_llm(tech_prompt, temperature=0.3)
            tech_analysis = self.parse_json_response(response)
            
            if isinstance(tech_analysis, dict):
                self.logger.info("Generated technology stack analysis")
                return tech_analysis
            
            return None
            
        except Exception as e:
            self.logger.error(f"Technology stack analysis failed: {str(e)}")
            return None

    def _get_mock_technology_analysis(self) -> Dict[str, Any]:
        """
        Get mock technology analysis for dry run mode.
        
        Returns:
            Mock technology analysis
        """
        return {
            'likelyTechStack': ['CRM System', 'Email Marketing', 'Basic Analytics', 'Office Suite'],
            'technologyGaps': ['Marketing Automation', 'Advanced Analytics', 'Customer Support Tools'],
            'innovationOpportunities': ['AI-powered customer insights', 'Process automation', 'Mobile solutions'],
            'digitalMaturityLevel': 'Intermediate',
            'recommendedTechnologies': ['Marketing Automation Platform', 'Business Intelligence Tools', 'Cloud Infrastructure']
        }

    def _analyze_development_plans(self, structured_data: Dict[str, Any], customer_info_text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze and enhance development plans.
        
        Args:
            structured_data: Current structured data
            customer_info_text: Original customer information
            
        Returns:
            Enhanced development plans or None if failed
        """
        try:
            company_info = structured_data.get('companyInfo', {})
            pain_points = structured_data.get('painPoints', [])
            
            # Extract key challenges for development planning
            key_challenges = [pp.get('description', '') for pp in pain_points[:3]]
            
            development_analysis = {
                'priorityAreas': self._identify_priority_development_areas(company_info, pain_points),
                'timelineEstimates': self._estimate_development_timelines(company_info),
                'resourceRequirements': self._estimate_resource_requirements(company_info, pain_points),
                'riskFactors': self._identify_development_risks(company_info, pain_points)
            }
            
            return development_analysis
            
        except Exception as e:
            self.logger.error(f"Development plans analysis failed: {str(e)}")
            return None

    def _identify_priority_development_areas(self, company_info: Dict[str, Any], pain_points: List[Dict[str, Any]]) -> List[str]:
        """
        Identify priority development areas based on pain points.
        
        Args:
            company_info: Company information
            pain_points: List of pain points
            
        Returns:
            List of priority development areas
        """
        priority_areas = []
        
        for pain_point in pain_points:
            category = pain_point.get('category', '').lower()
            
            if 'operational' in category or 'efficiency' in category:
                priority_areas.append('Process Optimization')
            elif 'technology' in category:
                priority_areas.append('Technology Modernization')
            elif 'customer' in category:
                priority_areas.append('Customer Experience Enhancement')
            elif 'financial' in category:
                priority_areas.append('Financial Management Systems')
            elif 'market' in category or 'competition' in category:
                priority_areas.append('Market Expansion Strategy')
        
        # Remove duplicates and limit to top 5
        return list(dict.fromkeys(priority_areas))[:5]

    def _estimate_development_timelines(self, company_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Estimate development timelines based on company size.
        
        Args:
            company_info: Company information
            
        Returns:
            Timeline estimates
        """
        company_size = company_info.get('size', '').lower()
        
        if 'small' in company_size or 'startup' in company_size:
            return {
                'shortTerm': '3-6 months',
                'mediumTerm': '6-12 months',
                'longTerm': '1-2 years'
            }
        elif 'large' in company_size or 'enterprise' in company_size:
            return {
                'shortTerm': '6-12 months',
                'mediumTerm': '1-2 years',
                'longTerm': '2-3 years'
            }
        else:  # Medium size
            return {
                'shortTerm': '4-8 months',
                'mediumTerm': '8-18 months',
                'longTerm': '1.5-2.5 years'
            }

    def _estimate_resource_requirements(self, company_info: Dict[str, Any], pain_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Estimate resource requirements for development.
        
        Args:
            company_info: Company information
            pain_points: List of pain points
            
        Returns:
            Resource requirement estimates
        """
        return {
            'budgetRange': 'Varies by project scope',
            'keyRoles': ['Project Manager', 'Technical Lead', 'Business Analyst'],
            'externalSupport': 'May require consultants for specialized areas',
            'trainingNeeds': 'Staff training on new processes and technologies'
        }

    def _identify_development_risks(self, company_info: Dict[str, Any], pain_points: List[Dict[str, Any]]) -> List[str]:
        """
        Identify potential development risks.
        
        Args:
            company_info: Company information
            pain_points: List of pain points
            
        Returns:
            List of development risks
        """
        return [
            'Resource allocation conflicts with daily operations',
            'Change management resistance from staff',
            'Technology integration challenges',
            'Budget overruns due to scope creep',
            'Timeline delays due to unforeseen complications'
        ]

    def _generate_competitive_analysis(self, company_info: Dict[str, Any], customer_info_text: str) -> Dict[str, Any]:
        """
        Generate competitive analysis insights.
        
        Args:
            company_info: Company information
            customer_info_text: Original customer information
            
        Returns:
            Competitive analysis insights
        """
        try:
            industry = company_info.get('industry', '')
            company_size = company_info.get('size', '')
            
            return {
                'competitivePosition': self._assess_competitive_position(industry, company_size),
                'marketTrends': self._identify_market_trends(industry),
                'competitiveAdvantages': self._identify_potential_advantages(company_info),
                'threats': self._identify_competitive_threats(industry, company_size),
                'opportunities': self._identify_market_opportunities(industry, company_size)
            }
            
        except Exception as e:
            self.logger.error(f"Competitive analysis failed: {str(e)}")
            return {
                'competitivePosition': 'Analysis pending',
                'marketTrends': [],
                'competitiveAdvantages': [],
                'threats': [],
                'opportunities': []
            }

    def _assess_competitive_position(self, industry: str, company_size: str) -> str:
        """Assess competitive position based on industry and size."""
        if 'small' in company_size.lower():
            return 'Niche player with agility advantages'
        elif 'large' in company_size.lower():
            return 'Established player with resource advantages'
        else:
            return 'Mid-market player with growth potential'

    def _identify_market_trends(self, industry: str) -> List[str]:
        """Identify relevant market trends."""
        industry_lower = industry.lower()
        
        if 'technology' in industry_lower or 'software' in industry_lower:
            return ['Digital transformation acceleration', 'AI/ML adoption', 'Cloud migration', 'Remote work tools']
        elif 'retail' in industry_lower or 'ecommerce' in industry_lower:
            return ['Omnichannel experiences', 'Personalization', 'Sustainability focus', 'Mobile commerce']
        elif 'healthcare' in industry_lower:
            return ['Telemedicine growth', 'Digital health records', 'Patient experience focus', 'Regulatory compliance']
        else:
            return ['Digital transformation', 'Customer experience focus', 'Operational efficiency', 'Sustainability']

    def _identify_potential_advantages(self, company_info: Dict[str, Any]) -> List[str]:
        """Identify potential competitive advantages."""
        return [
            'Local market knowledge',
            'Personalized customer service',
            'Agile decision making',
            'Specialized expertise'
        ]

    def _identify_competitive_threats(self, industry: str, company_size: str) -> List[str]:
        """Identify competitive threats."""
        return [
            'Larger competitors with more resources',
            'New market entrants with innovative solutions',
            'Price competition from low-cost providers',
            'Technology disruption changing industry dynamics'
        ]

    def _identify_market_opportunities(self, industry: str, company_size: str) -> List[str]:
        """Identify market opportunities."""
        return [
            'Underserved market segments',
            'Technology adoption gaps',
            'Partnership opportunities',
            'Geographic expansion potential'
        ]

    def _get_llm_instruction(self) -> str:
        """
        Get the LLM instruction from the original YAML workflow.
        
        Returns:
            LLM instruction text
        """
        return """Role: Customer research analyst conducting comprehensive data gathering on provided companies.

Objective: Based on the provided customer information. Conduct a comprehensive search to infer detailed customer information. Use online search tools, company databases, and public sources to gather accurate, up-to-date data. Ensure all fields in the JSON schema below are completed with reliable information.

If information is unavailable, use an empty string ('') for string fields. However, painPoints must always contain relevant data inferred from the company's description, industry, or general challenges associated with its sector. 

Return only the JSON result, strictly following the schema, without any additional explanation.

**JSON Schema**:
```
{'companyInfo':{'name':'','industry':'','size':'','annualRevenue':'','address':'','website':''},'primaryContact':{'name':'','position':'','email':'','phone':'','linkedIn':''},'currentTechStack':[],'painPoints':[{'category':'','description':'','impact':''}],'financialInfo':{'revenueLastThreeYears':[{'year':0,'revenue':0}],'profit':0,'fundingSources':[]},'legalInfo':{'taxCode':'','businessLicense':'','foundingYear':0},'productsAndServices':{'mainProducts':[],'targetMarket':[]},'developmentPlans':{'shortTermGoals':[],'longTermGoals':[]},'technologyAndInnovation':{'rdProjects':[],'patents':[{'name':'','number':'','filingDate':''}]}}
```
**Key Focus Areas**:
1. Pain Points: Highlight specific issues the company may face, such as financial challenges, operational inefficiencies, market positioning struggles, or customer satisfaction concerns. Always include specific issues the company may face, inferred from its description, industry, or general market challenges.
2. Accuracy: Ensure all provided data is reliable and up-to-date.
3. Fallbacks: For unavailable data, fill fields with empty strings ('') or empty arrays ([]).
Note: Return only the JSON output, without the json keyword or additional commentary."""

    def _get_mock_structured_data(self) -> Dict[str, Any]:
        """
        Get mock structured data for dry run mode.
        
        Returns:
            Mock structured customer data
        """
        return {
            'companyInfo': {
                'name': 'Example Corp',
                'industry': 'Technology',
                'size': 'Medium (50-200 employees)',
                'annualRevenue': '$5-10M',
                'address': '123 Main St, City, State',
                'website': 'https://example.com'
            },
            'primaryContact': {
                'name': 'John Doe',
                'position': 'CEO',
                'email': 'john@example.com',
                'phone': '+1-555-0123',
                'linkedIn': 'https://linkedin.com/in/johndoe'
            },
            'currentTechStack': ['CRM', 'Email Marketing', 'Analytics'],
            'painPoints': [
                {
                    'category': 'Operational Efficiency',
                    'description': 'Manual processes causing delays and errors',
                    'impact': 'High - affecting customer satisfaction and costs'
                },
                {
                    'category': 'Data Management',
                    'description': 'Scattered data across multiple systems',
                    'impact': 'Medium - limiting insights and decision making'
                }
            ],
            'financialInfo': {
                'revenueLastThreeYears': [
                    {'year': 2023, 'revenue': 8500000},
                    {'year': 2022, 'revenue': 7200000},
                    {'year': 2021, 'revenue': 6100000}
                ],
                'profit': 1200000,
                'fundingSources': ['Self-funded', 'Bank loan']
            },
            'legalInfo': {
                'taxCode': 'TC123456789',
                'businessLicense': 'BL987654321',
                'foundingYear': 2018
            },
            'productsAndServices': {
                'mainProducts': ['Software Solutions', 'Consulting Services'],
                'targetMarket': ['SMB', 'Enterprise']
            },
            'developmentPlans': {
                'shortTermGoals': ['Improve operational efficiency', 'Expand customer base'],
                'longTermGoals': ['International expansion', 'Product diversification']
            },
            'technologyAndInnovation': {
                'rdProjects': ['AI Integration', 'Mobile App Development'],
                'patents': [
                    {
                        'name': 'Automated Process Management',
                        'number': 'US123456789',
                        'filingDate': '2023-01-15'
                    }
                ]
            }
        }

    def _get_fallback_structured_data(self, customer_info_text: str) -> Dict[str, Any]:
        """
        Get fallback structured data when LLM extraction fails.
        Uses data from acquisition stage if available.
        
        Args:
            customer_info_text: Original customer information text
            
        Returns:
            Minimal structured customer data with available contact info
        """
        # Try to get acquisition data from context
        acquisition_data = getattr(self, '_current_acquisition_data', {})
        
        return {
            'companyInfo': {
                'name': acquisition_data.get('company_name', ''),
                'industry': '',
                'size': '',
                'annualRevenue': '',
                'address': acquisition_data.get('customer_address', ''),
                'website': acquisition_data.get('company_website', '')
            },
            'primaryContact': {
                'name': acquisition_data.get('contact_name', ''),
                'position': '',
                'email': acquisition_data.get('customer_email', ''),
                'phone': acquisition_data.get('customer_phone', ''),
                'linkedIn': acquisition_data.get('customer_linkedin', '')
            },
            'currentTechStack': [],
            'painPoints': [
                {
                    'category': 'General Business Challenges',
                    'description': 'Common business challenges that may affect operational efficiency and growth',
                    'impact': 'Medium - typical for businesses in competitive markets'
                }
            ],
            'financialInfo': {
                'revenueLastThreeYears': [],
                'profit': 0,
                'fundingSources': []
            },
            'legalInfo': {
                'taxCode': '',
                'businessLicense': '',
                'foundingYear': 0
            },
            'productsAndServices': {
                'mainProducts': [],
                'targetMarket': []
            },
            'developmentPlans': {
                'shortTermGoals': [],
                'longTermGoals': []
            },
            'technologyAndInnovation': {
                'rdProjects': [],
                'patents': []
            },
            'rawCustomerInfo': customer_info_text[:1000] + "..." if len(customer_info_text) > 1000 else customer_info_text
        }

    def _validate_and_clean_data(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean the structured data.
        
        Args:
            structured_data: Raw structured data from LLM
            
        Returns:
            Validated and cleaned structured data
        """
        try:
            # Ensure all required sections exist
            required_sections = [
                'companyInfo', 'primaryContact', 'currentTechStack', 'painPoints',
                'financialInfo', 'legalInfo', 'productsAndServices', 
                'developmentPlans', 'technologyAndInnovation'
            ]
            
            for section in required_sections:
                if section not in structured_data:
                    structured_data[section] = {}
            
            # Validate companyInfo
            company_info = structured_data.get('companyInfo', {})
            required_company_fields = ['name', 'industry', 'size', 'annualRevenue', 'address', 'website']
            for field in required_company_fields:
                if field not in company_info:
                    company_info[field] = ''
            
            # Validate primaryContact
            contact = structured_data.get('primaryContact', {})
            required_contact_fields = ['name', 'position', 'email', 'phone', 'linkedIn']
            for field in required_contact_fields:
                if field not in contact:
                    contact[field] = ''
            
            # Ensure painPoints is always a list with at least one item
            pain_points = structured_data.get('painPoints', [])
            if not pain_points or not isinstance(pain_points, list):
                pain_points = [
                    {
                        'category': 'Business Operations',
                        'description': 'General operational challenges common in the industry',
                        'impact': 'Medium'
                    }
                ]
            structured_data['painPoints'] = pain_points
            
            # Validate financial info
            financial_info = structured_data.get('financialInfo', {})
            if 'revenueLastThreeYears' not in financial_info:
                financial_info['revenueLastThreeYears'] = []
            if 'profit' not in financial_info:
                financial_info['profit'] = 0
            if 'fundingSources' not in financial_info:
                financial_info['fundingSources'] = []
            
            # Validate legal info
            legal_info = structured_data.get('legalInfo', {})
            required_legal_fields = ['taxCode', 'businessLicense', 'foundingYear']
            for field in required_legal_fields:
                if field not in legal_info:
                    legal_info[field] = '' if field != 'foundingYear' else 0
            
            # Ensure lists are actually lists
            list_fields = [
                ('currentTechStack', []),
                ('productsAndServices', {'mainProducts': [], 'targetMarket': []}),
                ('developmentPlans', {'shortTermGoals': [], 'longTermGoals': []}),
                ('technologyAndInnovation', {'rdProjects': [], 'patents': []})
            ]
            
            for field, default in list_fields:
                if field not in structured_data:
                    structured_data[field] = default
                elif isinstance(default, dict):
                    for subfield, subdefault in default.items():
                        if subfield not in structured_data[field]:
                            structured_data[field][subfield] = subdefault
            
            self.logger.info("Successfully validated and cleaned structured data")
            return structured_data
            
        except Exception as e:
            self.logger.error(f"Data validation failed: {str(e)}")
            return structured_data  # Return as-is if validation fails

    def _save_customer_data(self, context: Dict[str, Any], structured_data: Dict[str, Any]) -> None:
        """
        Save customer data to local database.
        
        Args:
            context: Execution context
            structured_data: Structured customer data
        """
        try:
            execution_id = context.get('execution_id')
            task_id = context.get('task_id', execution_id)
            company_info = structured_data.get('companyInfo', {})
            contact_info = structured_data.get('primaryContact', {})
            
            # Save to customers table (basic customer info)
            customer_data = {
                'customer_id': execution_id,
                'org_id': self.config.get('org_id', ''),
                'company_name': company_info.get('name', ''),
                'website': company_info.get('website', ''),
                'industry': company_info.get('industry', ''),
                'contact_name': contact_info.get('name', ''),
                'contact_email': contact_info.get('email', ''),
                'contact_phone': contact_info.get('phone', ''),
                'address': company_info.get('address', ''),
                'profile_data': json.dumps(structured_data)
            }
            
            # Save customer data to customers table
            self.data_manager.save_customer(customer_data)
            self.logger.info(f"Customer data saved to customers table: {execution_id}")
            
            # Save to gs_customer_llmtask table (server-compatible)
            customer_task_data = {
                'task_id': task_id,
                'customer_id': execution_id,
                'customer_name': company_info.get('name', ''),
                'customer_phone': contact_info.get('phone', ''),
                'customer_address': company_info.get('address', ''),
                'customer_email': contact_info.get('email', ''),
                'customer_industry': company_info.get('industry', ''),
                'customer_taxcode': company_info.get('taxCode', ''),
                'customer_website': company_info.get('website', ''),
                'contact_name': contact_info.get('name', ''),
                'org_id': self.config.get('org_id', ''),
                'org_name': self.config.get('org_name', ''),
                'project_code': 'FUSESELL',
                'crm_dob': contact_info.get('dateOfBirth'),
                'image_url': ''
            }
            
            # Save customer task data to gs_customer_llmtask table
            self.data_manager.save_customer_task(customer_task_data)
            self.logger.info(f"Customer task data saved to gs_customer_llmtask table: {task_id}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save customer data: {str(e)}")

    def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        Validate input data for data preparation stage.

        Args:
            context: Execution context

        Returns:
            True if input is valid
        """
        # Check if we have data from data acquisition stage
        stage_results = context.get('stage_results', {})
        if 'data_acquisition' in stage_results:
            return True
        
        # Fallback: check if we have basic input data
        input_data = context.get('input_data', {})
        return bool(input_data.get('customer_website') or input_data.get('customer_description'))

    def get_required_fields(self) -> List[str]:
        """
        Get list of required input fields for this stage.
        
        Returns:
            List of required field names
        """
        return []  # This stage depends on data_acquisition stage output
