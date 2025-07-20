"""
Unit tests for TextExtractor service.
Tests text extraction from various travel booking site HTML structures.
"""

import pytest
from app.services.text_extractor import TextExtractor

import httpx


class TestTextExtractor:
    """Test cases for TextExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = TextExtractor()
    
    def test_extract_text_basic_html(self):
        """Test basic text extraction from simple HTML."""
        html = """
        <html>
            <body>
                <div class="booking">
                    <h1>Flight Details</h1>
                    <p>From: JFK to CDG</p>
                    <p>Price: $599.99</p>
                    <p>Duration: 7h 30m</p>
                </div>
            </body>
        </html>
        """
        
        result = self.extractor.extract_text(html)
        
        assert "Flight Details" in result
        assert "JFK to CDG" in result
        assert "$599.99" in result
        assert "7h 30m" in result
    
    def test_remove_navigation_elements(self):
        """Test removal of navigation and irrelevant content."""
        html = """
        <html>
            <body>
                <nav class="navigation">
                    <a href="/home">Home</a>
                    <a href="/about">About</a>
                </nav>
                <div class="booking">
                    <p>Flight from NYC to Paris</p>
                    <p>Price: $750</p>
                </div>
                <footer>
                    <p>Copyright 2024</p>
                </footer>
            </body>
        </html>
        """
        
        result = self.extractor.extract_text(html)
        
        assert "Flight from NYC to Paris" in result
        assert "$750" in result
        assert "Home" not in result
        assert "About" not in result
        assert "Copyright 2024" not in result
    
    def test_remove_ads_and_banners(self):
        """Test removal of advertisements and banner content."""
        html = """
        <html>
            <body>
                <div class="advertisement">
                    <p>Buy our premium service!</p>
                </div>
                <div class="booking-details">
                    <p>Hotel: Grand Plaza</p>
                    <p>Check-in: March 15, 2024</p>
                    <p>Rate: $200/night</p>
                </div>
                <div class="banner ad">
                    <p>Special offer!</p>
                </div>
            </body>
        </html>
        """
        
        result = self.extractor.extract_text(html)
        
        assert "Hotel: Grand Plaza" in result
        assert "March 15, 2024" in result
        assert "$200/night" in result
        assert "Buy our premium service!" not in result
        assert "Special offer!" not in result
    
    def test_google_flights_html(self):
        """Test extraction from Google Flights-like HTML structure."""
        html = """
        <html>
            <body>
                <div class="gws-flights__booking-card">
                    <div class="gws-flights__itinerary">
                        <span>JFK → CDG</span>
                        <span>Air France AF123</span>
                        <span>7h 30m</span>
                    </div>
                    <div class="gws-flights__price">
                        <span>$599</span>
                        <span>per person</span>
                    </div>
                </div>
                <div class="gws-flights__ads">
                    <p>Advertisement content</p>
                </div>
            </body>
        </html>
        """
        
        result = self.extractor.extract_text(html, "https://flights.google.com/search")
        
        assert "JFK → CDG" in result
        assert "Air France AF123" in result
        assert "7h 30m" in result
        assert "$599" in result
        assert "per person" in result
        assert "Advertisement content" not in result
    
    def test_airbnb_html(self):
        """Test extraction from Airbnb-like HTML structure."""
        html = """
        <html>
            <body>
                <div data-testid="listing-details">
                    <h1>Cozy Apartment in Paris</h1>
                    <p>Entire apartment • 2 guests</p>
                    <p>Montmartre, Paris, France</p>
                </div>
                <div data-testid="price-breakdown">
                    <span>$120 per night</span>
                    <span>5 nights</span>
                    <span>Total: $600</span>
                </div>
                <div class="reviews-section">
                    <p>User reviews...</p>
                </div>
            </body>
        </html>
        """
        
        result = self.extractor.extract_text(html, "https://www.airbnb.com/rooms/123")
        
        assert "Cozy Apartment in Paris" in result
        assert "2 guests" in result
        assert "Montmartre, Paris, France" in result
        assert "$120 per night" in result
        assert "5 nights" in result
        assert "Total: $600" in result
        assert "User reviews..." not in result
    
    def test_booking_com_html(self):
        """Test extraction from Booking.com-like HTML structure."""
        html = """
        <html>
            <body>
                <div class="hp__hotel-title">
                    <h1>Hotel Magnificent</h1>
                </div>
                <div class="bui-price-display">
                    <span>€150</span>
                    <span>per night</span>
                </div>
                <div class="c-accommodation-header">
                    <p>London, United Kingdom</p>
                    <p>Check-in: 20 Mar 2024</p>
                    <p>Check-out: 25 Mar 2024</p>
                </div>
                <div class="bui-header">
                    <nav>Navigation menu</nav>
                </div>
            </body>
        </html>
        """
        
        result = self.extractor.extract_text(html, "https://www.booking.com/hotel/gb/magnificent.html")
        
        assert "Hotel Magnificent" in result
        assert "€150" in result
        assert "per night" in result
        assert "London, United Kingdom" in result
        assert "Check-in: 20 Mar 2024" in result
        assert "Check-out: 25 Mar 2024" in result
        assert "Navigation menu" not in result
    
    def test_clean_text_normalization(self):
        """Test text cleaning and normalization."""
        html = """
        <html>
            <body>
                <div class="booking">
                    <p>Flight   Details</p>
                    <p>Price:    $500.00   </p>
                    <p>Duration:&nbsp;&nbsp;6h&nbsp;45m</p>
                    <p>Airline: &lt;Air France&gt;</p>
                </div>
            </body>
        </html>
        """
        
        result = self.extractor.extract_text(html)
        
        # Check whitespace normalization
        assert "Flight Details" in result
        assert "Price: $500.00" in result
        assert "Duration: 6h 45m" in result
        assert "Airline: <Air France>" in result
        
        # Ensure no excessive whitespace
        assert "   " not in result
        assert "&nbsp;" not in result
        assert "&lt;" not in result
        assert "&gt;" not in result
    
    def test_extract_structured_data(self):
        """Test structured data extraction with categorization."""
        html = """
        <html>
            <body>
                <div class="booking">
                    <p>Flight AF123 from JFK to CDG</p>
                    <p>Date: March 15, 2024</p>
                    <p>Price: $599.99</p>
                    <p>Duration: 7h 30m</p>
                    <p>Confirmation: ABC123XYZ</p>
                </div>
            </body>
        </html>
        """
        
        result = self.extractor.extract_structured_data(html)
        
        assert isinstance(result, dict)
        assert "prices" in result
        assert "dates" in result
        assert "locations" in result
        assert "numbers" in result
        assert "general" in result
        
        # Check extracted prices
        assert any("$599.99" in price for price in result["prices"])
        
        # Check extracted dates
        assert any("March 15, 2024" in date for date in result["dates"])
        
        # Check extracted locations (airport codes)
        assert "JFK" in result["locations"] or "CDG" in result["locations"]
        
        # Check extracted numbers (flight numbers)
        assert any("AF123" in num for num in result["numbers"])
    
    def test_empty_html_handling(self):
        """Test handling of empty or invalid HTML."""
        # Empty HTML
        result = self.extractor.extract_text("")
        assert result == ""
        
        # HTML with no content
        html = "<html><body></body></html>"
        result = self.extractor.extract_text(html)
        assert result == ""
        
        # HTML with only noise
        html = """
        <html>
            <body>
                <nav>Navigation</nav>
                <footer>Footer</footer>
                <script>console.log('test');</script>
            </body>
        </html>
        """
        result = self.extractor.extract_text(html)
        assert result == "" or result.strip() == ""
    
    def test_platform_detection(self):
        """Test platform detection from URLs."""
        # Test Google Flights
        platform = self.extractor._get_platform("https://flights.google.com/search")
        assert platform == "google.com"
        
        # Test Airbnb
        platform = self.extractor._get_platform("https://www.airbnb.com/rooms/123")
        assert platform == "airbnb.com"
        
        # Test Booking.com
        platform = self.extractor._get_platform("https://www.booking.com/hotel/gb/test.html")
        assert platform == "booking.com"
        
        # Test Hotels.com
        platform = self.extractor._get_platform("https://www.hotels.com/hotel/details.html")
        assert platform == "hotels.com"
        
        # Test unknown platform
        platform = self.extractor._get_platform("https://unknown-site.com/booking")
        assert platform is None
    
    def test_complex_travel_booking_html(self):
        """Test extraction from complex, realistic travel booking HTML."""
        html = """
        <html>
            <head>
                <title>Flight Booking - Travel Site</title>
                <script>analytics.track('page_view');</script>
            </head>
            <body>
                <header class="site-header">
                    <nav>
                        <a href="/">Home</a>
                        <a href="/flights">Flights</a>
                        <a href="/hotels">Hotels</a>
                    </nav>
                </header>
                
                <main class="booking-container">
                    <div class="flight-summary">
                        <h2>Your Flight Details</h2>
                        <div class="route-info">
                            <span class="departure">New York (JFK)</span>
                            <span class="arrow">→</span>
                            <span class="arrival">Paris (CDG)</span>
                        </div>
                        <div class="flight-info">
                            <p>Flight: Air France AF123</p>
                            <p>Date: March 15, 2024</p>
                            <p>Departure: 10:30 AM</p>
                            <p>Arrival: 11:00 PM (+1 day)</p>
                            <p>Duration: 7 hours 30 minutes</p>
                        </div>
                        <div class="pricing">
                            <p class="base-price">Base fare: $450.00</p>
                            <p class="taxes">Taxes & fees: $149.99</p>
                            <p class="total-price">Total: $599.99</p>
                            <p class="per-person">Per person</p>
                        </div>
                    </div>
                    
                    <aside class="advertisements">
                        <div class="ad-banner">
                            <h3>Special Hotel Deals!</h3>
                            <p>Save up to 50% on your next stay</p>
                        </div>
                    </aside>
                </main>
                
                <footer class="site-footer">
                    <p>&copy; 2024 Travel Site. All rights reserved.</p>
                    <div class="social-links">
                        <a href="/facebook">Facebook</a>
                        <a href="/twitter">Twitter</a>
                    </div>
                </footer>
            </body>
        </html>
        """
        
        result = self.extractor.extract_text(html)
        
        # Should contain booking information
        assert "Your Flight Details" in result
        assert "New York (JFK)" in result
        assert "Paris (CDG)" in result
        assert "Air France AF123" in result
        assert "March 15, 2024" in result
        assert "7 hours 30 minutes" in result
        assert "$599.99" in result
        
        # Should not contain navigation, ads, or footer
        assert "Home" not in result or result.count("Home") == 0
        assert "Special Hotel Deals!" not in result
        assert "All rights reserved" not in result
        assert "Facebook" not in result
        assert "Twitter" not in result
    
    def test_malformed_html_handling(self):
        """Test handling of malformed HTML."""
        malformed_html = """
        <html>
            <body>
                <div class="booking">
                    <p>Flight Details
                    <p>Price: $500
                    <span>Duration: 6h</span>
                </div>
            </body>
        """
        
        # Should not raise an exception
        result = self.extractor.extract_text(malformed_html)
        
        assert "Flight Details" in result
        assert "$500" in result
        assert "6h" in result


def test_extract_text_from_google_flights_url():
    """
    Fetches the Google Flights page and prints the text extracted by TextExtractor.
    This demonstrates what the parser sees for a JavaScript-heavy site.
    """
    from app.services.text_extractor import TextExtractor
    url = "https://www.google.com/travel/flights/s/2Bs5Vn7d3GXGoPg87"
    response = httpx.get(url, timeout=30)
    html = response.text
    extractor = TextExtractor()
    extracted_text = extractor.extract_text(html)
    print("\n--- Extracted Text from Google Flights Page ---\n")
    print(extracted_text)
    print("\n--- End of Extracted Text ---\n")
    # Optionally, assert that the extracted text is not empty (should be mostly empty for JS sites)
    assert isinstance(extracted_text, str)


def test_fetch_raw_html_from_google_flights_url():
    """
    Fetches the Google Flights page and prints the RAW HTML (no noise reduction).
    This shows exactly what the parser receives before any processing.
    """
    import httpx
    url = "https://www.google.com/travel/flights/s/2Bs5Vn7d3GXGoPg87"
    response = httpx.get(url, timeout=30)
    html = response.text
    print("\n--- RAW HTML from Google Flights Page ---\n")
    print(html)
    print("\n--- End of RAW HTML ---\n")
    assert isinstance(html, str)