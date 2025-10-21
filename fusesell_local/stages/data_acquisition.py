"""
Data Acquisition Stage - Extract customer information from multiple sources
Converted from fusesell_data_acquisition.yml
"""

import requests
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import time
from .base_stage import BaseStage


class DataAcquisitionStage(BaseStage):
    """
    Data Acquisition stage for extracting customer information from multiple sources.
    Converts YAML workflow logic to Python implementation.
    """

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute data acquisition stage.

        Args:
            context: Execution context

        Returns:
            Stage execution result
        """
        try:
            input_data = context.get('input_data', {})

            # Collect data from all available sources
            collected_data = []
            data_sources = []

            # 1. Website scraping (matching original YAML: input_website)
            if input_data.get('input_website'):
                website_data = self._scrape_website(
                    input_data['input_website'])
                if website_data:
                    collected_data.append(website_data)
                    data_sources.append('website')
                    self.logger.info("Successfully scraped website data")

            # 2. Customer description (matching original YAML: input_description)
            if input_data.get('input_description'):
                collected_data.append(input_data['input_description'])
                data_sources.append('description')
                self.logger.info("Added customer description")

            # 3. Business card processing (matching original YAML: input_business_card)
            if input_data.get('input_business_card'):
                business_card_data = self._process_business_card(
                    input_data['input_business_card'])
                if business_card_data:
                    collected_data.append(business_card_data)
                    data_sources.append('business_card')
                    self.logger.info("Successfully processed business card")

            # 4. Social media scraping (matching original YAML: input_facebook_url, input_linkedin_url)
            if input_data.get('input_facebook_url'):
                facebook_data = self._scrape_social_media(
                    input_data['input_facebook_url'])
                if facebook_data:
                    collected_data.append(facebook_data)
                    data_sources.append('facebook')
                    self.logger.info("Successfully scraped Facebook data")

            if input_data.get('input_linkedin_url'):
                linkedin_data = self._scrape_social_media(
                    input_data['input_linkedin_url'])
                if linkedin_data:
                    collected_data.append(linkedin_data)
                    data_sources.append('linkedin')
                    self.logger.info("Successfully scraped LinkedIn data")

            # 5. Free text input (matching executor schema: input_freetext)
            if input_data.get('input_freetext'):
                collected_data.append(input_data['input_freetext'])
                data_sources.append('freetext')
                self.logger.info("Added free text input")

            # Combine all collected data
            combined_data = ' '.join(str(data)
                                     for data in collected_data if data)

            if not combined_data:
                raise ValueError("No data could be collected from any source")

            # 5. Extract structured customer information using LLM
            customer_info = self._extract_customer_info(combined_data)

            # 6. Perform additional company research
            research_data = self._perform_company_research(customer_info)

            # 7. Scrape company website if not already done
            website_research_data = self._scrape_company_website(
                customer_info, data_sources)

            # Combine all research data
            mini_research = ' '.join(
                filter(None, [research_data, website_research_data]))

            # Final result
            result_data = {
                **customer_info,
                'company_mini_search': mini_research,
                'research_mini': True,
                'data_sources': data_sources,
                'extraction_status': 'success',
                'customer_id': context.get('execution_id')
            }

            # Save to database
            self.save_stage_result(context, result_data)

            result = self.create_success_result(result_data, context)
            return result

        except Exception as e:
            self.log_stage_error(context, e)
            return self.handle_stage_error(e, context)

    def _scrape_website(self, url: str) -> Optional[str]:
        """
        Scrape website content with enhanced fallback mechanisms.

        Args:
            url: Website URL to scrape

        Returns:
            Scraped text content or None if failed
        """
        try:
            if self.is_dry_run():
                return f"[DRY RUN] Would scrape website: {url}"

            # Step 1: Try direct HTTP request first
            scraped_content = self._direct_website_scrape(url)
            if scraped_content:
                self.logger.info(f"Successfully scraped website directly: {url}")
                return scraped_content

            # Step 2: Try Serper API scraping
            serper_key = self.config.get('serper_api_key')
            if serper_key:
                scraped_content = self._scrape_with_serper(url, serper_key)
                if scraped_content:
                    self.logger.info(f"Successfully scraped website via Serper API: {url}")
                    return scraped_content
                
                # Step 3: Enhanced fallback - Search-based data recovery
                self.logger.info(f"Direct scraping failed for {url}, attempting search-based fallback")
                company_name = self._extract_company_name_from_url(url)
                if company_name:
                    fallback_content = self._search_based_fallback(company_name, serper_key)
                    if fallback_content:
                        self.logger.info(f"Successfully recovered company data via search fallback for: {company_name}")
                        return fallback_content

            self.logger.warning(f"All scraping methods failed for {url}")
            return None

        except Exception as e:
            self.logger.error(f"Website scraping failed for {url}: {str(e)}")
            return None

    def _extract_company_name_from_url(self, url: str) -> Optional[str]:
        """
        Extract company name from URL for search fallback.

        Args:
            url: Website URL

        Returns:
            Extracted company name or None if failed
        """
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove common prefixes
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Extract company name from domain
            # Remove common TLDs
            domain_parts = domain.split('.')
            if len(domain_parts) >= 2:
                company_name = domain_parts[0]
                
                # Clean up common patterns
                company_name = company_name.replace('-', ' ')
                company_name = company_name.replace('_', ' ')
                
                # Capitalize words
                company_name = ' '.join(word.capitalize() for word in company_name.split())
                
                return company_name
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to extract company name from URL {url}: {str(e)}")
            return None

    def _search_based_fallback(self, company_name: str, api_key: str) -> Optional[str]:
        """
        Enhanced fallback mechanism using search to recover company data.

        Args:
            company_name: Company name to search for
            api_key: Serper API key

        Returns:
            Company information from search results or None if failed
        """
        try:
            self.logger.info(f"Attempting search-based fallback for company: {company_name}")
            
            # Try multiple search strategies
            search_queries = [
                f'"{company_name}" company about',
                f'"{company_name}" business services',
                f'{company_name} company profile',
                f'{company_name} official website',
                f'{company_name} contact information'
            ]
            
            all_results = []
            
            for query in search_queries:
                try:
                    search_result = self._search_with_serper(query, api_key)
                    if search_result and len(search_result.strip()) > 50:
                        all_results.append(search_result)
                        self.logger.debug(f"Search query '{query}' returned {len(search_result)} characters")
                    
                    # Add small delay between searches to avoid rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.debug(f"Search query '{query}' failed: {str(e)}")
                    continue
            
            if not all_results:
                self.logger.warning(f"No search results found for company: {company_name}")
                return None
            
            # Combine and deduplicate results
            combined_results = ' '.join(all_results)
            
            # Limit length to avoid token limits
            if len(combined_results) > 3000:
                combined_results = combined_results[:3000] + "..."
            
            # Try to find alternative URLs in search results
            alternative_urls = self._extract_urls_from_search_results(combined_results)
            
            # If we found alternative URLs, try scraping them
            for alt_url in alternative_urls[:3]:  # Try up to 3 alternative URLs
                try:
                    self.logger.info(f"Trying alternative URL from search: {alt_url}")
                    scraped_content = self._direct_website_scrape(alt_url)
                    if scraped_content and len(scraped_content.strip()) > 100:
                        self.logger.info(f"Successfully scraped alternative URL: {alt_url}")
                        return f"Search Results: {combined_results}\n\nAlternative Website Content: {scraped_content}"
                except Exception as e:
                    self.logger.debug(f"Failed to scrape alternative URL {alt_url}: {str(e)}")
                    continue
            
            # Return search results even if no alternative URLs worked
            self.logger.info(f"Returning search results for company: {company_name}")
            return f"Search Results: {combined_results}"
            
        except Exception as e:
            self.logger.error(f"Search-based fallback failed for {company_name}: {str(e)}")
            return None

    def _extract_urls_from_search_results(self, search_text: str) -> List[str]:
        """
        Extract potential website URLs from search results.

        Args:
            search_text: Search results text

        Returns:
            List of extracted URLs
        """
        try:
            import re
            
            # Pattern to match URLs in search results
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, search_text, re.IGNORECASE)
            
            # Filter out common non-company URLs
            filtered_urls = []
            exclude_domains = [
                'google.com', 'facebook.com', 'linkedin.com', 'twitter.com',
                'instagram.com', 'youtube.com', 'wikipedia.org', 'yelp.com',
                'glassdoor.com', 'indeed.com', 'crunchbase.com'
            ]
            
            for url in urls:
                # Skip if it's a social media or directory site
                if not any(domain in url.lower() for domain in exclude_domains):
                    # Skip if it's too long (likely not a main company website)
                    if len(url) < 100:
                        filtered_urls.append(url)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in filtered_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            return unique_urls[:5]  # Return top 5 URLs
            
        except Exception as e:
            self.logger.debug(f"Failed to extract URLs from search results: {str(e)}")
            return []

    def _direct_website_scrape(self, url: str) -> Optional[str]:
        """
        Direct website scraping using requests and basic HTML parsing.

        Args:
            url: Website URL to scrape

        Returns:
            Scraped text content or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Basic HTML parsing to extract text
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get text content
                text = soup.get_text()

                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip()
                          for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)

                # Limit text length to avoid token limits
                if len(text) > 5000:
                    text = text[:5000] + "..."

                return text

            except ImportError:
                self.logger.warning(
                    "BeautifulSoup not available. Install with: pip install beautifulsoup4")
                # Fallback: return raw HTML (limited)
                content = response.text
                if len(content) > 2000:
                    content = content[:2000] + "..."
                return content

        except Exception as e:
            self.logger.error(f"Direct website scraping failed: {str(e)}")
            return None

    def _scrape_with_serper(self, url: str, api_key: str) -> Optional[str]:
        """
        Scrape website using Serper API (original method).

        Args:
            url: Website URL to scrape
            api_key: Serper API key

        Returns:
            Scraped text content or None if failed
        """
        try:
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }

            body = {'url': url}

            response = requests.post(
                'https://scrape.serper.dev',
                json=body,
                headers=headers,
                timeout=300  # 5 minutes
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('text', '')
            else:
                self.logger.warning(
                    f"Serper API returned status {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Serper API scraping failed: {str(e)}")
            return None

    def _process_business_card(self, business_card_url: str) -> Optional[str]:
        """
        Process business card image using OCR.

        Args:
            business_card_url: URL to business card image

        Returns:
            Extracted text from business card or None if failed
        """
        try:
            if self.is_dry_run():
                return f"[DRY RUN] Would process business card: {business_card_url}"

            # Download the image
            image_data = self._download_image(business_card_url)
            if not image_data:
                return None

            # Try OCR processing with different methods
            extracted_text = self._extract_text_from_image(image_data)

            if extracted_text:
                self.logger.info(
                    "Successfully extracted text from business card")
                return extracted_text
            else:
                self.logger.warning(
                    "No text could be extracted from business card")
                return None

        except Exception as e:
            self.logger.error(f"Business card processing failed: {str(e)}")
            return None

    def _download_image(self, image_url: str) -> Optional[bytes]:
        """
        Download image or PDF from URL.

        Args:
            image_url: URL to image or PDF

        Returns:
            Image/PDF data as bytes or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Verify it's an image or PDF
            content_type = response.headers.get('content-type', '').lower()
            if not (content_type.startswith('image/') or content_type == 'application/pdf'):
                self.logger.warning(
                    f"URL does not point to an image or PDF: {content_type}")
                return None

            return response.content

        except Exception as e:
            self.logger.error(
                f"Failed to download file from {image_url}: {str(e)}")
            return None

    def _extract_text_from_image(self, image_data: bytes) -> Optional[str]:
        """
        Extract text from image or PDF using OCR.

        Args:
            image_data: Image or PDF data as bytes

        Returns:
            Extracted text or None if failed
        """
        try:
            # Check if it's a PDF first
            if image_data.startswith(b'%PDF'):
                text = self._extract_text_from_pdf(image_data)
                if text:
                    return text

            # Try Tesseract OCR first (most common)
            text = self._ocr_with_tesseract(image_data)
            if text:
                return text

            # Try EasyOCR as fallback
            text = self._ocr_with_easyocr(image_data)
            if text:
                return text

            # Try cloud OCR services if available
            text = self._ocr_with_cloud_service(image_data)
            if text:
                return text

            return None

        except Exception as e:
            self.logger.error(f"Text extraction failed: {str(e)}")
            return None

    def _extract_text_from_pdf(self, pdf_data: bytes) -> Optional[str]:
        """
        Extract text from PDF business card.

        Args:
            pdf_data: PDF data as bytes

        Returns:
            Extracted text or None if failed
        """
        try:
            import io
            
            # Try PyPDF2 first for text extraction
            text = self._extract_pdf_text_pypdf2(pdf_data)
            if text and len(text.strip()) > 10:
                structured_text = self._extract_business_card_info(text)
                return structured_text if structured_text else text

            # If no text found, convert PDF to image and use OCR
            text = self._extract_pdf_text_via_ocr(pdf_data)
            if text:
                return text

            return None

        except Exception as e:
            self.logger.debug(f"PDF text extraction failed: {str(e)}")
            return None

    def _extract_pdf_text_pypdf2(self, pdf_data: bytes) -> Optional[str]:
        """
        Extract text from PDF using PyPDF2.

        Args:
            pdf_data: PDF data as bytes

        Returns:
            Extracted text or None if failed
        """
        try:
            import PyPDF2
            import io

            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
            
            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            combined_text = ' '.join(text_parts).strip()
            return combined_text if len(combined_text) > 10 else None

        except ImportError:
            self.logger.debug("PyPDF2 not available. Install with: pip install PyPDF2")
            return None
        except Exception as e:
            self.logger.debug(f"PyPDF2 extraction failed: {str(e)}")
            return None

    def _extract_pdf_text_via_ocr(self, pdf_data: bytes) -> Optional[str]:
        """
        Convert PDF to image and extract text via OCR.

        Args:
            pdf_data: PDF data as bytes

        Returns:
            Extracted text or None if failed
        """
        try:
            import fitz  # PyMuPDF
            import io
            from PIL import Image

            # Open PDF
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            
            all_text = []
            
            # Process each page (usually business cards are single page)
            for page_num in range(min(3, len(pdf_document))):  # Max 3 pages
                page = pdf_document[page_num]
                
                # Convert page to image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Extract text using OCR
                text = self._ocr_with_tesseract(img_data)
                if not text:
                    text = self._ocr_with_easyocr(img_data)
                
                if text:
                    all_text.append(text)

            pdf_document.close()
            
            combined_text = ' '.join(all_text).strip()
            if combined_text:
                structured_text = self._extract_business_card_info(combined_text)
                return structured_text if structured_text else combined_text

            return None

        except ImportError:
            self.logger.debug("PyMuPDF not available. Install with: pip install PyMuPDF")
            return None
        except Exception as e:
            self.logger.debug(f"PDF OCR extraction failed: {str(e)}")
            return None

    def _ocr_with_tesseract(self, image_data: bytes) -> Optional[str]:
        """
        Extract text using Tesseract OCR with image preprocessing.

        Args:
            image_data: Image data as bytes

        Returns:
            Extracted text or None if failed
        """
        try:
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter
            import io

            # Load image
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Apply image preprocessing for better OCR accuracy
            processed_image = self._preprocess_image_for_ocr(image)

            # Try different OCR configurations for business cards
            ocr_configs = [
                '--psm 6',  # Uniform block of text
                '--psm 4',  # Single column of text
                '--psm 3',  # Fully automatic page segmentation
                '--psm 8',  # Single word
                '--psm 13'  # Raw line. Treat the image as a single text line
            ]

            best_text = ""
            best_confidence = 0

            for config in ocr_configs:
                try:
                    # Extract text with configuration
                    text = pytesseract.image_to_string(processed_image, lang='eng', config=config)
                    
                    # Get confidence score
                    data = pytesseract.image_to_data(processed_image, lang='eng', config=config, output_type=pytesseract.Output.DICT)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                    # Keep the best result
                    if avg_confidence > best_confidence and len(text.strip()) > 10:
                        best_text = text.strip()
                        best_confidence = avg_confidence

                except Exception as e:
                    self.logger.debug(f"OCR config {config} failed: {str(e)}")
                    continue

            # Also try the original image without preprocessing
            try:
                text = pytesseract.image_to_string(image, lang='eng')
                if len(text.strip()) > len(best_text):
                    best_text = text.strip()
            except:
                pass

            # Extract structured information from business card text
            if best_text:
                structured_text = self._extract_business_card_info(best_text)
                return structured_text if structured_text else best_text

            return None

        except ImportError:
            self.logger.debug(
                "Tesseract OCR not available. Install with: pip install pytesseract pillow")
            return None
        except Exception as e:
            self.logger.debug(f"Tesseract OCR failed: {str(e)}")
            return None

    def _preprocess_image_for_ocr(self, image):
        """
        Preprocess image to improve OCR accuracy.

        Args:
            image: PIL Image object

        Returns:
            Preprocessed PIL Image object
        """
        try:
            from PIL import ImageEnhance, ImageFilter
            import numpy as np

            # Convert to grayscale for better OCR
            if image.mode != 'L':
                image = image.convert('L')

            # Resize image if too small (OCR works better on larger images)
            width, height = image.size
            if width < 300 or height < 300:
                scale_factor = max(300 / width, 300 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)

            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)

            # Apply noise reduction
            image = image.filter(ImageFilter.MedianFilter(size=3))

            # Apply slight blur to smooth out noise
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

            return image

        except Exception as e:
            self.logger.debug(f"Image preprocessing failed: {str(e)}")
            return image  # Return original image if preprocessing fails

    def _extract_business_card_info(self, raw_text: str) -> Optional[str]:
        """
        Extract structured information from business card OCR text.

        Args:
            raw_text: Raw OCR text from business card

        Returns:
            Structured business card information
        """
        try:
            import re

            # Clean up the text
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            
            # Initialize extracted info
            extracted_info = {
                'name': None,
                'title': None,
                'company': None,
                'email': None,
                'phone': None,
                'website': None,
                'address': None
            }

            # Email pattern
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            
            # Phone pattern (various formats)
            phone_pattern = r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
            
            # Website pattern
            website_pattern = r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'

            # Extract email
            email_matches = re.findall(email_pattern, raw_text, re.IGNORECASE)
            if email_matches:
                extracted_info['email'] = email_matches[0]

            # Extract phone
            phone_matches = re.findall(phone_pattern, raw_text)
            if phone_matches:
                phone = ''.join(phone_matches[0])
                extracted_info['phone'] = phone

            # Extract website
            website_matches = re.findall(website_pattern, raw_text, re.IGNORECASE)
            if website_matches:
                website = website_matches[0]
                if not website.startswith('http'):
                    website = 'https://' + website
                extracted_info['website'] = website

            # Heuristic extraction for name, title, company
            # Usually name is on the first or second line
            # Title is often after the name
            # Company is often the largest/most prominent text

            if len(lines) >= 1:
                # First line is often the name
                potential_name = lines[0]
                if len(potential_name.split()) <= 4 and not any(char.isdigit() for char in potential_name):
                    extracted_info['name'] = potential_name

            if len(lines) >= 2:
                # Second line might be title
                potential_title = lines[1]
                if len(potential_title.split()) <= 6 and not any(char in potential_title for char in '@.'):
                    extracted_info['title'] = potential_title

            # Look for company name (often contains "Inc", "LLC", "Corp", etc.)
            company_indicators = ['inc', 'llc', 'corp', 'ltd', 'company', 'co.', 'corporation']
            for line in lines:
                if any(indicator in line.lower() for indicator in company_indicators):
                    extracted_info['company'] = line
                    break

            # If no company found with indicators, use the longest line that's not name/title/contact info
            if not extracted_info['company']:
                for line in lines:
                    if (line != extracted_info['name'] and 
                        line != extracted_info['title'] and
                        not re.search(email_pattern, line, re.IGNORECASE) and
                        not re.search(phone_pattern, line) and
                        len(line) > 10):
                        extracted_info['company'] = line
                        break

            # Format the structured output
            structured_parts = []
            if extracted_info['name']:
                structured_parts.append(f"Name: {extracted_info['name']}")
            if extracted_info['title']:
                structured_parts.append(f"Title: {extracted_info['title']}")
            if extracted_info['company']:
                structured_parts.append(f"Company: {extracted_info['company']}")
            if extracted_info['email']:
                structured_parts.append(f"Email: {extracted_info['email']}")
            if extracted_info['phone']:
                structured_parts.append(f"Phone: {extracted_info['phone']}")
            if extracted_info['website']:
                structured_parts.append(f"Website: {extracted_info['website']}")

            if structured_parts:
                return " | ".join(structured_parts)
            else:
                return raw_text  # Return raw text if no structured info found

        except Exception as e:
            self.logger.debug(f"Business card info extraction failed: {str(e)}")
            return raw_text  # Return raw text if processing fails

    def _ocr_with_easyocr(self, image_data: bytes) -> Optional[str]:
        """
        Extract text using EasyOCR with preprocessing.

        Args:
            image_data: Image data as bytes

        Returns:
            Extracted text or None if failed
        """
        try:
            import easyocr
            import numpy as np
            from PIL import Image
            import io

            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Apply preprocessing
            processed_image = self._preprocess_image_for_ocr(image)
            
            # Convert to numpy array for EasyOCR
            image_array = np.array(processed_image)

            # Initialize EasyOCR reader with multiple languages for better detection
            reader = easyocr.Reader(['en'], gpu=False)  # Disable GPU for compatibility

            # Extract text with different confidence thresholds
            results = reader.readtext(image_array, detail=1)

            # Sort results by confidence and position
            high_conf_results = [result for result in results if result[2] > 0.6]
            medium_conf_results = [result for result in results if 0.3 < result[2] <= 0.6]

            # Try high confidence results first
            if high_conf_results:
                text_parts = [result[1] for result in high_conf_results]
                text = ' '.join(text_parts)
                
                # Extract structured info if it looks like a business card
                structured_text = self._extract_business_card_info(text)
                if structured_text:
                    return structured_text
                elif len(text.strip()) > 10:
                    return text.strip()

            # Fall back to medium confidence results
            if medium_conf_results:
                text_parts = [result[1] for result in medium_conf_results]
                text = ' '.join(text_parts)
                
                if len(text.strip()) > 10:
                    return text.strip()

            # Try with original image if preprocessing didn't help
            try:
                original_array = np.array(image)
                results = reader.readtext(original_array, detail=1)
                text_parts = [result[1] for result in results if result[2] > 0.4]
                text = ' '.join(text_parts)
                
                if len(text.strip()) > 10:
                    return text.strip()
            except:
                pass

            return None

        except ImportError:
            self.logger.debug(
                "EasyOCR not available. Install with: pip install easyocr")
            return None
        except Exception as e:
            self.logger.debug(f"EasyOCR failed: {str(e)}")
            return None

    def _ocr_with_cloud_service(self, image_data: bytes) -> Optional[str]:
        """
        Extract text using cloud OCR service (Google Vision API, Azure, etc.).

        Args:
            image_data: Image data as bytes

        Returns:
            Extracted text or None if failed
        """
        try:
            # Try Google Vision API if credentials are available
            google_creds = self.config.get('google_vision_credentials')
            if google_creds:
                return self._ocr_with_google_vision(image_data, google_creds)

            # Try Azure Computer Vision if key is available
            azure_key = self.config.get('azure_vision_key')
            azure_endpoint = self.config.get('azure_vision_endpoint')
            if azure_key and azure_endpoint:
                return self._ocr_with_azure_vision(image_data, azure_key, azure_endpoint)

            self.logger.debug("No cloud OCR service credentials available")
            return None

        except Exception as e:
            self.logger.debug(f"Cloud OCR failed: {str(e)}")
            return None

    def _ocr_with_google_vision(self, image_data: bytes, credentials_path: str) -> Optional[str]:
        """
        Extract text using Google Vision API.

        Args:
            image_data: Image data as bytes
            credentials_path: Path to Google credentials JSON

        Returns:
            Extracted text or None if failed
        """
        try:
            from google.cloud import vision
            import os

            # Set credentials
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

            # Initialize client
            client = vision.ImageAnnotatorClient()

            # Create image object
            image = vision.Image(content=image_data)

            # Perform text detection
            response = client.text_detection(image=image)
            texts = response.text_annotations

            if texts:
                return texts[0].description.strip()

            return None

        except ImportError:
            self.logger.debug(
                "Google Vision API not available. Install with: pip install google-cloud-vision")
            return None
        except Exception as e:
            self.logger.debug(f"Google Vision API failed: {str(e)}")
            return None

    def _ocr_with_azure_vision(self, image_data: bytes, api_key: str, endpoint: str) -> Optional[str]:
        """
        Extract text using Azure Computer Vision API.

        Args:
            image_data: Image data as bytes
            api_key: Azure API key
            endpoint: Azure endpoint URL

        Returns:
            Extracted text or None if failed
        """
        try:
            import time

            # Submit image for OCR
            headers = {
                'Ocp-Apim-Subscription-Key': api_key,
                'Content-Type': 'application/octet-stream'
            }

            # Start OCR operation
            ocr_url = f"{endpoint}/vision/v3.2/read/analyze"
            response = requests.post(ocr_url, headers=headers, data=image_data)
            response.raise_for_status()

            # Get operation location
            operation_url = response.headers['Operation-Location']

            # Poll for results
            for _ in range(10):  # Max 10 attempts
                time.sleep(1)
                result_response = requests.get(operation_url, headers={
                                               'Ocp-Apim-Subscription-Key': api_key})
                result_response.raise_for_status()
                result = result_response.json()

                if result['status'] == 'succeeded':
                    # Extract text from results
                    text_parts = []
                    for read_result in result['analyzeResult']['readResults']:
                        for line in read_result['lines']:
                            text_parts.append(line['text'])

                    return ' '.join(text_parts)
                elif result['status'] == 'failed':
                    break

            return None

        except Exception as e:
            self.logger.debug(f"Azure Vision API failed: {str(e)}")
            return None

    def _scrape_social_media(self, url: str) -> Optional[str]:
        """
        Scrape social media profile data.

        Args:
            url: Social media profile URL

        Returns:
            Scraped profile data or None if failed
        """
        try:
            if self.is_dry_run():
                return f"[DRY RUN] Would scrape social media: {url}"

            # Determine platform and use appropriate scraping method
            if 'linkedin.com' in url.lower():
                return self._scrape_linkedin_profile(url)
            elif 'facebook.com' in url.lower():
                return self._scrape_facebook_profile(url)
            else:
                # Generic social media scraping
                return self._scrape_website(url)

        except Exception as e:
            self.logger.error(
                f"Social media scraping failed for {url}: {str(e)}")
            return None

    def _scrape_linkedin_profile(self, url: str) -> Optional[str]:
        """
        Scrape LinkedIn profile with specific handling for LinkedIn's structure.

        Args:
            url: LinkedIn profile URL

        Returns:
            Scraped LinkedIn profile data or None if failed
        """
        try:
            # LinkedIn has anti-scraping measures, so we'll try different approaches

            # Method 1: Try with Serper API if available (most reliable)
            serper_key = self.config.get('serper_api_key')
            if serper_key:
                linkedin_data = self._scrape_with_serper(url, serper_key)
                if linkedin_data:
                    return linkedin_data

            # Method 2: Try direct scraping with LinkedIn-specific headers
            linkedin_data = self._scrape_linkedin_direct(url)
            if linkedin_data:
                return linkedin_data

            # Method 3: Fallback to generic scraping
            return self._direct_website_scrape(url)

        except Exception as e:
            self.logger.error(f"LinkedIn scraping failed: {str(e)}")
            return None

    def _scrape_linkedin_direct(self, url: str) -> Optional[str]:
        """
        Direct LinkedIn scraping with specific headers and handling.

        Args:
            url: LinkedIn profile URL

        Returns:
            Scraped content or None if failed
        """
        try:
            # LinkedIn-specific headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            # Add delay to avoid rate limiting
            time.sleep(2)

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse LinkedIn-specific content
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract LinkedIn-specific elements
                profile_data = []

                # Try to extract name
                name_selectors = [
                    'h1.text-heading-xlarge',
                    '.pv-text-details__left-panel h1',
                    '.ph5 h1'
                ]
                for selector in name_selectors:
                    name_elem = soup.select_one(selector)
                    if name_elem:
                        profile_data.append(
                            f"Name: {name_elem.get_text().strip()}")
                        break

                # Try to extract headline/title
                headline_selectors = [
                    '.text-body-medium.break-words',
                    '.pv-text-details__left-panel .text-body-medium',
                    '.ph5 .text-body-medium'
                ]
                for selector in headline_selectors:
                    headline_elem = soup.select_one(selector)
                    if headline_elem:
                        profile_data.append(
                            f"Title: {headline_elem.get_text().strip()}")
                        break

                # Try to extract company
                company_selectors = [
                    '.pv-text-details__right-panel',
                    '.pv-entity__summary-info h3',
                    '.experience-section .pv-entity__summary-info h3'
                ]
                for selector in company_selectors:
                    company_elem = soup.select_one(selector)
                    if company_elem:
                        profile_data.append(
                            f"Company: {company_elem.get_text().strip()}")
                        break

                if profile_data:
                    return ' | '.join(profile_data)

                # Fallback: extract all text
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                text = ' '.join(line for line in lines if line)

                if len(text) > 3000:
                    text = text[:3000] + "..."

                return text if len(text) > 50 else None

            except ImportError:
                # Fallback without BeautifulSoup
                content = response.text
                if len(content) > 2000:
                    content = content[:2000] + "..."
                return content

        except Exception as e:
            self.logger.debug(f"Direct LinkedIn scraping failed: {str(e)}")
            return None

    def _scrape_facebook_profile(self, url: str) -> Optional[str]:
        """
        Scrape Facebook profile with specific handling for Facebook's structure.

        Args:
            url: Facebook profile URL

        Returns:
            Scraped Facebook profile data or None if failed
        """
        try:
            # Facebook has strong anti-scraping measures

            # Method 1: Try with Serper API if available (most reliable)
            serper_key = self.config.get('serper_api_key')
            if serper_key:
                facebook_data = self._scrape_with_serper(url, serper_key)
                if facebook_data:
                    return facebook_data

            # Method 2: Try direct scraping with Facebook-specific headers
            facebook_data = self._scrape_facebook_direct(url)
            if facebook_data:
                return facebook_data

            # Method 3: Fallback to generic scraping
            return self._direct_website_scrape(url)

        except Exception as e:
            self.logger.error(f"Facebook scraping failed: {str(e)}")
            return None

    def _scrape_facebook_direct(self, url: str) -> Optional[str]:
        """
        Direct Facebook scraping with specific headers and handling.

        Args:
            url: Facebook profile URL

        Returns:
            Scraped content or None if failed
        """
        try:
            # Facebook-specific headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            }

            # Add delay to avoid rate limiting
            time.sleep(3)

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse Facebook-specific content
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract Facebook-specific elements
                profile_data = []

                # Try to extract page/profile name
                name_selectors = [
                    'h1[data-testid="page_title"]',
                    '.x1heor9g.x1qlqyl8.x1pd3egz.x1a2a7pz h1',
                    '#seo_h1_tag',
                    'title'
                ]
                for selector in name_selectors:
                    name_elem = soup.select_one(selector)
                    if name_elem:
                        name_text = name_elem.get_text().strip()
                        if name_text and len(name_text) > 3:
                            profile_data.append(f"Name: {name_text}")
                            break

                # Try to extract description/about
                desc_selectors = [
                    '[data-testid="page_description"]',
                    '.x1i10hfl.xjbqb8w.x6umtig.x1b1mbwd.xaqea5y.xav7gou.x9f619.x1ypdohk.xt0psk2.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.x1sur9pj.xkrqix3.x1fey0fg.x1s688f',
                    '.x1i10hfl.xjbqb8w.x6umtig.x1b1mbwd.xaqea5y.xav7gou.x9f619.x1ypdohk.xt0psk2.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.x1heor9g.xt0b8zv.xo1l8bm'
                ]
                for selector in desc_selectors:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        desc_text = desc_elem.get_text().strip()
                        if desc_text and len(desc_text) > 10:
                            profile_data.append(f"Description: {desc_text}")
                            break

                if profile_data:
                    return ' | '.join(profile_data)

                # Fallback: extract meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    return f"Description: {meta_desc['content']}"

                # Last fallback: extract title
                title = soup.find('title')
                if title:
                    return f"Title: {title.get_text().strip()}"

                return None

            except ImportError:
                # Fallback without BeautifulSoup
                content = response.text
                if 'Facebook' in content and len(content) > 100:
                    # Extract title from HTML
                    title_start = content.find('<title>')
                    title_end = content.find('</title>')
                    if title_start != -1 and title_end != -1:
                        title = content[title_start + 7:title_end].strip()
                        return f"Title: {title}"
                return None

        except Exception as e:
            self.logger.debug(f"Direct Facebook scraping failed: {str(e)}")
            return None

    def _extract_customer_info(self, raw_data: str) -> Dict[str, Any]:
        """
        Extract structured customer information using LLM.

        Args:
            raw_data: Combined raw data from all sources

        Returns:
            Structured customer information dictionary
        """
        try:
            if self.is_dry_run():
                return {
                    'contact_name': 'John Doe',
                    'company_name': 'Example Corp',
                    'customer_phone': '+1-555-0123',
                    'customer_email': 'contact@example.com',
                    'customer_linkedin': 'https://linkedin.com/company/example',
                    'customer_facebook': 'https://facebook.com/example',
                    'company_website': 'https://example.com',
                    'customer_address': '123 Main St, City, State',
                    'company_business': 'Technology solutions',
                    'company_industries': ['Technology', 'Software'],
                    'founders': ['John Doe'],
                    'branches': ['Main Office'],
                    'customer_description': '[DRY RUN] Mock customer description'
                }

            prompt = f"""This is the customer information: {raw_data}.

Based on the above data, generate a JSON structure with the following format:

{{
  "contact_name": "Name of the contact/representative",
  "company_name": "Name of the company",
  "customer_phone": "Company/Contact phone number in the correct format",
  "customer_email": "Company/Contact email",
  "customer_linkedin": "LinkedIn profile URL",
  "customer_facebook": "Facebook profile URL",
  "company_website": "Company website (valid structure)",
  "customer_address": "Company/Contact address",
  "company_business": "Main business activities of the company",
  "company_industries": ["List of industries or fields of operation"],
  "founders": ["List of founders"],
  "branches": ["List of branches"],
  "customer_description": "All information about the customer"
}}

Rules:
1. Ensure `company_website` is correctly structured as a valid URL.
2. If `company_name` is an array with multiple values:
   - Use available data and context to generate a comprehensive, accurate company name.
3. Return an empty result if the required information is not available.
4. Do not include the word ```JSON in the result.
5. Provide the output directly without any explanations or additional text. In JSON response, use double quotes instead of single quotes."""

            response = self.call_llm(prompt, temperature=0.2)

            # Parse the JSON response
            customer_info = self.parse_json_response(response)

            self.logger.info("Successfully extracted customer information")
            return customer_info

        except Exception as e:
            self.logger.error(f"Customer info extraction failed: {str(e)}")
            # Try basic regex extraction as fallback
            fallback_info = self._extract_basic_info_fallback(raw_data)
            self.logger.info("Using basic regex extraction as fallback")
            return fallback_info

    def _extract_basic_info_fallback(self, raw_data: str) -> Dict[str, Any]:
        """
        Extract basic information using regex patterns when LLM is not available.
        
        Args:
            raw_data: Raw text data to extract from
            
        Returns:
            Dictionary with extracted basic information
        """
        import re
        
        # Initialize result with empty values
        result = {
            'contact_name': '',
            'company_name': '',
            'customer_phone': '',
            'customer_email': '',
            'customer_linkedin': '',
            'customer_facebook': '',
            'company_website': '',
            'customer_address': '',
            'company_business': '',
            'company_industries': [],
            'founders': [],
            'branches': [],
            'customer_description': raw_data[:500] + "..." if len(raw_data) > 500 else raw_data
        }
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, raw_data, re.IGNORECASE)
        if emails:
            result['customer_email'] = emails[0]
        
        # Extract phone numbers (various formats)
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, raw_data)
        if phones:
            result['customer_phone'] = ''.join(phones[0])
        
        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, raw_data, re.IGNORECASE)
        for url in urls:
            if 'linkedin.com' in url.lower():
                result['customer_linkedin'] = url
            elif 'facebook.com' in url.lower():
                result['customer_facebook'] = url
            elif not result['company_website']:  # First non-social URL becomes website
                result['company_website'] = url
        
        # Extract names and companies using common patterns
        # Look for "Customer: Name at Company" pattern
        customer_pattern = r'Customer:\s*([^,\n]+?)(?:\s+at\s+([^,\n]+?))?(?:,|$|\n)'
        customer_match = re.search(customer_pattern, raw_data, re.IGNORECASE)
        if customer_match:
            result['contact_name'] = customer_match.group(1).strip()
            if customer_match.group(2):
                result['company_name'] = customer_match.group(2).strip()
        
        # Look for "Name: value" patterns
        name_patterns = [
            (r'Name:\s*([^\n,]+)', 'contact_name'),
            (r'Company:\s*([^\n,]+)', 'company_name'),
            (r'Organization:\s*([^\n,]+)', 'company_name'),
            (r'Business:\s*([^\n,]+)', 'company_business'),
            (r'Address:\s*([^\n,]+)', 'customer_address')
        ]
        
        for pattern, field in name_patterns:
            match = re.search(pattern, raw_data, re.IGNORECASE)
            if match and not result[field]:  # Only set if not already set
                result[field] = match.group(1).strip()
        
        # If we found an email but no name, try to extract name from email
        if result['customer_email'] and not result['contact_name']:
            email_name = result['customer_email'].split('@')[0]
            # Convert common email formats to names
            if '.' in email_name:
                parts = email_name.split('.')
                result['contact_name'] = ' '.join(part.capitalize() for part in parts)
            else:
                result['contact_name'] = email_name.capitalize()
        
        # If we found an email but no company, try to extract from email domain
        if result['customer_email'] and not result['company_name']:
            domain = result['customer_email'].split('@')[1]
            # Remove common TLDs and convert to company name
            company_part = domain.split('.')[0]
            result['company_name'] = company_part.upper()
        
        return result

    def _perform_company_research(self, customer_info: Dict[str, Any]) -> Optional[str]:
        """
        Perform enhanced company research using multiple search strategies.

        Args:
            customer_info: Extracted customer information

        Returns:
            Research results or None if failed
        """
        try:
            company_name = customer_info.get('company_name', '')
            company_website = customer_info.get('company_website', '')

            if not company_name:
                return None

            if self.is_dry_run():
                return f"[DRY RUN] Would research company: {company_name} {company_website}"

            # Use Serper API for search if available
            serper_key = self.config.get('serper_api_key')
            if not serper_key:
                self.logger.warning("Company research skipped - no Serper API key available")
                return None

            research_results = []

            # Strategy 1: General company search
            general_query = f'"{company_name}" company profile business'
            general_results = self._search_with_serper(general_query, serper_key, 'search')
            if general_results:
                research_results.append(f"General Info: {general_results}")

            # Strategy 2: News search for recent company information
            news_query = f'"{company_name}" company news'
            news_results = self._search_with_serper(news_query, serper_key, 'news')
            if news_results:
                research_results.append(f"Recent News: {news_results}")

            # Strategy 3: Industry-specific search
            if company_website:
                industry_query = f'"{company_name}" industry services products site:{company_website}'
                industry_results = self._search_with_serper(industry_query, serper_key, 'search')
                if industry_results:
                    research_results.append(f"Industry Info: {industry_results}")

            # Strategy 4: Contact and location search
            contact_query = f'"{company_name}" contact address phone location'
            contact_results = self._search_with_serper(contact_query, serper_key, 'search')
            if contact_results:
                research_results.append(f"Contact Info: {contact_results}")

            if research_results:
                combined_research = ' | '.join(research_results)
                # Limit length to avoid token limits
                if len(combined_research) > 4000:
                    combined_research = combined_research[:4000] + "..."
                return combined_research

            return None

        except Exception as e:
            self.logger.error(f"Company research failed: {str(e)}")
            return None

    def _search_with_serper(self, query: str, api_key: str, search_type: str = 'search') -> Optional[str]:
        """
        Enhanced search using Serper API with multiple search types.

        Args:
            query: Search query
            api_key: Serper API key
            search_type: Type of search ('search', 'news', 'images')

        Returns:
            Search results or None if failed
        """
        try:
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }

            body = {
                'q': query,
                'num': 10  # Get more results for better fallback
            }

            # Choose appropriate endpoint
            endpoints = {
                'search': 'https://google.serper.dev/search',
                'news': 'https://google.serper.dev/news',
                'images': 'https://google.serper.dev/images'
            }
            
            endpoint = endpoints.get(search_type, endpoints['search'])

            response = requests.post(
                endpoint,
                json=body,
                headers=headers,
                timeout=60  # Reduced timeout for faster fallback
            )

            if response.status_code == 200:
                result = response.json()
                
                # Extract different types of results based on search type
                if search_type == 'search':
                    return self._process_search_results(result)
                elif search_type == 'news':
                    return self._process_news_results(result)
                else:
                    return self._process_search_results(result)
                    
            elif response.status_code == 429:
                self.logger.warning("Serper API rate limit exceeded, waiting before retry")
                time.sleep(2)
                return None
            else:
                self.logger.warning(
                    f"Serper search API returned status {response.status_code}: {response.text}")
                return None

        except requests.exceptions.Timeout:
            self.logger.warning(f"Serper search timed out for query: {query}")
            return None
        except Exception as e:
            self.logger.error(f"Serper search failed: {str(e)}")
            return None

    def _process_search_results(self, result: Dict[str, Any]) -> Optional[str]:
        """
        Process search results from Serper API.

        Args:
            result: JSON response from Serper API

        Returns:
            Processed search results text
        """
        try:
            processed_parts = []
            
            # Extract knowledge graph info (company info box)
            knowledge_graph = result.get('knowledgeGraph', {})
            if knowledge_graph:
                kg_title = knowledge_graph.get('title', '')
                kg_description = knowledge_graph.get('description', '')
                kg_attributes = knowledge_graph.get('attributes', {})
                
                if kg_title:
                    processed_parts.append(f"Company: {kg_title}")
                if kg_description:
                    processed_parts.append(f"Description: {kg_description}")
                
                # Add relevant attributes
                for key, value in kg_attributes.items():
                    if key.lower() in ['founded', 'headquarters', 'ceo', 'industry', 'revenue']:
                        processed_parts.append(f"{key}: {value}")
            
            # Extract organic results
            organic_results = result.get('organic', [])
            snippets = []
            
            for item in organic_results:
                title = item.get('title', '')
                snippet = item.get('snippet', '')
                link = item.get('link', '')
                
                if snippet:
                    # Combine title and snippet for better context
                    if title:
                        snippets.append(f"{title}: {snippet}")
                    else:
                        snippets.append(snippet)
            
            if snippets:
                processed_parts.extend(snippets[:5])  # Top 5 results
            
            # Extract answer box if available
            answer_box = result.get('answerBox', {})
            if answer_box:
                answer = answer_box.get('answer', '')
                if answer:
                    processed_parts.insert(0, f"Answer: {answer}")
            
            return ' | '.join(processed_parts) if processed_parts else None
            
        except Exception as e:
            self.logger.debug(f"Failed to process search results: {str(e)}")
            # Fallback to simple snippet extraction
            organic_results = result.get('organic', [])
            snippets = [item.get('snippet', '') for item in organic_results if 'snippet' in item]
            return ', '.join(snippets) if snippets else None

    def _process_news_results(self, result: Dict[str, Any]) -> Optional[str]:
        """
        Process news results from Serper API.

        Args:
            result: JSON response from Serper API

        Returns:
            Processed news results text
        """
        try:
            news_results = result.get('news', [])
            news_snippets = []
            
            for item in news_results[:3]:  # Top 3 news items
                title = item.get('title', '')
                snippet = item.get('snippet', '')
                date = item.get('date', '')
                
                if snippet:
                    news_item = f"{title}: {snippet}"
                    if date:
                        news_item += f" ({date})"
                    news_snippets.append(news_item)
            
            return ' | '.join(news_snippets) if news_snippets else None
            
        except Exception as e:
            self.logger.debug(f"Failed to process news results: {str(e)}")
            return None

    def _scrape_company_website(self, customer_info: Dict[str, Any], data_sources: List[str]) -> Optional[str]:
        """
        Scrape company website if not already scraped.

        Args:
            customer_info: Extracted customer information
            data_sources: List of already processed data sources

        Returns:
            Website content or None if failed/skipped
        """
        try:
            # Only scrape if website wasn't already processed
            if 'website' in data_sources:
                return None

            company_website = customer_info.get('company_website', '')
            if not company_website:
                return None

            return self._scrape_website(company_website)

        except Exception as e:
            self.logger.error(f"Company website research failed: {str(e)}")
            return None

    def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        Validate input data for data acquisition stage.

        Args:
            context: Execution context

        Returns:
            True if input is valid
        """
        input_data = context.get('input_data', {})

        # Check if at least one data source is available (matching executor schema)
        sources = [
            input_data.get('input_website'),
            input_data.get('input_description'),
            input_data.get('input_business_card'),
            input_data.get('input_linkedin_url'),
            input_data.get('input_facebook_url'),
            input_data.get('input_freetext')
        ]

        return any(sources)

    def get_required_fields(self) -> List[str]:
        """
        Get list of required input fields for this stage.

        Returns:
            List of required field names (at least one data source required)
        """
        return []  # No strictly required fields, but at least one source needed
