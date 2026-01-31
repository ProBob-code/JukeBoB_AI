"""
WTPT (Where's the Party Tonight) - Event Aggregator
Scrapes music events from BookMyShow and District
Enhanced version with actual images, ticket availability, and accurate data
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import random
import hashlib
import json
import re

# Cache for events
event_cache = {}
CACHE_DURATION = 1800  # 30 minutes

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Event categories with strict matching keywords
CATEGORIES = {
    "dj_night": ["dj", "edm", "electronica", "house", "techno", "trance", "club night", "sundowner", "night club", "rave", "electronic", "deep house", "progressive"],
    "karaoke": ["karaoke", "sing along", "open mic singing", "karaoke night"],
    "live_show": ["live music", "live band", "live performance", "unplugged", "acoustic", "gig", "jam session"],
    "concert": ["concert", "festival", "tour", "arena show", "stadium", "mega event", "sunburn", "nh7", "bacardi"],
}

# Supported cities with platform-specific identifiers
CITIES = {
    "mumbai": {"bms": "mumbai", "district": "mumbai", "spotify": "1275339-Mumbai-IN"},
    "delhi": {"bms": "ncr", "district": "delhi", "spotify": "1273294-Delhi-IN"},
    "bangalore": {"bms": "bengaluru", "district": "bangalore", "spotify": "1277333-Bangalore-IN"},
    "chennai": {"bms": "chennai", "district": "chennai", "spotify": "1264527-Chennai-IN"},
    "hyderabad": {"bms": "hyderabad", "district": "hyderabad", "spotify": "1269843-Hyderabad-IN"},
    "pune": {"bms": "pune", "district": "pune", "spotify": "1259229-Pune-IN"},
    "kolkata": {"bms": "kolkata", "district": "kolkata", "spotify": "1275004-Kolkata-IN"},
    "goa": {"bms": "goa", "district": "goa", "spotify": "1271157-Goa-IN"},
}

# Bookings storage
bookings = {}

# JukeBob Xclusive events (future scope)
jukebob_exclusive = []


class WTPTScraper:
    """Web scraper for music events with enhanced data extraction"""
    
    def __init__(self):
        self.session = requests.Session()
        # Disable SSL verification to avoid corporate firewall issues
        self.session.verify = False
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.rate_limit_delay = 2  # seconds between requests
    
    def _get_headers(self) -> dict:
        """Get request headers with random user agent"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    def _rate_limit(self):
        """Apply rate limiting"""
        time.sleep(self.rate_limit_delay)
    
    def _categorize_event(self, title: str, description: str = "") -> str:
        """Categorize event based on title and description keywords - STRICT matching"""
        text = (title + " " + description).lower()
        
        # Check each category's keywords
        for category, keywords in CATEGORIES.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        
        # Default to live_show for music events
        return "live_show"
    
    def _get_cache_key(self, city: str, source: str) -> str:
        """Generate cache key"""
        return f"{city}_{source}_{datetime.now().strftime('%Y%m%d%H')}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if cache_key not in event_cache:
            return False
        cached_time = event_cache[cache_key].get("timestamp", 0)
        return (time.time() - cached_time) < CACHE_DURATION
    
    def _extract_availability(self, card, text: str) -> str:
        """Extract ticket availability status"""
        text_lower = text.lower()
        
        if "sold out" in text_lower or "housefull" in text_lower:
            return "Sold Out"
        elif "fast filling" in text_lower or "selling fast" in text_lower:
            return "Fast Filling"
        elif "few left" in text_lower or "limited" in text_lower:
            return "Few Left"
        elif "book now" in text_lower or "buy" in text_lower or "available" in text_lower:
            return "Available"
        
        return "Check Availability"
    
    def scrape_spotify_selenium(self, city: str = "mumbai") -> List[Dict]:
        """Scrape events from Spotify Concerts using Selenium for JavaScript rendering"""
        cache_key = self._get_cache_key(city, "spotify_selenium")
        
        if self._is_cache_valid(cache_key):
            return event_cache[cache_key]["events"]
        
        events = []
        city_config = CITIES.get(city.lower(), {})
        spotify_location = city_config.get("spotify", "1277333-Bangalore-IN")
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            
            # Setup headless Chrome
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
            
            # Use webdriver-manager to handle ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                url = f"https://open.spotify.com/concerts/location/{spotify_location}"
                driver.get(url)
                
                # Wait for page to load and events to render
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/concert/']"))
                )
                time.sleep(3)  # Extra time for images to load
                
                # Scroll down to load more events
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(2)
                
                # Extract events using JavaScript for reliable data extraction
                events_data = driver.execute_script("""
                    const events = [];
                    const concertLinks = document.querySelectorAll('a[href*="/concert/"]');
                    
                    concertLinks.forEach((link, index) => {
                        if (index >= 30) return; // Limit to 30 events
                        
                        const card = link.closest('div[class*="Card"]') || link.parentElement;
                        if (!card) return;
                        
                        // Get artist image - look for img tag or background-image style
                        let imageUrl = '';
                        const img = card.querySelector('img');
                        if (img && img.src && img.src.includes('scdn.co')) {
                            imageUrl = img.src;
                        } else {
                            // Check for background-image
                            const divWithBg = card.querySelector('div[style*="background-image"]');
                            if (divWithBg) {
                                const bgMatch = divWithBg.style.backgroundImage.match(/url\\(["']?([^"')]+)["']?\\)/);
                                if (bgMatch) imageUrl = bgMatch[1];
                            }
                        }
                        
                        // Get date from time element
                        const timeEl = card.querySelector('time');
                        const dateStr = timeEl ? timeEl.textContent.trim() : 'Upcoming';
                        const dateTimeAttr = timeEl ? timeEl.getAttribute('datetime') : '';
                        
                        // Get artist name (usually in heading)
                        const heading = card.querySelector('h3, h4, [class*="Title"]');
                        const artist = heading ? heading.textContent.trim() : '';
                        
                        // Get venue
                        const venueEl = card.querySelector('[data-testid="location-name"], span:last-child');
                        const venue = venueEl ? venueEl.textContent.trim() : '';
                        
                        if (artist && artist.length > 2) {
                            events.push({
                                href: link.href,
                                artist: artist,
                                date: dateStr,
                                datetime: dateTimeAttr,
                                venue: venue,
                                image: imageUrl
                            });
                        }
                    });
                    
                    return events;
                """)
                
                seen_artists = set()
                
                for event_data in events_data:
                    artist = event_data.get('artist', '')
                    if not artist or artist.lower() in seen_artists:
                        continue
                    seen_artists.add(artist.lower())
                    
                    venue = event_data.get('venue', '') or f"Various Venues, {city.title()}"
                    date_str = event_data.get('date', 'Upcoming')
                    image_url = event_data.get('image', '')
                    booking_url = event_data.get('href', '')
                    
                    # Use Spotify image or fallback to a concert image
                    if not image_url or 'scdn.co' not in image_url:
                        image_url = "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400"
                    
                    event = {
                        "id": f"spotify_{hashlib.md5(artist.encode()).hexdigest()[:8]}",
                        "title": artist,
                        "category": self._categorize_event(artist, venue),
                        "platform": "spotify",
                        "platform_name": "Spotify Concerts",
                        "booking_url": booking_url,
                        "venue": venue,
                        "city": city.title(),
                        "date": date_str,
                        "price": "See ticket options",
                        "image": image_url,
                        "availability": "Available",
                    }
                    events.append(event)
                    
            finally:
                driver.quit()
                
        except ImportError as e:
            print(f"Selenium not installed: {e}")
        except Exception as e:
            print(f"Selenium Spotify scraping error: {e}")
        
        event_cache[cache_key] = {"events": events, "timestamp": time.time()}
        return events
    
    def scrape_spotify_concerts(self, city: str = "mumbai") -> List[Dict]:
        """Scrape events from Spotify Concerts - try Selenium first, fallback to basic"""
        # Try Selenium-based scraping first for real data
        events = self.scrape_spotify_selenium(city)
        if events:
            return events
        
        # Fallback to basic scraping if Selenium fails
        cache_key = self._get_cache_key(city, "spotify")
        
        if self._is_cache_valid(cache_key):
            return event_cache[cache_key]["events"]
        
        events = []
        city_config = CITIES.get(city.lower(), {})
        spotify_location = city_config.get("spotify", "1259229-Pune-IN")
        
        try:
            url = f"https://open.spotify.com/concerts/location/{spotify_location}"
            self._rate_limit()
            response = self.session.get(url, headers=self._get_headers(), timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all concert links - Spotify uses anchor tags with concert URLs
                concert_links = soup.select('a[href*="/concert/"]')
                
                seen_titles = set()  # Avoid duplicates
                
                for link in concert_links[:30]:  # Limit to 30 events
                    try:
                        href = link.get('href', '')
                        if not href:
                            continue
                        
                        # Get the link text which contains event info
                        link_text = link.get_text(separator=' ', strip=True)
                        if not link_text or len(link_text) < 10:
                            continue
                        
                        # Parse the text - format is typically "Day, Mon DD, TimeArtist NameVenue, City"
                        # Example: "Wed, Dec 31, 7:00 PMProject 91The Royal Lake Banquets & Resort, Pune"
                        
                        # Extract date/time (starts with day abbreviation)
                        date_match = re.match(r'^([A-Za-z]{3}, [A-Za-z]{3} \d{1,2}(?:, \d{4})?,? ?\d{1,2}:\d{2} [AP]M)', link_text)
                        if date_match:
                            date_str = date_match.group(1)
                            remaining = link_text[len(date_str):].strip()
                        else:
                            date_str = "Upcoming"
                            remaining = link_text
                        
                        # The remaining text is Artist + Venue
                        venue = f"Various Venues, {city.title()}"
                        artist = remaining
                        
                        # Look for venue patterns
                        venue_patterns = [
                            r'(.+?)([\w\s]+(?:Hall|Theatre|Arena|Stadium|Grounds|Park|Cafe|Club|Lounge|Hotel|Lawn|Resort|Centre|Center|Garden|Palace|House|Bar|Pub|College|School|Institute|Auditorium|Complex|Ground)[^,]*,?\s*[\w\s]*$)',
                        ]
                        
                        for pattern in venue_patterns:
                            match = re.match(pattern, remaining, re.IGNORECASE)
                            if match:
                                artist = match.group(1).strip()
                                venue = match.group(2).strip()
                                break
                        
                        # Clean up artist name
                        artist = artist.strip(' ,')
                        if not artist or len(artist) < 2:
                            continue
                        
                        # Skip duplicates
                        if artist.lower() in seen_titles:
                            continue
                        seen_titles.add(artist.lower())
                        
                        # Build full concert URL
                        concert_url = f"https://open.spotify.com{href}" if href.startswith('/') else href
                        
                        event = {
                            "id": f"spotify_{hashlib.md5(artist.encode()).hexdigest()[:8]}",
                            "title": artist,
                            "category": self._categorize_event(artist, venue),
                            "platform": "spotify",
                            "platform_name": "Spotify Concerts",
                            "booking_url": concert_url,
                            "venue": venue if venue else f"Various Venues, {city.title()}",
                            "city": city.title(),
                            "date": date_str,
                            "price": "See ticket options",
                            "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
                            "availability": "Available",
                        }
                        events.append(event)
                        
                    except Exception as e:
                        continue
                        
        except Exception as e:
            print(f"Spotify Concerts scraping error: {e}")
        
        event_cache[cache_key] = {"events": events, "timestamp": time.time()}
        return events
    
    def scrape_bookmyshow(self, city: str = "mumbai") -> List[Dict]:
        """Scrape events from BookMyShow with full details"""
        cache_key = self._get_cache_key(city, "bookmyshow")
        
        if self._is_cache_valid(cache_key):
            return event_cache[cache_key]["events"]
        
        events = []
        city_code = CITIES.get(city, {}).get("bms", city)
        
        try:
            # Try music events page
            url = f"https://in.bookmyshow.com/explore/music-events-{city_code}"
            self._rate_limit()
            response = self.session.get(url, headers=self._get_headers(), timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all event cards - BookMyShow uses various class patterns
                event_cards = soup.select('[data-testid*="event"], [class*="EventCard"], .sc-7o7nez-0, [class*="card"]')
                
                for card in event_cards[:25]:
                    try:
                        # Get card HTML for analysis
                        card_text = card.get_text(separator=' ', strip=True)
                        
                        # Extract title
                        title_el = card.select_one('h3, h4, [class*="title"], [class*="name"], [data-testid*="title"]')
                        if not title_el:
                            continue
                        title = title_el.get_text(strip=True)
                        if len(title) < 5:
                            continue
                        
                        # Extract image - try multiple sources
                        img_url = ""
                        img_el = card.select_one('img[src], img[data-src], [style*="background-image"]')
                        if img_el:
                            img_url = img_el.get('src') or img_el.get('data-src', '')
                            if not img_url and 'style' in img_el.attrs:
                                style = img_el.get('style', '')
                                match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                                if match:
                                    img_url = match.group(1)
                        
                        # Ensure full URL for images
                        if img_url and not img_url.startswith('http'):
                            img_url = f"https://in.bookmyshow.com{img_url}"
                        
                        # Extract venue
                        venue_el = card.select_one('[class*="venue"], [class*="location"], [class*="place"], [data-testid*="venue"]')
                        venue = venue_el.get_text(strip=True) if venue_el else f"Various Venues, {city.title()}"
                        
                        # Extract date
                        date_el = card.select_one('[class*="date"], time, [class*="when"], [data-testid*="date"]')
                        date_str = date_el.get_text(strip=True) if date_el else "Upcoming"
                        
                        # Extract price
                        price_el = card.select_one('[class*="price"], [class*="cost"], [class*="amount"]')
                        price = price_el.get_text(strip=True) if price_el else "Check website"
                        if not price or price == "":
                            price = "Check website"
                        
                        # Extract link
                        link_el = card.select_one('a[href]')
                        link = ""
                        if link_el:
                            href = link_el.get('href', '')
                            if href.startswith('/'):
                                link = f"https://in.bookmyshow.com{href}"
                            elif href.startswith('http'):
                                link = href
                        if not link:
                            link = url
                        
                        # Ticket availability
                        availability = self._extract_availability(card, card_text)
                        
                        event = {
                            "id": f"bms_{hashlib.md5(title.encode()).hexdigest()[:8]}",
                            "title": title,
                            "category": self._categorize_event(title, card_text),
                            "platform": "bookmyshow",
                            "platform_name": "BookMyShow",
                            "booking_url": link,
                            "venue": venue,
                            "city": city.title(),
                            "date": date_str,
                            "price": price,
                            "image": img_url,
                            "availability": availability,
                        }
                        events.append(event)
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"BookMyShow scraping error: {e}")
        
        # Cache results
        event_cache[cache_key] = {"events": events, "timestamp": time.time()}
        return events
    

    
    def scrape_district(self, city: str = "mumbai") -> List[Dict]:
        """Scrape events from District (formerly Paytm Insider) with full details"""
        cache_key = self._get_cache_key(city, "district")
        
        if self._is_cache_valid(cache_key):
            return event_cache[cache_key]["events"]
        
        events = []
        city_code = CITIES.get(city, {}).get("district", city)
        
        try:
            # District uses the insider.in domain
            url = f"https://insider.in/{city_code}/music"
            self._rate_limit()
            response = self.session.get(url, headers=self._get_headers(), timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # District uses specific card classes
                event_cards = soup.select('[class*="EventCard"], [class*="event-card"], article, .card')
                
                for card in event_cards[:25]:
                    try:
                        card_text = card.get_text(separator=' ', strip=True)
                        
                        title_el = card.select_one('h2, h3, h4, [class*="title"], [class*="name"]')
                        if not title_el:
                            continue
                        title = title_el.get_text(strip=True)
                        if len(title) < 5:
                            continue
                        
                        # Extract image
                        img_url = ""
                        img_el = card.select_one('img[src], img[data-src]')
                        if img_el:
                            img_url = img_el.get('src') or img_el.get('data-src', '')
                        
                        # Also check for background images
                        if not img_url:
                            bg_el = card.select_one('[style*="background"]')
                            if bg_el:
                                style = bg_el.get('style', '')
                                match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                                if match:
                                    img_url = match.group(1)
                        
                        if img_url and not img_url.startswith('http'):
                            img_url = f"https://insider.in{img_url}"
                        
                        venue_el = card.select_one('[class*="venue"], [class*="location"]')
                        venue = venue_el.get_text(strip=True) if venue_el else f"Various Venues, {city.title()}"
                        
                        date_el = card.select_one('[class*="date"], time')
                        date_str = date_el.get_text(strip=True) if date_el else "Upcoming"
                        
                        price_el = card.select_one('[class*="price"]')
                        price = price_el.get_text(strip=True) if price_el else "Check website"
                        
                        link_el = card.select_one('a[href]')
                        link = link_el.get('href', url) if link_el else url
                        if not link.startswith('http'):
                            link = f"https://insider.in{link}"
                        
                        availability = self._extract_availability(card, card_text)
                        
                        event = {
                            "id": f"dis_{hashlib.md5(title.encode()).hexdigest()[:8]}",
                            "title": title,
                            "category": self._categorize_event(title, card_text),
                            "platform": "district",
                            "platform_name": "District",
                            "booking_url": link,
                            "venue": venue,
                            "city": city.title(),
                            "date": date_str,
                            "price": price,
                            "image": img_url,
                            "availability": availability,
                        }
                        events.append(event)
                    except Exception:
                        continue
        except Exception as e:
            print(f"District scraping error: {e}")
        
        event_cache[cache_key] = {"events": events, "timestamp": time.time()}
        return events
    
    def get_all_events(self, city: str = "mumbai", category: Optional[str] = None) -> List[Dict]:
        """Get all music events from all platforms with STRICT category filtering
        
        Priority order:
        1. Spotify Concerts (aggregates from all platforms globally)
        2. BookMyShow (India)
        3. District (India)
        4. JukeBob Xclusive (future)
        """
        all_events = []
        
        # Primary source: Spotify Concerts (aggregates all platforms)
        spotify_events = self.scrape_spotify_concerts(city)
        all_events.extend(spotify_events)
        
        # If Spotify didn't return many results, supplement with BookMyShow and District
        if len(spotify_events) < 5:
            all_events.extend(self.scrape_bookmyshow(city))
            all_events.extend(self.scrape_district(city))
        
        # Add JukeBob Xclusive events for the city
        for event in jukebob_exclusive:
            if event.get("city", "").lower() == city.lower():
                all_events.append(event)
        
        # Remove duplicates based on similar titles
        seen_titles = set()
        unique_events = []
        for event in all_events:
            title_key = event.get("title", "").lower().strip()[:30]  # First 30 chars for comparison
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_events.append(event)
        
        all_events = unique_events
        
        # STRICT category filtering
        if category and category != "all" and category != "":
            all_events = [e for e in all_events if e.get("category") == category]
        
        return all_events
    
    def get_mock_events(self, city: str = "mumbai", category: Optional[str] = None) -> List[Dict]:
        """Return mock events as fallback with proper images and availability"""
        
        # City-specific venues
        city_venues = {
            "mumbai": {
                "club": "Tryst, Lower Parel",
                "bar": "Blues Bar, Bandra",
                "liveVenue": "Hard Rock Cafe, Worli",
                "arena": "Mahalaxmi Racecourse",
                "lounge": "Kitty Su, The Lalit",
                "rooftop": "Soho House"
            },
            "delhi": {
                "club": "Kitty Su, The Lalit",
                "bar": "Piano Man Jazz Club, Safdarjung",
                "liveVenue": "Hard Rock Cafe, Saket",
                "arena": "JLN Stadium",
                "lounge": "Privee, Shangri-La",
                "rooftop": "Farzi Cafe, CP"
            },
            "bangalore": {
                "club": "Loft 38, Indiranagar",
                "bar": "The Humming Tree, Indiranagar",
                "liveVenue": "Hard Rock Cafe, MG Road",
                "arena": "Palace Grounds",
                "lounge": "Shiro, UB City",
                "rooftop": "Skyye, UB City"
            },
            "pune": {
                "club": "High Spirits, Koregaon Park",
                "bar": "Effingut Brewerkz, KP",
                "liveVenue": "Hard Rock Cafe, Camp",
                "arena": "FC Road",
                "lounge": "Mi-A-Mi, Phoenix",
                "rooftop": "Paasha, JW Marriott"
            },
            "goa": {
                "club": "Club Cubana, Arpora",
                "bar": "Cape Town Cafe, Candolim",
                "liveVenue": "LPK Waterfront, Nerul",
                "arena": "Vagator Beach",
                "lounge": "Tito's, Baga",
                "rooftop": "Antares, Vagator"
            },
            "hyderabad": {
                "club": "Prism Club, Jubilee Hills",
                "bar": "Heart Cup Coffee, Kondapur",
                "liveVenue": "Hard Rock Cafe, GVK One",
                "arena": "Hitex Ground",
                "lounge": "Kismet, Park Hyatt",
                "rooftop": "Aqua, Park Hyatt"
            },
            "chennai": {
                "club": "10 Downing Street, Nungambakkam",
                "bar": "The Flying Elephant, Park Hyatt",
                "liveVenue": "Dublin, Taramani",
                "arena": "YMCA Grounds",
                "lounge": "Leather Bar, Park Hyatt",
                "rooftop": "Bay 146, ECR"
            },
            "kolkata": {
                "club": "Nocturne, Park Street",
                "bar": "Someplace Else, Park Hotel",
                "liveVenue": "Hard Rock Cafe, Park Street",
                "arena": "Nicco Park",
                "lounge": "Tantra, Park Street",
                "rooftop": "Ozora, Salt Lake"
            }
        }
        
        venues = city_venues.get(city.lower(), city_venues["mumbai"])
        city_code = "ncr" if city.lower() == "delhi" else ("bengaluru" if city.lower() == "bangalore" else city.lower())
        
        # City-specific REAL upcoming events (updated from web search)
        city_events = {
            "pune": [
                {
                    "id": "real_pune_001",
                    "title": "Sonu Nigam - Satrangi Re India Tour",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/pune/music-events",
                    "venue": "Mahalakshmi Lawns, Kharadi",
                    "city": "Pune",
                    "date": "Jan 10, 2025 | 7:00 PM",
                    "price": "₹2,999 onwards",
                    "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
                    "availability": "Fast Filling",
                },
                {
                    "id": "real_pune_002",
                    "title": "Lucky Ali - Re:Sound Experience",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/pune/music-events",
                    "venue": "Mahalakshmi Lawns, Lohegaon",
                    "city": "Pune",
                    "date": "Jan 17, 2025 | 7:00 PM",
                    "price": "₹1,999 onwards",
                    "image": "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?w=400",
                    "availability": "Available",
                },
                {
                    "id": "real_pune_003",
                    "title": "Gulzar Live in Pune",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/pune/music-events",
                    "venue": "Pandit Farms, Pune",
                    "city": "Pune",
                    "date": "Jan 16, 2025 | 7:00 PM",
                    "price": "₹2,500 onwards",
                    "image": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400",
                    "availability": "Available",
                },
                {
                    "id": "real_pune_004",
                    "title": "Rahul Deshpande & Mahalakshmi Iyer Live",
                    "category": "concert", 
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/pune/music-events",
                    "venue": "MIT - WPU Campus, Pune",
                    "city": "Pune",
                    "date": "Jan 11, 2025 | 7:00 PM",
                    "price": "₹1,500 onwards",
                    "image": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400",
                    "availability": "Available",
                },
                {
                    "id": "real_pune_005",
                    "title": "Anuv Jain - Dastakhat India Tour",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/pune/music-events",
                    "venue": "Various Venues, Pune",
                    "city": "Pune",
                    "date": "Jan 23, 2025 | 7:00 PM",
                    "price": "₹1,999 onwards",
                    "image": "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400",
                    "availability": "Available",
                },
                {
                    "id": "real_pune_006",
                    "title": "NYE 2025 - New Year Carnival",
                    "category": "dj_night",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/pune/music-events?q=new+year",
                    "venue": "Asilo, Westin Pune",
                    "city": "Pune",
                    "date": "Dec 31, 2024 | 8:00 PM",
                    "price": "₹5,000 onwards",
                    "image": "https://images.unsplash.com/photo-1571266028243-d220c6a8b0e7?w=400",
                    "availability": "Few Left",
                },
                {
                    "id": "real_pune_007",
                    "title": "AP Dhillon - One Of One Tour",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/pune/music-events",
                    "venue": "Mayfield Yash Garden, Pune",
                    "city": "Pune",
                    "date": "Dec 14, 2025 | 7:00 PM",
                    "price": "₹3,999 onwards",
                    "image": "https://images.unsplash.com/photo-1574391884720-bbc3740c59d1?w=400",
                    "availability": "Available",
                },
                {
                    "id": "real_pune_008",
                    "title": "Sufiyana Kabir 2025",
                    "category": "live_show",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/pune/music-events",
                    "venue": "Elpro City Square, Pune",
                    "city": "Pune",
                    "date": "Jan 23, 2025 | 7:00 PM",
                    "price": "₹999 onwards",
                    "image": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=400",
                    "availability": "Available",
                },
            ],
            "mumbai": [
                {
                    "id": "real_mumbai_001",
                    "title": "Jubin Nautiyal Live",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/mumbai/music-events",
                    "venue": "DOME, SVP Stadium, Mumbai",
                    "city": "Mumbai",
                    "date": "Jan 11, 2025 | 7:00 PM",
                    "price": "₹1,999 onwards",
                    "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
                    "availability": "Fast Filling",
                },
                {
                    "id": "real_mumbai_002",
                    "title": "Lucky Ali Live at DOME",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/mumbai/music-events",
                    "venue": "DOME, SVP Stadium, Mumbai",
                    "city": "Mumbai",
                    "date": "Jan 11, 2025 | 7:00 PM",
                    "price": "₹2,999 onwards",
                    "image": "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?w=400",
                    "availability": "Available",
                },
                {
                    "id": "real_mumbai_003",
                    "title": "Anyasa NYE 2025",
                    "category": "dj_night",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/mumbai/music-events?q=anyasa",
                    "venue": "ICONIQA Hotel, Mumbai Airport",
                    "city": "Mumbai",
                    "date": "Dec 31, 2024 | 9:00 PM",
                    "price": "₹4,999 onwards",
                    "image": "https://images.unsplash.com/photo-1571266028243-d220c6a8b0e7?w=400",
                    "availability": "Few Left",
                },
                {
                    "id": "real_mumbai_004",
                    "title": "Kaushiki Chakraborty - Classical Evening",
                    "category": "live_show",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/mumbai/music-events",
                    "venue": "Tata Theatre, NCPA Mumbai",
                    "city": "Mumbai",
                    "date": "Jan 3, 2025 | 6:30 PM",
                    "price": "₹1,500 onwards",
                    "image": "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400",
                    "availability": "Available",
                },
                {
                    "id": "real_mumbai_005",
                    "title": "Marty Friedman Live",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/mumbai/music-events",
                    "venue": "Phoenix Palladium, Mumbai",
                    "city": "Mumbai",
                    "date": "Jan 16, 2025 | 6:00 PM",
                    "price": "₹2,500 onwards",
                    "image": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400",
                    "availability": "Available",
                },
                {
                    "id": "real_mumbai_006",
                    "title": "Sooryagayathri Live",
                    "category": "live_show",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": "https://in.bookmyshow.com/mumbai/music-events",
                    "venue": "The Royal Opera House, Mumbai",
                    "city": "Mumbai",
                    "date": "Jan 16, 2025 | 6:30 PM",
                    "price": "₹1,000 onwards",
                    "image": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=400",
                    "availability": "Available",
                },
            ],
        }
        
        # Use city-specific real events if available, otherwise use generic mock data
        if city.lower() in city_events:
            mock_data = city_events[city.lower()]
        else:
            # Fallback generic events for other cities
            mock_data = [
                {
                    "id": f"mock_001_{city}",
                    "title": "Weekend DJ Night Special",
                    "category": "dj_night",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": f"https://in.bookmyshow.com/explore/music-events-{city_code}?q=dj+night",
                    "venue": venues["club"],
                    "city": city.title(),
                    "date": "Every Saturday | 9:00 PM",
                    "price": "₹1,500 onwards",
                    "image": "https://images.unsplash.com/photo-1571266028243-d220c6a8b0e7?w=400",
                    "availability": "Available",
                },
                {
                    "id": f"mock_002_{city}",
                    "title": "Karaoke Nights - Sing Your Heart Out",
                    "category": "karaoke",
                    "platform": "district",
                    "platform_name": "District",
                    "booking_url": f"https://www.district.in/events/?city={city.lower()}&category=music",
                    "venue": venues["bar"],
                    "city": city.title(),
                    "date": "Every Tuesday | 8:00 PM",
                    "price": "₹500 cover",
                    "image": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=400",
                    "availability": "Available",
                },
                {
                    "id": f"mock_003_{city}",
                    "title": "Live Music Friday - Acoustic Evening",
                    "category": "live_show",
                    "platform": "district",
                    "platform_name": "District",
                    "booking_url": f"https://www.district.in/events/?city={city.lower()}&category=music",
                    "venue": venues["liveVenue"],
                    "city": city.title(),
                    "date": "Every Friday | 8:00 PM",
                    "price": "₹2,000 onwards",
                    "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
                    "availability": "Available",
                },
                {
                    "id": f"mock_004_{city}",
                    "title": "NYE 2025 Grand Celebration",
                    "category": "concert",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": f"https://in.bookmyshow.com/explore/music-events-{city_code}?q=new+year",
                    "venue": venues["arena"],
                    "city": city.title(),
                    "date": "Dec 31, 2024 | 8:00 PM",
                    "price": "₹5,000 onwards",
                    "image": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400",
                    "availability": "Few Left",
                },
                {
                    "id": f"mock_005_{city}",
                    "title": "Deep House Underground Sessions",
                    "category": "dj_night",
                    "platform": "district",
                    "platform_name": "District",
                    "booking_url": f"https://www.district.in/events/?city={city.lower()}&category=music",
                    "venue": venues["lounge"],
                    "city": city.title(),
                    "date": "Every Sunday | 10:00 PM",
                    "price": "₹2,500 onwards",
                    "image": "https://images.unsplash.com/photo-1574391884720-bbc3740c59d1?w=400",
                    "availability": "Available",
                },
                {
                    "id": f"mock_006_{city}",
                    "title": "Rooftop Sundowner Party",
                    "category": "dj_night",
                    "platform": "bookmyshow",
                    "platform_name": "BookMyShow",
                    "booking_url": f"https://in.bookmyshow.com/explore/music-events-{city_code}?q=sundowner",
                    "venue": venues["rooftop"],
                    "city": city.title(),
                    "date": "Every Weekend | 5:00 PM",
                    "price": "₹3,000 onwards",
                    "image": "https://images.unsplash.com/photo-1598387993441-a364f854c3e1?w=400",
                    "availability": "Available",
                },
            ]
        
        # STRICT category filtering for mock data
        if category and category != "all" and category != "":
            mock_data = [e for e in mock_data if e.get("category") == category]
        
        return mock_data


# Booking Management
def create_booking(booking_data: dict) -> dict:
    """Create a new booking record"""
    import uuid
    
    booking_id = f"JB_{uuid.uuid4().hex[:8].upper()}"
    booking = {
        "id": booking_id,
        "event_id": booking_data.get("event_id"),
        "event_title": booking_data.get("event_title"),
        "platform": booking_data.get("platform"),
        "platform_booking_id": booking_data.get("platform_booking_id"),
        "user_name": booking_data.get("user_name"),
        "user_email": booking_data.get("user_email"),
        "user_phone": booking_data.get("user_phone"),
        "tickets": booking_data.get("tickets", 1),
        "total_amount": booking_data.get("total_amount", 0),
        "booking_date": datetime.now().isoformat(),
        "event_date": booking_data.get("event_date"),
        "venue": booking_data.get("venue"),
        "status": "confirmed",
    }
    
    bookings[booking_id] = booking
    return booking


def get_bookings(user_email: Optional[str] = None) -> List[dict]:
    """Get all bookings or filter by user"""
    if user_email:
        return [b for b in bookings.values() if b.get("user_email") == user_email]
    return list(bookings.values())


def get_booking(booking_id: str) -> Optional[dict]:
    """Get a specific booking"""
    return bookings.get(booking_id)


def generate_invoice_html(booking_id: str) -> Optional[str]:
    """Generate HTML invoice for a booking"""
    booking = bookings.get(booking_id)
    if not booking:
        return None
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>JukeBoB Invoice - {booking_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; border-bottom: 2px solid #f5d547; padding-bottom: 20px; margin-bottom: 20px; }}
            .logo {{ font-size: 32px; font-weight: bold; color: #333; }}
            .logo span {{ color: #f5d547; }}
            .invoice-id {{ color: #666; font-size: 14px; }}
            .section {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 8px; }}
            .section h3 {{ margin-top: 0; color: #333; }}
            .row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
            .row:last-child {{ border-bottom: none; }}
            .label {{ color: #666; }}
            .value {{ font-weight: bold; }}
            .total {{ font-size: 24px; color: #333; text-align: right; margin-top: 20px; }}
            .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 40px; }}
            .note {{ background: #fff3cd; padding: 10px; border-radius: 4px; margin-top: 20px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">Juke<span>BoB</span></div>
            <p>Where's the Party Tonight</p>
            <p class="invoice-id">Invoice: {booking_id}</p>
        </div>
        
        <div class="section">
            <h3>Event Details</h3>
            <div class="row"><span class="label">Event</span><span class="value">{booking.get('event_title', 'N/A')}</span></div>
            <div class="row"><span class="label">Venue</span><span class="value">{booking.get('venue', 'N/A')}</span></div>
            <div class="row"><span class="label">Date</span><span class="value">{booking.get('event_date', 'N/A')}</span></div>
            <div class="row"><span class="label">Platform</span><span class="value">{booking.get('platform', 'N/A').title()}</span></div>
            <div class="row"><span class="label">Platform Booking ID</span><span class="value">{booking.get('platform_booking_id', 'N/A')}</span></div>
        </div>
        
        <div class="section">
            <h3>Customer Details</h3>
            <div class="row"><span class="label">Name</span><span class="value">{booking.get('user_name', 'N/A')}</span></div>
            <div class="row"><span class="label">Email</span><span class="value">{booking.get('user_email', 'N/A')}</span></div>
            <div class="row"><span class="label">Phone</span><span class="value">{booking.get('user_phone', 'N/A')}</span></div>
        </div>
        
        <div class="section">
            <h3>Booking Summary</h3>
            <div class="row"><span class="label">Number of Tickets</span><span class="value">{booking.get('tickets', 1)}</span></div>
            <div class="row"><span class="label">Booking Date</span><span class="value">{booking.get('booking_date', 'N/A')[:10]}</span></div>
            <div class="row"><span class="label">Status</span><span class="value" style="color: green;">✓ {booking.get('status', 'confirmed').title()}</span></div>
        </div>
        
        <div class="total">
            Total Amount: ₹{booking.get('total_amount', 0):,.2f}
        </div>
        
        <div class="note">
            <strong>Note:</strong> This invoice is for record-keeping purposes. The actual ticket was purchased through {booking.get('platform', 'the original platform').title()}. 
            Please carry your original booking confirmation from {booking.get('platform', 'the platform').title()} to the event.
            <br><br>
            <strong>JukeBoB Commission:</strong> ₹0.00 (No commission charged)
        </div>
        
        <div class="footer">
            <p>Generated by JukeBoB | Where's the Party Tonight</p>
            <p>© 2024 JukeBoB. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    return html


# Create singleton scraper instance
scraper = WTPTScraper()
