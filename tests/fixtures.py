"""
Test fixtures with sample booking URLs and expected structured responses.
Provides realistic test data for comprehensive testing scenarios.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any


class BookingURLFixtures:
    """Sample booking URLs for different travel platforms."""
    
    # Flight booking URLs
    FLIGHT_URLS = {
        "google_flights": [
            "https://flights.google.com/flights?hl=en&curr=USD&tfs=CBwQAhoeEgoyMDI0LTA2LTE1agcIARIDSkZLcgcIARIDTEFYGh4SCjIwMjQtMDYtMjJqBwgBEgNMQVhyBwgBEgNKRktwAYIBCwj___________8BQAFIAZgBAQ",
            "https://flights.google.com/flights?hl=en&curr=USD&tfs=CBwQAhoeEgoyMDI0LTA3LTEwagcIARIDTllDcgcIARIDQ0RHGh4SCjIwMjQtMDctMTdqBwgBEgNDREdyBwgBEgNOWUNwAYIBCwj___________8BQAFIAZgBAQ",
            "https://flights.google.com/flights?hl=en&curr=USD&tfs=CBwQAhoeEgoyMDI0LTA4LTA1agcIARIDU0ZPcgcIARIDTUlBGh4SCjIwMjQtMDgtMTJqBwgBEgNNSUFyBwgBEgNTRk9wAYIBCwj___________8BQAFIAZgBAQ"
        ],
        "expedia": [
            "https://www.expedia.com/Flights-Search?trip=oneway&leg1=from:New%20York,to:Los%20Angeles,departure:06/15/2024TANYT&passengers=adults:1,children:0,seniors:0,infantinlap:Y&options=cabinclass:economy",
            "https://www.expedia.com/Flights-Search?trip=roundtrip&leg1=from:Chicago,to:Miami,departure:07/10/2024TANYT&leg2=from:Miami,to:Chicago,departure:07/17/2024TANYT&passengers=adults:2,children:0,seniors:0,infantinlap:Y&options=cabinclass:economy"
        ],
        "kayak": [
            "https://www.kayak.com/flights/NYC-LAX/2024-06-15/2024-06-22?sort=bestflight_a&fs=stops=0",
            "https://www.kayak.com/flights/CHI-MIA/2024-07-10/2024-07-17?sort=price_a&fs=stops=~1"
        ],
        "airline_direct": [
            "https://www.united.com/ual/en/us/flight-search/book-a-flight/results/rev?f=JFK&t=LAX&d=2024-06-15&tt=1&at=1&sc=7&px=1&taxng=1&newHP=True&clm=7",
            "https://www.delta.com/flight-search/book-a-flight?tripType=RT&fromAirportName=New+York+%28JFK%29&toAirportName=Los+Angeles+%28LAX%29&departureDate=06%2F15%2F2024&returnDate=06%2F22%2F2024&paxCount=1",
            "https://www.american.com/booking/flights/search?locale=en_US&from=JFK&to=LAX&depart=2024-06-15&return=2024-06-22&adult=1&child=0&infant=0&cabin=economy"
        ]
    }
    
    # Lodging booking URLs
    LODGING_URLS = {
        "airbnb": [
            "https://www.airbnb.com/rooms/12345678?adults=2&children=0&infants=0&check_in=2024-06-15&check_out=2024-06-18&source_impression_id=p3_1234567890_abcdefghijklmnop",
            "https://www.airbnb.com/rooms/87654321?adults=4&children=2&infants=0&check_in=2024-07-10&check_out=2024-07-17&source_impression_id=p3_0987654321_zyxwvutsrqponmlk",
            "https://www.airbnb.com/rooms/11223344?adults=1&children=0&infants=0&check_in=2024-08-05&check_out=2024-08-12&source_impression_id=p3_1122334455_mnbvcxzasdfghjkl"
        ],
        "booking_com": [
            "https://www.booking.com/hotel/us/luxury-manhattan-suite.html?aid=304142&label=gen173nr-1FCAEoggI46AdIM1gEaGyIAQGYAQm4AQfIAQzYAQHoAQH4AQuIAgGoAgO4AqGH2qwGwAIB0gIkNzE4YzQyNzAtMzE4Zi00YzE4LWI4YzMtMjE4YzQyNzAzMThmNgID4AIB&checkin=2024-06-15&checkout=2024-06-18&group_adults=2&group_children=0&no_rooms=1",
            "https://www.booking.com/hotel/fr/paris-luxury-hotel.html?aid=304142&label=gen173nr-1FCAEoggI46AdIM1gEaGyIAQGYAQm4AQfIAQzYAQHoAQH4AQuIAgGoAgO4AqGH2qwGwAIB0gIkNzE4YzQyNzAtMzE4Zi00YzE4LWI4YzMtMjE4YzQyNzAzMThmNgID4AIB&checkin=2024-07-10&checkout=2024-07-17&group_adults=2&group_children=0&no_rooms=1"
        ],
        "hotels_com": [
            "https://www.hotels.com/ho123456/2024-06-15/2024-06-18/2-adults?pos=HCOM_US&locale=en_US",
            "https://www.hotels.com/ho789012/2024-07-10/2024-07-17/4-adults-2-children?pos=HCOM_US&locale=en_US"
        ],
        "vrbo": [
            "https://www.vrbo.com/1234567?arrival=2024-06-15&departure=2024-06-18&adults=4&children=2",
            "https://www.vrbo.com/7654321?arrival=2024-08-05&departure=2024-08-12&adults=2&children=0"
        ]
    }


class ExpectedResponseFixtures:
    """Expected structured responses for test scenarios."""
    
    # Expected flight data responses
    FLIGHT_RESPONSES = {
        "jfk_to_lax_direct": {
            "origin_airport": "JFK",
            "destination_airport": "LAX",
            "duration": 360,  # 6 hours
            "total_cost": 299.99,
            "total_cost_per_person": 299.99,
            "segment": 1,
            "flight_number": "AA123"
        },
        "nyc_to_cdg_with_stop": {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": 480,  # 8 hours
            "total_cost": 1200.50,
            "total_cost_per_person": 600.25,
            "segment": 2,
            "flight_number": "AF456"
        },
        "sfo_to_mia_multi_segment": {
            "origin_airport": "SFO",
            "destination_airport": "MIA",
            "duration": 540,  # 9 hours
            "total_cost": 450.75,
            "total_cost_per_person": 225.38,
            "segment": 3,
            "flight_number": "UA789"
        },
        "budget_flight": {
            "origin_airport": "BWI",
            "destination_airport": "FLL",
            "duration": 150,  # 2.5 hours
            "total_cost": 89.99,
            "total_cost_per_person": 89.99,
            "segment": 1,
            "flight_number": "B6101"
        },
        "international_premium": {
            "origin_airport": "LAX",
            "destination_airport": "NRT",
            "duration": 660,  # 11 hours
            "total_cost": 2500.00,
            "total_cost_per_person": 2500.00,
            "segment": 1,
            "flight_number": "NH175"
        }
    }
    
    # Expected lodging data responses
    LODGING_RESPONSES = {
        "manhattan_luxury_hotel": {
            "name": "Luxury Manhattan Suite",
            "location": "New York, NY, USA",
            "number_of_guests": 2,
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 6, 18, 11, 0, 0, tzinfo=timezone.utc)
        },
        "paris_boutique_hotel": {
            "name": "Paris Boutique Hotel",
            "location": "Paris, France",
            "number_of_guests": 2,
            "total_cost": 840.00,
            "total_cost_per_person": 420,
            "number_of_nights": 7,
            "check_in": datetime(2024, 7, 10, 14, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 7, 17, 12, 0, 0, tzinfo=timezone.utc)
        },
        "airbnb_family_home": {
            "name": "Spacious Family Home with Pool",
            "location": "Orlando, FL, USA",
            "number_of_guests": 6,
            "total_cost": 1200.00,
            "total_cost_per_person": 200,
            "number_of_nights": 7,
            "check_in": datetime(2024, 8, 5, 16, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 8, 12, 10, 0, 0, tzinfo=timezone.utc)
        },
        "budget_motel": {
            "name": "Budget Inn & Suites",
            "location": "Las Vegas, NV, USA",
            "number_of_guests": 2,
            "total_cost": 120.00,
            "total_cost_per_person": 60,
            "number_of_nights": 2,
            "check_in": datetime(2024, 9, 1, 15, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 9, 3, 11, 0, 0, tzinfo=timezone.utc)
        },
        "luxury_resort": {
            "name": "Tropical Paradise Resort & Spa",
            "location": "Maui, HI, USA",
            "number_of_guests": 2,
            "total_cost": 3500.00,
            "total_cost_per_person": 1750,
            "number_of_nights": 5,
            "check_in": datetime(2024, 12, 20, 15, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 12, 25, 12, 0, 0, tzinfo=timezone.utc)
        }
    }


class ErrorScenarioFixtures:
    """Test fixtures for error scenarios and edge cases."""
    
    # Invalid URLs for testing validation
    INVALID_URLS = [
        "not-a-url",
        "http://",
        "https://",
        "ftp://invalid-protocol.com",
        "javascript:alert('xss')",
        "",
        None,
        "https://example.com/path with spaces",
        "https://toolongdomainname" + "a" * 300 + ".com"
    ]
    
    # URLs that should return 404 or be unreachable
    UNREACHABLE_URLS = [
        "https://flights.google.com/nonexistent-page-404",
        "https://www.airbnb.com/rooms/999999999999",
        "https://www.booking.com/hotel/nonexistent/fake-hotel.html",
        "https://httpstat.us/404",
        "https://httpstat.us/500",
        "https://httpstat.us/503"
    ]
    
    # URLs for unsupported platforms
    UNSUPPORTED_PLATFORM_URLS = [
        "https://www.facebook.com/travel",
        "https://www.instagram.com/travel",
        "https://www.twitter.com/travel",
        "https://www.reddit.com/r/travel",
        "https://www.youtube.com/watch?v=travel",
        "https://unsupported-travel-site.com/booking"
    ]
    
    # Sample HTML content that should fail parsing
    UNPARSEABLE_HTML_CONTENT = [
        "<html><body>No travel data here</body></html>",
        "<html><head><title>Error Page</title></head><body><h1>404 Not Found</h1></body></html>",
        "<!DOCTYPE html><html><body><p>This page contains no booking information.</p></body></html>",
        "<html><body><div>Random content without any travel data</div></body></html>",
        ""  # Empty content
    ]
    
    # Malformed JSON responses from LLM
    MALFORMED_LLM_RESPONSES = [
        "This is not JSON at all",
        '{"incomplete": json',
        '{"valid_json": "but_missing_required_fields"}',
        '{"origin_airport": "JFK", "destination_airport": null}',
        '{"duration": "not_a_number", "total_cost": "also_not_a_number"}',
        '[]',  # Array instead of object
        'null',
        ''
    ]


class MockHTMLFixtures:
    """Mock HTML content for different travel booking sites."""
    
    GOOGLE_FLIGHTS_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Google Flights</title></head>
    <body>
        <div class="flight-info">
            <span class="origin">JFK</span>
            <span class="destination">LAX</span>
            <span class="duration">6h 0m</span>
            <span class="price">$299</span>
            <span class="airline">American Airlines</span>
            <span class="flight-number">AA123</span>
        </div>
    </body>
    </html>
    """
    
    AIRBNB_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Luxury Manhattan Suite - Airbnb</title></head>
    <body>
        <div class="listing-info">
            <h1>Luxury Manhattan Suite</h1>
            <div class="location">New York, NY</div>
            <div class="guests">2 guests</div>
            <div class="price">$150 per night</div>
            <div class="dates">
                <span class="checkin">Jun 15, 2024</span>
                <span class="checkout">Jun 18, 2024</span>
            </div>
            <div class="nights">3 nights</div>
            <div class="total">$450 total</div>
        </div>
    </body>
    </html>
    """
    
    BOOKING_COM_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Paris Boutique Hotel - Booking.com</title></head>
    <body>
        <div class="hotel-info">
            <h1>Paris Boutique Hotel</h1>
            <div class="location">Paris, France</div>
            <div class="room-info">
                <span class="guests">2 adults</span>
                <span class="nights">7 nights</span>
            </div>
            <div class="price-info">
                <span class="total-price">€840</span>
                <span class="per-night">€120 per night</span>
            </div>
            <div class="dates">
                <span class="checkin">July 10, 2024</span>
                <span class="checkout">July 17, 2024</span>
            </div>
        </div>
    </body>
    </html>
    """
    
    HOTELS_COM_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Budget Inn & Suites - Hotels.com</title></head>
    <body>
        <div class="hotel-details">
            <h1>Budget Inn & Suites</h1>
            <div class="address">Las Vegas, NV</div>
            <div class="booking-details">
                <div class="guests">2 guests</div>
                <div class="stay-duration">2 nights</div>
                <div class="check-in">Sep 1, 2024</div>
                <div class="check-out">Sep 3, 2024</div>
                <div class="total-cost">$120.00</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    EMPTY_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Empty Page</title></head>
    <body></body>
    </html>
    """
    
    ERROR_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Error</title></head>
    <body>
        <h1>404 - Page Not Found</h1>
        <p>The requested page could not be found.</p>
    </body>
    </html>
    """


class TestDataGenerator:
    """Utility class for generating test data combinations."""
    
    @staticmethod
    def get_all_flight_urls() -> List[str]:
        """Get all flight booking URLs for testing."""
        all_urls = []
        for platform_urls in BookingURLFixtures.FLIGHT_URLS.values():
            all_urls.extend(platform_urls)
        return all_urls
    
    @staticmethod
    def get_all_lodging_urls() -> List[str]:
        """Get all lodging booking URLs for testing."""
        all_urls = []
        for platform_urls in BookingURLFixtures.LODGING_URLS.values():
            all_urls.extend(platform_urls)
        return all_urls
    
    @staticmethod
    def get_url_response_pairs() -> List[tuple]:
        """Get URL and expected response pairs for testing."""
        pairs = []
        
        # Flight URL/response pairs
        flight_urls = TestDataGenerator.get_all_flight_urls()
        flight_responses = list(ExpectedResponseFixtures.FLIGHT_RESPONSES.values())
        
        for i, url in enumerate(flight_urls):
            response = flight_responses[i % len(flight_responses)]
            pairs.append(("flight", url, response))
        
        # Lodging URL/response pairs
        lodging_urls = TestDataGenerator.get_all_lodging_urls()
        lodging_responses = list(ExpectedResponseFixtures.LODGING_RESPONSES.values())
        
        for i, url in enumerate(lodging_urls):
            response = lodging_responses[i % len(lodging_responses)]
            pairs.append(("lodging", url, response))
        
        return pairs
    
    @staticmethod
    def get_error_scenarios() -> List[Dict[str, Any]]:
        """Get error scenarios for testing."""
        scenarios = []
        
        # Invalid URL scenarios
        for url in ErrorScenarioFixtures.INVALID_URLS:
            scenarios.append({
                "type": "invalid_url",
                "url": url,
                "expected_status": 422,
                "expected_error": "VALIDATION_ERROR"
            })
        
        # Unreachable URL scenarios
        for url in ErrorScenarioFixtures.UNREACHABLE_URLS:
            scenarios.append({
                "type": "unreachable_url",
                "url": url,
                "expected_status": 500,
                "expected_error": "URL_UNREACHABLE"
            })
        
        # Unsupported platform scenarios
        for url in ErrorScenarioFixtures.UNSUPPORTED_PLATFORM_URLS:
            scenarios.append({
                "type": "unsupported_platform",
                "url": url,
                "expected_status": 400,
                "expected_error": "UNSUPPORTED_PLATFORM"
            })
        
        return scenarios
    
    @staticmethod
    def get_performance_test_urls(count: int = 10) -> List[str]:
        """Generate URLs for performance testing."""
        base_urls = TestDataGenerator.get_all_flight_urls() + TestDataGenerator.get_all_lodging_urls()
        
        # Cycle through base URLs to generate the requested count
        performance_urls = []
        for i in range(count):
            base_url = base_urls[i % len(base_urls)]
            # Add unique parameter to avoid caching
            separator = "&" if "?" in base_url else "?"
            performance_url = f"{base_url}{separator}perf_test={i}"
            performance_urls.append(performance_url)
        
        return performance_urls