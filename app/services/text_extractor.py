"""
Text extraction service using BeautifulSoup for travel booking sites.
Removes navigation, ads, and irrelevant content while preserving booking information.
"""

import re
import logging
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse


class TextExtractor:
    """
    Extracts clean text from HTML content of travel booking sites.
    Focuses on preserving booking-relevant information while removing noise.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common selectors for irrelevant content to remove
        self.noise_selectors = [
            'nav', 'header', 'footer', 'aside',
            '.navigation', '.nav', '.menu', '.sidebar',
            '.advertisement', '.ad', '.ads', '.banner',
            '.social', '.share', '.newsletter', '.popup',
            '.cookie', '.gdpr', '.privacy-notice',
            'script', 'style', 'noscript', 'iframe',
            '.comments', '.reviews-summary', '.user-reviews',
            '.breadcrumb', '.breadcrumbs'
        ]
        
        # Selectors for content that's likely to contain booking information
        self.booking_content_selectors = [
            '.booking', '.reservation', '.itinerary',
            '.flight-details', '.hotel-details', '.property-details',
            '.price', '.cost', '.fare', '.rate', '.total',
            '.date', '.time', '.duration', '.nights',
            '.guest', '.passenger', '.traveler',
            '.location', '.destination', '.airport', '.city',
            '.room', '.accommodation', '.property',
            '[data-testid*="price"]', '[data-testid*="date"]',
            '[data-testid*="flight"]', '[data-testid*="hotel"]'
        ]
        
        # Platform-specific selectors for better extraction
        self.platform_selectors = {
            'google.com': {
                'booking_content': [
                    '[data-ved]', '.gws-flights__booking-card',
                    '.gws-flights__itinerary', '.gws-flights__price'
                ],
                'noise': ['.gws-flights__ads', '.gws-flights__footer']
            },
            'airbnb.com': {
                'booking_content': [
                    '[data-testid="listing-details"]',
                    '[data-testid="price-breakdown"]',
                    '.listing-summary', '.booking-form'
                ],
                'noise': ['.navigation', '.footer', '.reviews-section']
            },
            'booking.com': {
                'booking_content': [
                    '.hp__hotel-title', '.prco-valign-middle-helper',
                    '.bui-price-display', '.c-accommodation-header'
                ],
                'noise': ['.bui-header', '.bui-footer', '.sr-usp-overlay']
            },
            'hotels.com': {
                'booking_content': [
                    '.hotel-name', '.price-current', '.room-rate-item',
                    '.booking-summary'
                ],
                'noise': ['.site-header', '.site-footer', '.advertisement']
            }
        }

    def extract_text(self, html_content: str, url: Optional[str] = None) -> str:
        """
        Extract clean text from HTML content, preserving booking information.
        
        Args:
            html_content: Raw HTML content
            url: Optional URL to determine platform-specific extraction
            
        Returns:
            Clean text with booking information preserved
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Determine platform for specialized extraction
            platform = self._get_platform(url) if url else None
            
            # Remove noise elements
            self._remove_noise_elements(soup, platform)
            
            # Extract booking-relevant content
            booking_text = self._extract_booking_content(soup, platform)
            
            # Clean and normalize the text
            clean_text = self._clean_text(booking_text)
            
            self.logger.info(f"Extracted {len(clean_text)} characters of clean text")
            return clean_text
            
        except Exception as e:
            self.logger.error(f"Error extracting text: {str(e)}")
            raise

    def _get_platform(self, url: str) -> Optional[str]:
        """Determine the platform from URL for specialized extraction."""
        try:
            domain = urlparse(url).netloc.lower()
            for platform_key in self.platform_selectors.keys():
                if platform_key in domain:
                    return platform_key
            return None
        except Exception:
            return None

    def _remove_noise_elements(self, soup: BeautifulSoup, platform: Optional[str] = None):
        """Remove navigation, ads, and other irrelevant content."""
        # Platform-specific noise removal
        if platform and platform in self.platform_selectors:
            platform_noise = self.platform_selectors[platform].get('noise', [])
            for selector in platform_noise:
                for element in soup.select(selector):
                    element.decompose()
        
        # General noise removal
        for selector in self.noise_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove elements with common noise class patterns
        # Be more specific to avoid false positives like "c-accommodation-header"
        noise_patterns = [
            r'^ad$', r'^ads$', r'advertisement', r'banner', r'popup', r'modal',
            r'cookie', r'gdpr', r'newsletter', r'social-share', r'promo'
        ]
        
        for pattern in noise_patterns:
            for element in soup.find_all(attrs={'class': re.compile(pattern, re.I)}):
                element.decompose()

    def _extract_booking_content(self, soup: BeautifulSoup, platform: Optional[str] = None) -> str:
        """Extract text from elements likely to contain booking information."""
        booking_texts = []
        
        # Platform-specific content extraction
        if platform and platform in self.platform_selectors:
            platform_selectors = self.platform_selectors[platform].get('booking_content', [])
            for selector in platform_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = self._extract_element_text(element)
                    if text.strip():
                        booking_texts.append(text)
        
        # Always try general booking content extraction as well
        for selector in self.booking_content_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = self._extract_element_text(element)
                if text.strip():
                    booking_texts.append(text)
        
        # If no specific booking content found, extract from main content areas
        if not booking_texts:
            main_selectors = ['main', '.main', '#main', '.content', '.container']
            for selector in main_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = self._extract_element_text(element)
                    if text.strip():
                        booking_texts.append(text)
        
        # Fallback to body text if nothing else found
        if not booking_texts:
            body = soup.find('body')
            if body:
                booking_texts.append(self._extract_element_text(body))
        
        return '\n'.join(booking_texts)

    def _extract_element_text(self, element: Tag) -> str:
        """Extract text from a BeautifulSoup element, preserving structure."""
        if not element:
            return ""
        
        # Use get_text() with separator to preserve some structure
        text = element.get_text(separator=' ', strip=True)
        return text

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # BeautifulSoup already handles HTML entity decoding and tag removal
        # We should not need to remove HTML tags here since BeautifulSoup.get_text() 
        # already extracts only text content
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n\s*\n', '\n', text)  # Multiple newlines to single
        text = re.sub(r'[ \t]+\n', '\n', text)  # Trailing spaces before newlines
        text = re.sub(r'\n[ \t]+', '\n', text)  # Leading spaces after newlines
        
        # Remove common artifacts
        text = re.sub(r'^\s*[\|\-\*\+]\s*', '', text, flags=re.MULTILINE)  # List markers
        text = re.sub(r'\s*[\|\-\*\+]\s*$', '', text, flags=re.MULTILINE)  # Trailing markers
        
        # Clean up excessive punctuation
        text = re.sub(r'[\.]{3,}', '...', text)  # Multiple dots
        text = re.sub(r'[\-]{3,}', '---', text)  # Multiple dashes
        
        return text.strip()

    def extract_structured_data(self, html_content: str, url: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Extract structured data organized by content type.
        
        Returns:
            Dictionary with categorized text content (prices, dates, locations, etc.)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            platform = self._get_platform(url) if url else None
            
            # Remove noise
            self._remove_noise_elements(soup, platform)
            
            structured_data = {
                'prices': [],
                'dates': [],
                'locations': [],
                'durations': [],
                'names': [],
                'numbers': [],
                'general': []
            }
            
            # Extract prices
            price_patterns = [
                r'\$[\d,]+(?:\.\d{2})?',
                r'€[\d,]+(?:\.\d{2})?',
                r'£[\d,]+(?:\.\d{2})?',
                r'[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|GBP|dollars?|euros?|pounds?)',
                r'(?:Total|Price|Cost|Fare):\s*[\d,]+(?:\.\d{2})?'
            ]
            
            # Extract dates
            date_patterns = [
                r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}\b',
                r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b'
            ]
            
            # Extract locations (airports, cities)
            location_patterns = [
                r'\b[A-Z]{3}\b',  # Airport codes
                r'\b(?:from|to|via)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*[A-Z]{2,3}\b'  # City, State/Country
            ]
            
            text = self._extract_booking_content(soup, platform)
            
            # Apply patterns to extract structured data
            for pattern in price_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                structured_data['prices'].extend(matches)
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                structured_data['dates'].extend(matches)
            
            for pattern in location_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches and isinstance(matches[0], tuple):
                    structured_data['locations'].extend([m[0] for m in matches])
                else:
                    structured_data['locations'].extend(matches)
            
            # Extract flight/booking numbers
            number_patterns = [
                r'\b[A-Z]{2}\d{3,4}\b',  # Flight numbers
                r'\b(?:Flight|Booking|Confirmation)[\s#:]*([A-Z0-9]+)\b'
            ]
            
            for pattern in number_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                structured_data['numbers'].extend(matches)
            
            # Store general clean text
            structured_data['general'] = [self._clean_text(text)]
            
            return structured_data
            
        except Exception as e:
            self.logger.error(f"Error extracting structured data: {str(e)}")
            raise