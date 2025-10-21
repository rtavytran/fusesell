"""
Timezone Detection Utility
Detect customer timezone from address or other information
"""

import re
import logging
from typing import Optional, Dict, Any


class TimezoneDetector:
    """Utility for detecting customer timezone from various inputs."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common timezone mappings
        self.country_timezones = {
            # North America
            'usa': 'America/New_York',
            'united states': 'America/New_York',
            'us': 'America/New_York',
            'canada': 'America/Toronto',
            'mexico': 'America/Mexico_City',
            
            # Europe
            'uk': 'Europe/London',
            'united kingdom': 'Europe/London',
            'england': 'Europe/London',
            'france': 'Europe/Paris',
            'germany': 'Europe/Berlin',
            'spain': 'Europe/Madrid',
            'italy': 'Europe/Rome',
            'netherlands': 'Europe/Amsterdam',
            'sweden': 'Europe/Stockholm',
            'norway': 'Europe/Oslo',
            'denmark': 'Europe/Copenhagen',
            'finland': 'Europe/Helsinki',
            'poland': 'Europe/Warsaw',
            'russia': 'Europe/Moscow',
            
            # Asia Pacific
            'japan': 'Asia/Tokyo',
            'china': 'Asia/Shanghai',
            'india': 'Asia/Kolkata',
            'singapore': 'Asia/Singapore',
            'thailand': 'Asia/Bangkok',
            'vietnam': 'Asia/Ho_Chi_Minh',
            'philippines': 'Asia/Manila',
            'indonesia': 'Asia/Jakarta',
            'malaysia': 'Asia/Kuala_Lumpur',
            'south korea': 'Asia/Seoul',
            'korea': 'Asia/Seoul',
            'australia': 'Australia/Sydney',
            'new zealand': 'Pacific/Auckland',
            
            # Others
            'brazil': 'America/Sao_Paulo',
            'argentina': 'America/Argentina/Buenos_Aires',
            'south africa': 'Africa/Johannesburg',
            'egypt': 'Africa/Cairo',
            'israel': 'Asia/Jerusalem',
            'uae': 'Asia/Dubai',
            'saudi arabia': 'Asia/Riyadh'
        }
        
        # US state timezones
        self.us_state_timezones = {
            # Eastern Time
            'new york': 'America/New_York',
            'florida': 'America/New_York',
            'georgia': 'America/New_York',
            'virginia': 'America/New_York',
            'north carolina': 'America/New_York',
            'south carolina': 'America/New_York',
            'pennsylvania': 'America/New_York',
            'new jersey': 'America/New_York',
            'massachusetts': 'America/New_York',
            'connecticut': 'America/New_York',
            'maryland': 'America/New_York',
            'delaware': 'America/New_York',
            'maine': 'America/New_York',
            'new hampshire': 'America/New_York',
            'vermont': 'America/New_York',
            'rhode island': 'America/New_York',
            
            # Central Time
            'texas': 'America/Chicago',
            'illinois': 'America/Chicago',
            'wisconsin': 'America/Chicago',
            'minnesota': 'America/Chicago',
            'iowa': 'America/Chicago',
            'missouri': 'America/Chicago',
            'arkansas': 'America/Chicago',
            'louisiana': 'America/Chicago',
            'mississippi': 'America/Chicago',
            'alabama': 'America/Chicago',
            'tennessee': 'America/Chicago',
            'kentucky': 'America/Chicago',
            'oklahoma': 'America/Chicago',
            'kansas': 'America/Chicago',
            'nebraska': 'America/Chicago',
            'south dakota': 'America/Chicago',
            'north dakota': 'America/Chicago',
            
            # Mountain Time
            'colorado': 'America/Denver',
            'utah': 'America/Denver',
            'wyoming': 'America/Denver',
            'montana': 'America/Denver',
            'new mexico': 'America/Denver',
            'arizona': 'America/Phoenix',  # Arizona doesn't observe DST
            
            # Pacific Time
            'california': 'America/Los_Angeles',
            'washington': 'America/Los_Angeles',
            'oregon': 'America/Los_Angeles',
            'nevada': 'America/Los_Angeles',
            
            # Alaska & Hawaii
            'alaska': 'America/Anchorage',
            'hawaii': 'Pacific/Honolulu'
        }
        
        # City timezones
        self.city_timezones = {
            # Major US cities
            'new york': 'America/New_York',
            'los angeles': 'America/Los_Angeles',
            'chicago': 'America/Chicago',
            'houston': 'America/Chicago',
            'phoenix': 'America/Phoenix',
            'philadelphia': 'America/New_York',
            'san antonio': 'America/Chicago',
            'san diego': 'America/Los_Angeles',
            'dallas': 'America/Chicago',
            'san jose': 'America/Los_Angeles',
            'austin': 'America/Chicago',
            'jacksonville': 'America/New_York',
            'san francisco': 'America/Los_Angeles',
            'columbus': 'America/New_York',
            'charlotte': 'America/New_York',
            'fort worth': 'America/Chicago',
            'detroit': 'America/New_York',
            'el paso': 'America/Denver',
            'memphis': 'America/Chicago',
            'seattle': 'America/Los_Angeles',
            'denver': 'America/Denver',
            'washington': 'America/New_York',
            'boston': 'America/New_York',
            'nashville': 'America/Chicago',
            'baltimore': 'America/New_York',
            'oklahoma city': 'America/Chicago',
            'portland': 'America/Los_Angeles',
            'las vegas': 'America/Los_Angeles',
            'milwaukee': 'America/Chicago',
            'albuquerque': 'America/Denver',
            'tucson': 'America/Phoenix',
            'fresno': 'America/Los_Angeles',
            'sacramento': 'America/Los_Angeles',
            'mesa': 'America/Phoenix',
            'kansas city': 'America/Chicago',
            'atlanta': 'America/New_York',
            'long beach': 'America/Los_Angeles',
            'colorado springs': 'America/Denver',
            'raleigh': 'America/New_York',
            'miami': 'America/New_York',
            'virginia beach': 'America/New_York',
            'omaha': 'America/Chicago',
            'oakland': 'America/Los_Angeles',
            'minneapolis': 'America/Chicago',
            'tulsa': 'America/Chicago',
            'arlington': 'America/Chicago',
            'tampa': 'America/New_York',
            'new orleans': 'America/Chicago',
            'wichita': 'America/Chicago',
            'cleveland': 'America/New_York',
            'bakersfield': 'America/Los_Angeles',
            'aurora': 'America/Denver',
            'anaheim': 'America/Los_Angeles',
            'honolulu': 'Pacific/Honolulu',
            'santa ana': 'America/Los_Angeles',
            'corpus christi': 'America/Chicago',
            'riverside': 'America/Los_Angeles',
            'lexington': 'America/New_York',
            'stockton': 'America/Los_Angeles',
            'st. paul': 'America/Chicago',
            'cincinnati': 'America/New_York',
            'anchorage': 'America/Anchorage',
            'henderson': 'America/Los_Angeles',
            'greensboro': 'America/New_York',
            'plano': 'America/Chicago',
            'newark': 'America/New_York',
            'lincoln': 'America/Chicago',
            'buffalo': 'America/New_York',
            'jersey city': 'America/New_York',
            'chula vista': 'America/Los_Angeles',
            'fort wayne': 'America/New_York',
            'orlando': 'America/New_York',
            'st. petersburg': 'America/New_York',
            'chandler': 'America/Phoenix',
            'laredo': 'America/Chicago',
            'norfolk': 'America/New_York',
            'durham': 'America/New_York',
            'madison': 'America/Chicago',
            'lubbock': 'America/Chicago',
            'irvine': 'America/Los_Angeles',
            'winston-salem': 'America/New_York',
            'glendale': 'America/Phoenix',
            'garland': 'America/Chicago',
            'hialeah': 'America/New_York',
            'reno': 'America/Los_Angeles',
            'chesapeake': 'America/New_York',
            'gilbert': 'America/Phoenix',
            'baton rouge': 'America/Chicago',
            'irving': 'America/Chicago',
            'scottsdale': 'America/Phoenix',
            'north las vegas': 'America/Los_Angeles',
            'fremont': 'America/Los_Angeles',
            'boise': 'America/Boise',
            'richmond': 'America/New_York',
            'san bernardino': 'America/Los_Angeles',
            'birmingham': 'America/Chicago',
            'spokane': 'America/Los_Angeles',
            'rochester': 'America/New_York',
            'des moines': 'America/Chicago',
            'modesto': 'America/Los_Angeles',
            'fayetteville': 'America/New_York',
            'tacoma': 'America/Los_Angeles',
            'oxnard': 'America/Los_Angeles',
            'fontana': 'America/Los_Angeles',
            'columbus': 'America/Chicago',
            'montgomery': 'America/Chicago',
            'moreno valley': 'America/Los_Angeles',
            'shreveport': 'America/Chicago',
            'aurora': 'America/Chicago',
            'yonkers': 'America/New_York',
            'akron': 'America/New_York',
            'huntington beach': 'America/Los_Angeles',
            'little rock': 'America/Chicago',
            'augusta': 'America/New_York',
            'amarillo': 'America/Chicago',
            'glendale': 'America/Los_Angeles',
            'mobile': 'America/Chicago',
            'grand rapids': 'America/New_York',
            'salt lake city': 'America/Denver',
            'tallahassee': 'America/New_York',
            'huntsville': 'America/Chicago',
            'grand prairie': 'America/Chicago',
            'knoxville': 'America/New_York',
            'worcester': 'America/New_York',
            'newport news': 'America/New_York',
            'brownsville': 'America/Chicago',
            'overland park': 'America/Chicago',
            'santa clarita': 'America/Los_Angeles',
            'providence': 'America/New_York',
            'garden grove': 'America/Los_Angeles',
            'chattanooga': 'America/New_York',
            'oceanside': 'America/Los_Angeles',
            'jackson': 'America/Chicago',
            'fort lauderdale': 'America/New_York',
            'santa rosa': 'America/Los_Angeles',
            'rancho cucamonga': 'America/Los_Angeles',
            'port st. lucie': 'America/New_York',
            'tempe': 'America/Phoenix',
            'ontario': 'America/Los_Angeles',
            'vancouver': 'America/Los_Angeles',
            'cape coral': 'America/New_York',
            'sioux falls': 'America/Chicago',
            'springfield': 'America/Chicago',
            'peoria': 'America/Chicago',
            'pembroke pines': 'America/New_York',
            'elk grove': 'America/Los_Angeles',
            'salem': 'America/Los_Angeles',
            'lancaster': 'America/Los_Angeles',
            'corona': 'America/Los_Angeles',
            'eugene': 'America/Los_Angeles',
            'palmdale': 'America/Los_Angeles',
            'salinas': 'America/Los_Angeles',
            'springfield': 'America/New_York',
            'pasadena': 'America/Los_Angeles',
            'fort collins': 'America/Denver',
            'hayward': 'America/Los_Angeles',
            'pomona': 'America/Los_Angeles',
            'cary': 'America/New_York',
            'rockford': 'America/Chicago',
            'alexandria': 'America/New_York',
            'escondido': 'America/Los_Angeles',
            'mckinney': 'America/Chicago',
            'kansas city': 'America/Chicago',
            'joliet': 'America/Chicago',
            'sunnyvale': 'America/Los_Angeles',
            'torrance': 'America/Los_Angeles',
            'bridgeport': 'America/New_York',
            'lakewood': 'America/Denver',
            'hollywood': 'America/New_York',
            'paterson': 'America/New_York',
            'naperville': 'America/Chicago',
            'syracuse': 'America/New_York',
            'mesquite': 'America/Chicago',
            'dayton': 'America/New_York',
            'savannah': 'America/New_York',
            'clarksville': 'America/Chicago',
            'orange': 'America/Los_Angeles',
            'pasadena': 'America/Chicago',
            'fullerton': 'America/Los_Angeles',
            'killeen': 'America/Chicago',
            'frisco': 'America/Chicago',
            'hampton': 'America/New_York',
            'mcallen': 'America/Chicago',
            'warren': 'America/New_York',
            'west valley city': 'America/Denver',
            'columbia': 'America/New_York',
            'olathe': 'America/Chicago',
            'sterling heights': 'America/New_York',
            'new haven': 'America/New_York',
            'miramar': 'America/New_York',
            'waco': 'America/Chicago',
            'thousand oaks': 'America/Los_Angeles',
            'cedar rapids': 'America/Chicago',
            'charleston': 'America/New_York',
            'visalia': 'America/Los_Angeles',
            'topeka': 'America/Chicago',
            'elizabeth': 'America/New_York',
            'gainesville': 'America/New_York',
            'thornton': 'America/Denver',
            'roseville': 'America/Los_Angeles',
            'carrollton': 'America/Chicago',
            'coral springs': 'America/New_York',
            'stamford': 'America/New_York',
            'simi valley': 'America/Los_Angeles',
            'concord': 'America/Los_Angeles',
            'hartford': 'America/New_York',
            'kent': 'America/Los_Angeles',
            'lafayette': 'America/Chicago',
            'midland': 'America/Chicago',
            'surprise': 'America/Phoenix',
            'denton': 'America/Chicago',
            'victorville': 'America/Los_Angeles',
            'evansville': 'America/Chicago',
            'santa clara': 'America/Los_Angeles',
            'abilene': 'America/Chicago',
            'athens': 'America/New_York',
            'vallejo': 'America/Los_Angeles',
            'allentown': 'America/New_York',
            'norman': 'America/Chicago',
            'beaumont': 'America/Chicago',
            'independence': 'America/Chicago',
            'murfreesboro': 'America/Chicago',
            'ann arbor': 'America/New_York',
            'fargo': 'America/Chicago',
            'temecula': 'America/Los_Angeles',
            'bellevue': 'America/Los_Angeles',
            'westminster': 'America/Denver',
            'arvada': 'America/Denver',
            'clearwater': 'America/New_York',
            'richardson': 'America/Chicago',
            'rochester': 'America/Chicago',
            'pueblo': 'America/Denver',
            'carlsbad': 'America/Los_Angeles',
            'fairfield': 'America/Los_Angeles',
            'west palm beach': 'America/New_York',
            'lowell': 'America/New_York',
            'billings': 'America/Denver',
            'san mateo': 'America/Los_Angeles',
            'el monte': 'America/Los_Angeles',
            'jurupa valley': 'America/Los_Angeles',
            'las cruces': 'America/Denver',
            'burbank': 'America/Los_Angeles',
            'fort smith': 'America/Chicago',
            'albany': 'America/New_York',
            'clovis': 'America/Los_Angeles',
            'inglewood': 'America/Los_Angeles',
            'sandy': 'America/Denver',
            'sandy springs': 'America/New_York',
            'hillsboro': 'America/Los_Angeles',
            'waterbury': 'America/New_York',
            'santa maria': 'America/Los_Angeles',
            'boulder': 'America/Denver',
            'greeley': 'America/Denver',
            'daly city': 'America/Los_Angeles',
            'meridian': 'America/Boise',
            'lewisville': 'America/Chicago',
            'davie': 'America/New_York',
            'west jordan': 'America/Denver',
            'league city': 'America/Chicago',
            'tyler': 'America/Chicago',
            'pearland': 'America/Chicago',
            'college station': 'America/Chicago',
            'kenosha': 'America/Chicago',
            'sandy': 'America/Denver',
            'missoula': 'America/Denver',
            'richardson': 'America/Chicago',
            'spokane valley': 'America/Los_Angeles',
            'arvada': 'America/Denver',
            'centennial': 'America/Denver',
            'roswell': 'America/New_York',
            'rialto': 'America/Los_Angeles',
            'el cajon': 'America/Los_Angeles',
            'las vegas': 'America/Los_Angeles',
            'miami gardens': 'America/New_York',
            'burbank': 'America/Los_Angeles',
            'south bend': 'America/New_York',
            'renton': 'America/Los_Angeles',
            'berkeley': 'America/Los_Angeles',
            'pompano beach': 'America/New_York',
            'woodbridge': 'America/New_York',
            'reading': 'America/New_York',
            'richmond': 'America/Los_Angeles',
            'beaverton': 'America/Los_Angeles',
            'broken arrow': 'America/Chicago',
            'west palm beach': 'America/New_York',
            'cambridge': 'America/New_York',
            'clearwater': 'America/New_York',
            'west valley city': 'America/Denver',
            'round rock': 'America/Chicago',
            'lakeland': 'America/New_York',
            'livermore': 'America/Los_Angeles',
            'sugar land': 'America/Chicago',
            'longmont': 'America/Denver',
            'boca raton': 'America/New_York',
            'san mateo': 'America/Los_Angeles',
            'hesperia': 'America/Los_Angeles',
            'baldwin park': 'America/Los_Angeles',
            'chico': 'America/Los_Angeles',
            'odessa': 'America/Chicago',
            'roanoke': 'America/New_York',
            'carson': 'America/Los_Angeles',
            'fort collins': 'America/Denver',
            'albany': 'America/New_York',
            'danbury': 'America/New_York',
            'compton': 'America/Los_Angeles',
            'san leandro': 'America/Los_Angeles',
            'tuscaloosa': 'America/Chicago',
            'spokane': 'America/Los_Angeles',
            'antioch': 'America/Los_Angeles',
            'high point': 'America/New_York',
            'norwalk': 'America/Los_Angeles',
            'centennial': 'America/Denver',
            'everett': 'America/Los_Angeles',
            'elgin': 'America/Chicago',
            'wichita falls': 'America/Chicago',
            'erie': 'America/New_York',
            'frederick': 'America/New_York',
            'gresham': 'America/Los_Angeles',
            'santa barbara': 'America/Los_Angeles',
            'pueblo': 'America/Denver',
            'dearborn': 'America/New_York',
            'lawton': 'America/Chicago',
            'san angelo': 'America/Chicago',
            'murrieta': 'America/Los_Angeles',
            'rochester': 'America/Chicago',
            'champaign': 'America/Chicago',
            'ogden': 'America/Denver',
            'concord': 'America/New_York',
            'denton': 'America/Chicago',
            'davenport': 'America/Chicago',
            'garden grove': 'America/Los_Angeles',
            'yakima': 'America/Los_Angeles',
            'new bedford': 'America/New_York',
            'south gate': 'America/Los_Angeles',
            'st. joseph': 'America/Chicago',
            'kalamazoo': 'America/New_York',
            'birmingham': 'America/New_York',
            'racine': 'America/Chicago',
            'orem': 'America/Denver',
            'flint': 'America/New_York',
            'las cruces': 'America/Denver',
            'springfield': 'America/Chicago',
            'brockton': 'America/New_York',
            'fayetteville': 'America/Chicago',
            'carson city': 'America/Los_Angeles',
            'santa monica': 'America/Los_Angeles',
            'fall river': 'America/New_York',
            'lynchburg': 'America/New_York',
            'nampa': 'America/Boise',
            'troy': 'America/New_York',
            'quincy': 'America/New_York',
            'duluth': 'America/Chicago',
            'chula vista': 'America/Los_Angeles',
            'dayton': 'America/New_York',
            'springfield': 'America/New_York',
            'orange': 'America/Los_Angeles',
            'akron': 'America/New_York',
            'huntington beach': 'America/Los_Angeles',
            'little rock': 'America/Chicago',
            'augusta': 'America/New_York',
            'amarillo': 'America/Chicago',
            'glendale': 'America/Los_Angeles',
            'mobile': 'America/Chicago',
            'grand rapids': 'America/New_York',
            'salt lake city': 'America/Denver',
            'tallahassee': 'America/New_York',
            'huntsville': 'America/Chicago',
            'grand prairie': 'America/Chicago',
            'knoxville': 'America/New_York',
            'worcester': 'America/New_York',
            'newport news': 'America/New_York',
            'brownsville': 'America/Chicago',
            'overland park': 'America/Chicago',
            'santa clarita': 'America/Los_Angeles',
            'providence': 'America/New_York',
            'garden grove': 'America/Los_Angeles',
            'chattanooga': 'America/New_York',
            'oceanside': 'America/Los_Angeles',
            'jackson': 'America/Chicago',
            'fort lauderdale': 'America/New_York',
            'santa rosa': 'America/Los_Angeles',
            'rancho cucamonga': 'America/Los_Angeles',
            'port st. lucie': 'America/New_York',
            'tempe': 'America/Phoenix',
            'ontario': 'America/Los_Angeles',
            'vancouver': 'America/Los_Angeles',
            'cape coral': 'America/New_York',
            'sioux falls': 'America/Chicago',
            'springfield': 'America/Chicago',
            'peoria': 'America/Chicago',
            'pembroke pines': 'America/New_York',
            'elk grove': 'America/Los_Angeles',
            'salem': 'America/Los_Angeles',
            'lancaster': 'America/Los_Angeles',
            'corona': 'America/Los_Angeles',
            'eugene': 'America/Los_Angeles',
            'palmdale': 'America/Los_Angeles',
            'salinas': 'America/Los_Angeles',
            'springfield': 'America/New_York',
            'pasadena': 'America/Los_Angeles',
            'fort collins': 'America/Denver',
            'hayward': 'America/Los_Angeles',
            'pomona': 'America/Los_Angeles',
            'cary': 'America/New_York',
            'rockford': 'America/Chicago',
            'alexandria': 'America/New_York',
            'escondido': 'America/Los_Angeles',
            'mckinney': 'America/Chicago',
            'kansas city': 'America/Chicago',
            'joliet': 'America/Chicago',
            'sunnyvale': 'America/Los_Angeles',
            'torrance': 'America/Los_Angeles',
            'bridgeport': 'America/New_York',
            'lakewood': 'America/Denver',
            'hollywood': 'America/New_York',
            'paterson': 'America/New_York',
            'naperville': 'America/Chicago',
            'syracuse': 'America/New_York',
            'mesquite': 'America/Chicago',
            'dayton': 'America/New_York',
            'savannah': 'America/New_York',
            'clarksville': 'America/Chicago',
            'orange': 'America/Los_Angeles',
            'pasadena': 'America/Chicago',
            'fullerton': 'America/Los_Angeles',
            'killeen': 'America/Chicago',
            'frisco': 'America/Chicago',
            'hampton': 'America/New_York',
            'mcallen': 'America/Chicago',
            'warren': 'America/New_York',
            'west valley city': 'America/Denver',
            'columbia': 'America/New_York',
            'olathe': 'America/Chicago',
            'sterling heights': 'America/New_York',
            'new haven': 'America/New_York',
            'miramar': 'America/New_York',
            'waco': 'America/Chicago',
            'thousand oaks': 'America/Los_Angeles',
            'cedar rapids': 'America/Chicago',
            'charleston': 'America/New_York',
            'visalia': 'America/Los_Angeles',
            'topeka': 'America/Chicago',
            'elizabeth': 'America/New_York',
            'gainesville': 'America/New_York',
            'thornton': 'America/Denver',
            'roseville': 'America/Los_Angeles',
            'carrollton': 'America/Chicago',
            'coral springs': 'America/New_York',
            'stamford': 'America/New_York',
            'simi valley': 'America/Los_Angeles',
            'concord': 'America/Los_Angeles',
            'hartford': 'America/New_York',
            'kent': 'America/Los_Angeles',
            'lafayette': 'America/Chicago',
            'midland': 'America/Chicago',
            'surprise': 'America/Phoenix',
            'denton': 'America/Chicago',
            'victorville': 'America/Los_Angeles',
            'evansville': 'America/Chicago',
            'santa clara': 'America/Los_Angeles',
            'abilene': 'America/Chicago',
            'athens': 'America/New_York',
            'vallejo': 'America/Los_Angeles',
            'allentown': 'America/New_York',
            'norman': 'America/Chicago',
            'beaumont': 'America/Chicago',
            'independence': 'America/Chicago',
            'murfreesboro': 'America/Chicago',
            'ann arbor': 'America/New_York',
            'fargo': 'America/Chicago',
            'temecula': 'America/Los_Angeles',
            'bellevue': 'America/Los_Angeles',
            'westminster': 'America/Denver',
            'arvada': 'America/Denver',
            'clearwater': 'America/New_York',
            'richardson': 'America/Chicago',
            'rochester': 'America/Chicago',
            'pueblo': 'America/Denver',
            'carlsbad': 'America/Los_Angeles',
            'fairfield': 'America/Los_Angeles',
            'west palm beach': 'America/New_York',
            'lowell': 'America/New_York',
            'billings': 'America/Denver',
            'san mateo': 'America/Los_Angeles',
            'el monte': 'America/Los_Angeles',
            'jurupa valley': 'America/Los_Angeles',
            'las cruces': 'America/Denver',
            'burbank': 'America/Los_Angeles',
            'fort smith': 'America/Chicago',
            'albany': 'America/New_York',
            'clovis': 'America/Los_Angeles',
            'inglewood': 'America/Los_Angeles',
            'sandy': 'America/Denver',
            'sandy springs': 'America/New_York',
            'hillsboro': 'America/Los_Angeles',
            'waterbury': 'America/New_York',
            'santa maria': 'America/Los_Angeles',
            'boulder': 'America/Denver',
            'greeley': 'America/Denver',
            'daly city': 'America/Los_Angeles',
            'meridian': 'America/Boise',
            'lewisville': 'America/Chicago',
            'davie': 'America/New_York',
            'west jordan': 'America/Denver',
            'league city': 'America/Chicago',
            'tyler': 'America/Chicago',
            'pearland': 'America/Chicago',
            'college station': 'America/Chicago',
            'kenosha': 'America/Chicago',
            'sandy': 'America/Denver',
            'missoula': 'America/Denver',
            'richardson': 'America/Chicago',
            'spokane valley': 'America/Los_Angeles',
            'arvada': 'America/Denver',
            'centennial': 'America/Denver',
            'roswell': 'America/New_York',
            'rialto': 'America/Los_Angeles',
            'el cajon': 'America/Los_Angeles',
            'las vegas': 'America/Los_Angeles',
            'miami gardens': 'America/New_York',
            'burbank': 'America/Los_Angeles',
            'south bend': 'America/New_York',
            'renton': 'America/Los_Angeles',
            'berkeley': 'America/Los_Angeles',
            'pompano beach': 'America/New_York',
            'woodbridge': 'America/New_York',
            'reading': 'America/New_York',
            'richmond': 'America/Los_Angeles',
            'beaverton': 'America/Los_Angeles',
            'broken arrow': 'America/Chicago',
            'west palm beach': 'America/New_York',
            'cambridge': 'America/New_York',
            'clearwater': 'America/New_York',
            'west valley city': 'America/Denver',
            'round rock': 'America/Chicago',
            'lakeland': 'America/New_York',
            'livermore': 'America/Los_Angeles',
            'sugar land': 'America/Chicago',
            'longmont': 'America/Denver',
            'boca raton': 'America/New_York',
            'san mateo': 'America/Los_Angeles',
            'hesperia': 'America/Los_Angeles',
            'baldwin park': 'America/Los_Angeles',
            'chico': 'America/Los_Angeles',
            'odessa': 'America/Chicago',
            'roanoke': 'America/New_York',
            'carson': 'America/Los_Angeles',
            'fort collins': 'America/Denver',
            'albany': 'America/New_York',
            'danbury': 'America/New_York',
            'compton': 'America/Los_Angeles',
            'san leandro': 'America/Los_Angeles',
            'tuscaloosa': 'America/Chicago',
            'spokane': 'America/Los_Angeles',
            'antioch': 'America/Los_Angeles',
            'high point': 'America/New_York',
            'norwalk': 'America/Los_Angeles',
            'centennial': 'America/Denver',
            'everett': 'America/Los_Angeles',
            'elgin': 'America/Chicago',
            'wichita falls': 'America/Chicago',
            'erie': 'America/New_York',
            'frederick': 'America/New_York',
            'gresham': 'America/Los_Angeles',
            'santa barbara': 'America/Los_Angeles',
            'pueblo': 'America/Denver',
            'dearborn': 'America/New_York',
            'lawton': 'America/Chicago',
            'san angelo': 'America/Chicago',
            'murrieta': 'America/Los_Angeles',
            'rochester': 'America/Chicago',
            'champaign': 'America/Chicago',
            'ogden': 'America/Denver',
            'concord': 'America/New_York',
            'denton': 'America/Chicago',
            'davenport': 'America/Chicago',
            'garden grove': 'America/Los_Angeles',
            'yakima': 'America/Los_Angeles',
            'new bedford': 'America/New_York',
            'south gate': 'America/Los_Angeles',
            'st. joseph': 'America/Chicago',
            'kalamazoo': 'America/New_York',
            'birmingham': 'America/New_York',
            'racine': 'America/Chicago',
            'orem': 'America/Denver',
            'flint': 'America/New_York',
            'las cruces': 'America/Denver',
            'springfield': 'America/Chicago',
            'brockton': 'America/New_York',
            'fayetteville': 'America/Chicago',
            'carson city': 'America/Los_Angeles',
            'santa monica': 'America/Los_Angeles',
            'fall river': 'America/New_York',
            'lynchburg': 'America/New_York',
            'nampa': 'America/Boise',
            'troy': 'America/New_York',
            'quincy': 'America/New_York',
            'duluth': 'America/Chicago',
            
            # International cities
            'london': 'Europe/London',
            'paris': 'Europe/Paris',
            'berlin': 'Europe/Berlin',
            'madrid': 'Europe/Madrid',
            'rome': 'Europe/Rome',
            'amsterdam': 'Europe/Amsterdam',
            'stockholm': 'Europe/Stockholm',
            'oslo': 'Europe/Oslo',
            'copenhagen': 'Europe/Copenhagen',
            'helsinki': 'Europe/Helsinki',
            'warsaw': 'Europe/Warsaw',
            'moscow': 'Europe/Moscow',
            'tokyo': 'Asia/Tokyo',
            'shanghai': 'Asia/Shanghai',
            'beijing': 'Asia/Shanghai',
            'mumbai': 'Asia/Kolkata',
            'delhi': 'Asia/Kolkata',
            'bangalore': 'Asia/Kolkata',
            'singapore': 'Asia/Singapore',
            'bangkok': 'Asia/Bangkok',
            'ho chi minh city': 'Asia/Ho_Chi_Minh',
            'saigon': 'Asia/Ho_Chi_Minh',
            'manila': 'Asia/Manila',
            'jakarta': 'Asia/Jakarta',
            'kuala lumpur': 'Asia/Kuala_Lumpur',
            'seoul': 'Asia/Seoul',
            'sydney': 'Australia/Sydney',
            'melbourne': 'Australia/Melbourne',
            'auckland': 'Pacific/Auckland',
            'sao paulo': 'America/Sao_Paulo',
            'buenos aires': 'America/Argentina/Buenos_Aires',
            'johannesburg': 'Africa/Johannesburg',
            'cairo': 'Africa/Cairo',
            'tel aviv': 'Asia/Jerusalem',
            'dubai': 'Asia/Dubai',
            'riyadh': 'Asia/Riyadh',
            'toronto': 'America/Toronto',
            'vancouver': 'America/Vancouver',
            'montreal': 'America/Toronto',
            'mexico city': 'America/Mexico_City'
        }
    
    def detect_timezone(self, customer_data: Dict[str, Any]) -> str:
        """
        Detect customer timezone from various data sources.
        
        Args:
            customer_data: Customer information
            
        Returns:
            Timezone string (e.g., 'America/New_York')
        """
        try:
            # Check if timezone is explicitly provided
            if 'customer_timezone' in customer_data:
                return customer_data['customer_timezone']
            
            # Try to extract from address
            address_timezone = self._detect_from_address(customer_data)
            if address_timezone:
                return address_timezone
            
            # Try to extract from company info
            company_timezone = self._detect_from_company_info(customer_data)
            if company_timezone:
                return company_timezone
            
            # Try to extract from contact info
            contact_timezone = self._detect_from_contact_info(customer_data)
            if contact_timezone:
                return contact_timezone
            
            # Default fallback
            self.logger.info("Could not detect timezone, using default: Asia/Bangkok")
            return 'Asia/Bangkok'
            
        except Exception as e:
            self.logger.error(f"Timezone detection failed: {str(e)}")
            return 'Asia/Bangkok'
    
    def _detect_from_address(self, customer_data: Dict[str, Any]) -> Optional[str]:
        """Detect timezone from address information."""
        try:
            # Check various address fields
            address_fields = [
                customer_data.get('customer_address', ''),
                customer_data.get('companyInfo', {}).get('address', ''),
                customer_data.get('primaryContact', {}).get('address', ''),
                customer_data.get('address', '')
            ]
            
            for address in address_fields:
                if not address:
                    continue
                
                address_lower = address.lower()
                
                # Check for country matches
                for country, timezone in self.country_timezones.items():
                    if country in address_lower:
                        self.logger.info(f"Detected timezone from country '{country}': {timezone}")
                        return timezone
                
                # Check for US state matches
                for state, timezone in self.us_state_timezones.items():
                    if state in address_lower:
                        self.logger.info(f"Detected timezone from US state '{state}': {timezone}")
                        return timezone
                
                # Check for city matches
                for city, timezone in self.city_timezones.items():
                    if city in address_lower:
                        self.logger.info(f"Detected timezone from city '{city}': {timezone}")
                        return timezone
            
            return None
            
        except Exception as e:
            self.logger.error(f"Address timezone detection failed: {str(e)}")
            return None
    
    def _detect_from_company_info(self, customer_data: Dict[str, Any]) -> Optional[str]:
        """Detect timezone from company information."""
        try:
            company_info = customer_data.get('companyInfo', {})
            
            # Check company location fields
            location_fields = [
                company_info.get('location', ''),
                company_info.get('headquarters', ''),
                company_info.get('country', ''),
                company_info.get('region', '')
            ]
            
            for location in location_fields:
                if not location:
                    continue
                
                location_lower = location.lower()
                
                # Check for matches
                for country, timezone in self.country_timezones.items():
                    if country in location_lower:
                        return timezone
                
                for city, timezone in self.city_timezones.items():
                    if city in location_lower:
                        return timezone
            
            return None
            
        except Exception as e:
            self.logger.error(f"Company info timezone detection failed: {str(e)}")
            return None
    
    def _detect_from_contact_info(self, customer_data: Dict[str, Any]) -> Optional[str]:
        """Detect timezone from contact information."""
        try:
            contact_info = customer_data.get('primaryContact', {})
            
            # Check contact location fields
            location_fields = [
                contact_info.get('location', ''),
                contact_info.get('city', ''),
                contact_info.get('country', '')
            ]
            
            for location in location_fields:
                if not location:
                    continue
                
                location_lower = location.lower()
                
                # Check for matches
                for country, timezone in self.country_timezones.items():
                    if country in location_lower:
                        return timezone
                
                for city, timezone in self.city_timezones.items():
                    if city in location_lower:
                        return timezone
            
            return None
            
        except Exception as e:
            self.logger.error(f"Contact info timezone detection failed: {str(e)}")
            return None