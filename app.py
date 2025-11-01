from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from datetime import datetime, timezone
import random
import requests
from threading import Thread, Event, Lock
import time
import csv
import io
import json
import logging
from collections import deque, Counter, defaultdict
from typing import Dict, List, Any, Optional, TypedDict, Tuple
from database import AttackDatabase
from utils.config import load_config
from services.osint import OSINTService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Use environment variable or generate a secure random key
import os
import sqlite3

app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24).hex())

# SECURITY FIX: Restrict CORS to specific origins from environment
ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5000').split(',')
socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS)

# SECURITY ENHANCEMENT: Initialize rate limiter for DoS protection
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5000 per day", "500 per hour"],  # Increased for dashboard usage
    storage_uri="memory://",
    strategy="fixed-window"
)

db = AttackDatabase()

# Load configuration and initialize OSINT service
try:
    config = load_config()
    osint_service = OSINTService(config)
    if osint_service.is_shodan_available():
        logger.info("✓ Shodan OSINT integration enabled")
    else:
        logger.info("○ Shodan OSINT integration disabled (API key not configured)")
except Exception as e:
    logger.warning(f"Could not initialize OSINT service: {e}")
    osint_service = None

# ============================================================================
# SWAGGER API DOCUMENTATION CONFIGURATION
# ============================================================================

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "title": "DDOS Tracker API",
    "version": "1.0.0",
    "description": "API for real-time DDoS attack tracking and threat intelligence",
    "termsOfService": "",
    "contact": {
        "name": "API Support",
        "url": "http://localhost:5000/health"
    }
}

swagger = Swagger(app, config=swagger_config)

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# Attack tracking configuration
MAX_ATTACKS = 100  # Maximum number of recent attacks to keep in memory
MAX_THREAT_HISTORY = 60  # Keep last 60 threat score readings

# Threat scoring configuration
_SCORE_PRECISION = 1  # Decimal places for score display
_ANALYSIS_WINDOW_SECONDS = 300  # Time window for threat analysis (5 minutes)
THREAT_SCORE_UPDATE_INTERVAL = 5  # Seconds between threat score updates

# Threat level thresholds
THREAT_LEVEL_CRITICAL = 80  # Score threshold for critical threat level
THREAT_LEVEL_HIGH = 60  # Score threshold for high threat level
THREAT_LEVEL_MEDIUM = 35  # Score threshold for medium threat level

# Trend detection thresholds
ESCALATION_THRESHOLD = 10  # Points above average to detect escalation
DE_ESCALATION_THRESHOLD = 10  # Points below average to detect de-escalation

# Cache configuration
CACHE_DURATION = 90  # IP threat data cache duration (seconds)
IP_GEOLOCATION_DELAY = 1.5  # Delay between IP geolocation API calls (seconds)

# API rate limiting and validation
MAX_EXPORT_LIMIT = 1000  # Maximum records for export operations
MAX_FILTER_LIMIT = 1000  # Maximum records for filter operations
DEFAULT_EXPORT_LIMIT = 100  # Default number of records to export
MAX_TIME_RANGE_MINUTES = 1440  # Maximum time range for queries (24 hours)

# Attack generation configuration
US_ATTACK_PROBABILITY = 0.3  # Probability of generating US attack (30%)
BURST_ATTACK_PROBABILITY = 0.1  # Probability of burst attack (10%)
IPV6_PROBABILITY = 0.4  # Probability of IPv6 address in US attacks (40%)

# Attack intensity configuration
MIN_ATTACK_INTENSITY = 0.3  # Minimum attack generation intensity
MAX_ATTACK_INTENSITY = 2.0  # Maximum attack generation intensity
MIN_SLEEP_TIME = 1.0  # Minimum seconds between attack generation
MAX_SLEEP_TIME = 5.0  # Maximum seconds between attack generation

# Store recent attacks in memory for real-time display (using deque for O(1) operations)
recent_attacks: deque = deque(maxlen=MAX_ATTACKS)
recent_attacks_lock = Lock()

# IP Geolocation cache and threat data cache
ip_cache: Dict[str, Dict[str, Any]] = {}
ip_cache_lock = Lock()

threat_ips_cache: List[str] = []
threat_cache_lock = Lock()
last_fetch_time: float = 0

# Threat Score System (using deque for efficient history management)
threat_score_history: deque = deque(maxlen=MAX_THREAT_HISTORY)
threat_history_lock = Lock()

# Shutdown event for graceful shutdown
shutdown_event = Event()

# Type definitions for threat score
class ThreatScoreFactors(TypedDict):
    frequency: float
    severity: float
    diversity: float
    concentration: float

class ThreatScoreResult(TypedDict):
    score: int
    level: str
    trend: str
    factors: ThreatScoreFactors
    timestamp: str

# Input Validation Helpers
def validate_positive_int(value: Optional[str], default: int, max_value: int = 10000) -> int:
    """Validate and sanitize integer inputs.
    
    Args:
        value: String value to validate
        default: Default value if validation fails
        max_value: Maximum allowed value
        
    Returns:
        Validated integer between 1 and max_value
    """
    try:
        num = int(value) if value else default
        return max(1, min(num, max_value))
    except (ValueError, TypeError):
        return default

def validate_time_range(value: Optional[str], default: int = 60) -> int:
    """Validate time range parameter using configured max value.
    
    Args:
        value: String value representing minutes
        default: Default value (60 minutes)
        
    Returns:
        Validated time range capped at configured maximum
    """
    try:
        minutes = int(value) if value else default
        return max(1, min(minutes, MAX_TIME_RANGE_MINUTES))
    except (ValueError, TypeError):
        return default

def _round_scores(scores: Dict[str, float]) -> ThreatScoreFactors:
    """Round score factors to configured precision."""
    return {
        key: round(value, _SCORE_PRECISION)
        for key, value in scores.items()
    }

def _classify_threat_level(score: int) -> str:
    """Classify threat level based on score using configured thresholds."""
    if score >= THREAT_LEVEL_CRITICAL:
        return 'Critical'
    elif score >= THREAT_LEVEL_HIGH:
        return 'High'
    elif score >= THREAT_LEVEL_MEDIUM:
        return 'Medium'
    else:
        return 'Low'

def _calculate_trend(history: deque, current_score: int) -> str:
    """Calculate threat score trend using configured thresholds."""
    if len(history) < 5:
        return 'stable'
    
    # Analyze last 5 scores
    recent_scores = [record['score'] for record in list(history)[-5:]]
    avg_recent = sum(recent_scores) / len(recent_scores)
    
    # Use configured thresholds for trend detection
    if current_score > avg_recent + ESCALATION_THRESHOLD:
        return 'escalating'
    elif current_score < avg_recent - DE_ESCALATION_THRESHOLD:
        return 'de-escalating'
    else:
        return 'stable'

def calculate_threat_score() -> ThreatScoreResult:
    """Calculate overall threat score based on recent attacks (0-100).
    
    This function analyzes recent attack patterns and calculates a comprehensive
    threat score using multiple weighted factors:
    - Attack frequency (weight: 30%)
    - Severity distribution (weight: 40%)
    - Attack type diversity (weight: 15%)
    - Geographic concentration (weight: 15%)
    
    Returns:
        Dict containing score, level, trend, factors, and timestamp
    """
    try:
        if not recent_attacks:
            return {
                'score': 0,
                'level': 'Low',
                'trend': 'stable',
                'factors': {
                    'frequency': 0.0,
                    'severity': 0.0,
                    'diversity': 0.0,
                    'concentration': 0.0
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Time window for analysis (last 5 minutes)
        recent_time = time.time() - _ANALYSIS_WINDOW_SECONDS
        recent_attack_list = [a for a in recent_attacks if 
                              datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')).timestamp() > recent_time]
        
        if not recent_attack_list:
            recent_attack_list = list(recent_attacks)[-10:]  # At least check last 10
        
        if not recent_attack_list:
            return {
                'score': 0,
                'level': 'Low',
                'trend': 'stable',
                'factors': {
                    'frequency': 0.0,
                    'severity': 0.0,
                    'diversity': 0.0,
                    'concentration': 0.0
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Factor 1: Attack frequency (0-30 points)
        frequency_score = min(30.0, len(recent_attack_list) * 1.5)
        
        # Factor 2: Severity distribution (0-40 points)
        severity_weights = {'Critical': 10, 'High': 6, 'Medium': 3, 'Low': 1}
        severity_score = sum(severity_weights.get(a.get('severity', 'Low'), 1) for a in recent_attack_list)
        severity_score = min(40.0, severity_score / 2.0)
        
        # Factor 3: Attack type diversity (0-15 points)
        unique_types = len({a.get('attack_type', 'Unknown') for a in recent_attack_list})
        diversity_score = min(15.0, unique_types * 2.0)
        
        # Factor 4: Geographic concentration (0-15 points)
        target_countries = [a['destination']['country'] for a in recent_attack_list if 'destination' in a]
        if target_countries:
            top_target_count = Counter(target_countries).most_common(1)[0][1]
            concentration_score = min(15.0, (top_target_count / len(target_countries)) * 20.0)
        else:
            concentration_score = 0.0
        
        # Calculate total score
        total_score = min(100, int(
            frequency_score + severity_score + diversity_score + concentration_score
        ))
        
        # Classify threat level
        threat_level = _classify_threat_level(total_score)
        
        # Determine trend based on history
        trend = _calculate_trend(threat_score_history, total_score)
        
        # Build result object with proper types and UTC timestamp
        result: ThreatScoreResult = {
            'score': total_score,
            'level': threat_level,
            'trend': trend,
            'factors': _round_scores({
                'frequency': frequency_score,
                'severity': severity_score,
                'diversity': diversity_score,
                'concentration': concentration_score
            }),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store in history (deque automatically manages size)
        threat_score_history.append(result)
        
        logger.debug(f"Calculated threat score: {total_score} ({threat_level})")
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating threat score: {e}")
        return {
            'score': 0,
            'level': 'Low',
            'trend': 'stable',
            'factors': {
                'frequency': 0.0,
                'severity': 0.0,
                'diversity': 0.0,
                'concentration': 0.0
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


def calculate_country_threat_scores():
    """Calculate threat scores per country"""
    try:
        from collections import defaultdict, Counter
        
        if not recent_attacks:
            return []
        
        # Time window (last 10 minutes)
        recent_time = time.time() - 600
        recent_attack_list = [a for a in recent_attacks if 
                              datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')).timestamp() > recent_time]
        
        if not recent_attack_list:
            recent_attack_list = list(recent_attacks)[-30:]
        
        if not recent_attack_list:
            return []
        
        country_attacks = defaultdict(list)
        for attack in recent_attack_list:
            if 'destination' in attack and 'country' in attack['destination']:
                country_attacks[attack['destination']['country']].append(attack)
        
        country_scores = []
        for country, attacks in country_attacks.items():
            # Calculate mini threat score for this country
            attack_count = len(attacks)
            severity_weights = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
            severity_sum = sum(severity_weights.get(a.get('severity', 'Low'), 0) for a in attacks)
            
            score = min(100, (attack_count * 5) + (severity_sum * 3))
            
            country_scores.append({
                'country': country,
                'score': score,
                'attack_count': attack_count,
                'critical_count': sum(1 for a in attacks if a.get('severity') == 'Critical')
            })
        
        # Sort by score
        country_scores.sort(key=lambda x: x['score'], reverse=True)
        return country_scores[:10]  # Top 10
    except Exception as e:
        logger.error(f"Error calculating country threat scores: {e}")
        return []

# Comprehensive US cities (all 50 states represented)
US_CITIES = [
    # Original major cities
    {"name": "New York", "lat": 40.7128, "lon": -74.0060, "state": "NY"},
    {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437, "state": "CA"},
    {"name": "Chicago", "lat": 41.8781, "lon": -87.6298, "state": "IL"},
    {"name": "Houston", "lat": 29.7604, "lon": -95.3698, "state": "TX"},
    {"name": "Phoenix", "lat": 33.4484, "lon": -112.0740, "state": "AZ"},
    {"name": "Philadelphia", "lat": 39.9526, "lon": -75.1652, "state": "PA"},
    {"name": "San Antonio", "lat": 29.4241, "lon": -98.4936, "state": "TX"},
    {"name": "San Diego", "lat": 32.7157, "lon": -117.1611, "state": "CA"},
    {"name": "Dallas", "lat": 32.7767, "lon": -96.7970, "state": "TX"},
    {"name": "San Jose", "lat": 37.3382, "lon": -121.8863, "state": "CA"},
    {"name": "Austin", "lat": 30.2672, "lon": -97.7431, "state": "TX"},
    {"name": "Seattle", "lat": 47.6062, "lon": -122.3321, "state": "WA"},
    {"name": "Denver", "lat": 39.7392, "lon": -104.9903, "state": "CO"},
    {"name": "Miami", "lat": 25.7617, "lon": -80.1918, "state": "FL"},
    {"name": "Atlanta", "lat": 33.7490, "lon": -84.3880, "state": "GA"},
    {"name": "Boston", "lat": 42.3601, "lon": -71.0589, "state": "MA"},
    {"name": "Las Vegas", "lat": 36.1699, "lon": -115.1398, "state": "NV"},
    {"name": "Portland", "lat": 45.5152, "lon": -122.6784, "state": "OR"},
    {"name": "Detroit", "lat": 42.3314, "lon": -83.0458, "state": "MI"},
    {"name": "Minneapolis", "lat": 44.9778, "lon": -93.2650, "state": "MN"},
    # Additional cities to cover all 50 states
    {"name": "Birmingham", "lat": 33.5186, "lon": -86.8104, "state": "AL"},
    {"name": "Anchorage", "lat": 61.2181, "lon": -149.9003, "state": "AK"},
    {"name": "Little Rock", "lat": 34.7465, "lon": -92.2896, "state": "AR"},
    {"name": "San Francisco", "lat": 37.7749, "lon": -122.4194, "state": "CA"},
    {"name": "Colorado Springs", "lat": 38.8339, "lon": -104.8214, "state": "CO"},
    {"name": "Hartford", "lat": 41.7658, "lon": -72.6734, "state": "CT"},
    {"name": "Wilmington", "lat": 39.7391, "lon": -75.5398, "state": "DE"},
    {"name": "Jacksonville", "lat": 30.3322, "lon": -81.6557, "state": "FL"},
    {"name": "Savannah", "lat": 32.0809, "lon": -81.0912, "state": "GA"},
    {"name": "Honolulu", "lat": 21.3099, "lon": -157.8581, "state": "HI"},
    {"name": "Boise", "lat": 43.6150, "lon": -116.2023, "state": "ID"},
    {"name": "Springfield", "lat": 39.7817, "lon": -89.6501, "state": "IL"},
    {"name": "Indianapolis", "lat": 39.7684, "lon": -86.1581, "state": "IN"},
    {"name": "Des Moines", "lat": 41.5868, "lon": -93.6250, "state": "IA"},
    {"name": "Wichita", "lat": 37.6872, "lon": -97.3301, "state": "KS"},
    {"name": "Louisville", "lat": 38.2527, "lon": -85.7585, "state": "KY"},
    {"name": "New Orleans", "lat": 29.9511, "lon": -90.0715, "state": "LA"},
    {"name": "Portland", "lat": 43.6591, "lon": -70.2568, "state": "ME"},
    {"name": "Baltimore", "lat": 39.2904, "lon": -76.6122, "state": "MD"},
    {"name": "Worcester", "lat": 42.2626, "lon": -71.8023, "state": "MA"},
    {"name": "Grand Rapids", "lat": 42.9634, "lon": -85.6681, "state": "MI"},
    {"name": "St. Paul", "lat": 44.9537, "lon": -93.0900, "state": "MN"},
    {"name": "Jackson", "lat": 32.2988, "lon": -90.1848, "state": "MS"},
    {"name": "Kansas City", "lat": 39.0997, "lon": -94.5786, "state": "MO"},
    {"name": "Billings", "lat": 45.7833, "lon": -108.5007, "state": "MT"},
    {"name": "Omaha", "lat": 41.2565, "lon": -95.9345, "state": "NE"},
    {"name": "Reno", "lat": 39.5296, "lon": -119.8138, "state": "NV"},
    {"name": "Manchester", "lat": 42.9956, "lon": -71.4548, "state": "NH"},
    {"name": "Newark", "lat": 40.7357, "lon": -74.1724, "state": "NJ"},
    {"name": "Albuquerque", "lat": 35.0844, "lon": -106.6504, "state": "NM"},
    {"name": "Buffalo", "lat": 42.8864, "lon": -78.8784, "state": "NY"},
    {"name": "Charlotte", "lat": 35.2271, "lon": -80.8431, "state": "NC"},
    {"name": "Fargo", "lat": 46.8772, "lon": -96.7898, "state": "ND"},
    {"name": "Columbus", "lat": 39.9612, "lon": -82.9988, "state": "OH"},
    {"name": "Oklahoma City", "lat": 35.4676, "lon": -97.5164, "state": "OK"},
    {"name": "Eugene", "lat": 44.0521, "lon": -123.0868, "state": "OR"},
    {"name": "Pittsburgh", "lat": 40.4406, "lon": -79.9959, "state": "PA"},
    {"name": "Providence", "lat": 41.8240, "lon": -71.4128, "state": "RI"},
    {"name": "Charleston", "lat": 32.7765, "lon": -79.9311, "state": "SC"},
    {"name": "Sioux Falls", "lat": 43.5460, "lon": -96.7313, "state": "SD"},
    {"name": "Nashville", "lat": 36.1627, "lon": -86.7816, "state": "TN"},
    {"name": "El Paso", "lat": 31.7619, "lon": -106.4850, "state": "TX"},
    {"name": "Salt Lake City", "lat": 40.7608, "lon": -111.8910, "state": "UT"},
    {"name": "Burlington", "lat": 44.4759, "lon": -73.2121, "state": "VT"},
    {"name": "Virginia Beach", "lat": 36.8529, "lon": -76.0852, "state": "VA"},
    {"name": "Spokane", "lat": 47.6588, "lon": -117.4260, "state": "WA"},
    {"name": "Charleston", "lat": 38.3498, "lon": -81.6326, "state": "WV"},
    {"name": "Milwaukee", "lat": 43.0389, "lon": -87.9065, "state": "WI"},
    {"name": "Cheyenne", "lat": 41.1400, "lon": -104.8202, "state": "WY"}
]

def generate_ipv6_address():
    """Generate a realistic IPv6 address in various formats"""
    # Different IPv6 address types for realism
    address_types = [
        # Global unicast (2000::/3) - Most common
        lambda: f"2{random.randint(0, 3)}{random.randint(0, 15):x}{random.randint(0, 15):x}:" + 
                ":".join(f"{random.randint(0, 65535):x}" for _ in range(7)),
        
        # Compressed format (with ::)
        lambda: f"2{random.randint(0, 3)}{random.randint(0, 15):x}{random.randint(0, 15):x}:" +
                ":".join(f"{random.randint(0, 65535):x}" for _ in range(2)) + "::" +
                ":".join(f"{random.randint(0, 65535):x}" for _ in range(2)),
        
        # Link-local (fe80::/10)
        lambda: "fe80::" + ":".join(f"{random.randint(0, 65535):x}" for _ in range(4)),
        
        # Unique local (fc00::/7)
        lambda: f"fd{random.randint(0, 15):x}{random.randint(0, 15):x}:" +
                ":".join(f"{random.randint(0, 65535):x}" for _ in range(7))
    ]
    
    # 70% global unicast, 10% compressed, 10% link-local, 10% unique local
    weights = [0.7, 0.1, 0.1, 0.1]
    address_gen = random.choices(address_types, weights=weights)[0]
    return address_gen()

def get_ip_location(ip):
    """Get location for an IP address using free API (supports IPv4 and IPv6)"""
    if ip in ip_cache:
        return ip_cache[ip]
    
    try:
        time.sleep(IP_GEOLOCATION_DELAY)
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,lat,lon,isp,org", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                location = {
                    "name": data.get('city', 'Unknown'),
                    "country": data.get('country', 'Unknown'),
                    "lat": data.get('lat', 0),
                    "lon": data.get('lon', 0),
                    "isp": data.get('isp', 'Unknown'),
                    "org": data.get('org', 'Unknown')
                }
                ip_cache[ip] = location
                return location
    except Exception as e:
        print(f"✗ Error getting location for {ip}: {e}")
    
    return None

def fetch_real_threat_data():
    """Fetch real threat data from multiple public blocklists"""
    global threat_ips_cache, last_fetch_time
    
    current_time = time.time()
    if threat_ips_cache and (current_time - last_fetch_time) < CACHE_DURATION:
        return threat_ips_cache
    
    all_ips = []
    
    sources = [
        ("https://lists.blocklist.de/lists/ssh.txt", "SSH"),
        ("https://lists.blocklist.de/lists/apache.txt", "Apache"),
        ("https://lists.blocklist.de/lists/mail.txt", "Mail"),
        ("https://lists.blocklist.de/lists/ftp.txt", "FTP"),
        ("https://lists.blocklist.de/lists/bruteforcelogin.txt", "Brute Force"),
        ("https://lists.blocklist.de/lists/strongips.txt", "Strong IPs"),
        ("https://lists.blocklist.de/lists/ircbot.txt", "IRC Bot"),
        ("https://lists.blocklist.de/lists/bots.txt", "Bots")
    ]
    
    for url, name in sources:
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                ips = [line.strip() for line in response.text.split('\n') if line.strip() and not line.startswith('#')]
                all_ips.extend(ips)
        except Exception:
            pass
    
    threat_ips_cache = list(set(all_ips))
    last_fetch_time = current_time
    return threat_ips_cache

def create_us_attack():
    """Create attack involving US cities to ensure all 50 states get representation"""
    # Choose random US cities for origin and destination
    origin_city = random.choice(US_CITIES)
    dest_city = random.choice([c for c in US_CITIES if c != origin_city])
    
    origin = {
        "name": origin_city['name'],
        "country": "United States",
        "lat": origin_city['lat'],
        "lon": origin_city['lon']
    }
    
    destination = {
        "name": dest_city['name'],
        "country": "United States",
        "lat": dest_city['lat'],
        "lon": dest_city['lon']
    }
    
    attack_types = [
        "SSH Brute Force", "HTTP Flood", "Port Scan", "DDoS Attack", 
        "Network Intrusion", "Apache Attack", "Mail Server Attack", 
        "FTP Brute Force", "SQL Injection Attempt"
    ]
    severity_levels = ["Low", "Medium", "High", "Critical"]
    severity_weights = [0.1, 0.2, 0.4, 0.3]
    
    # 40% of US attacks use IPv6, 60% use IPv4
    use_ipv6 = random.random() < 0.4
    
    if use_ipv6:
        source_ip = generate_ipv6_address()
        destination_ip = generate_ipv6_address()
        ip_version = "IPv6"
    else:
        source_ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
        destination_ip = f"10.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        ip_version = "IPv4"
    
    attack = {
        "id": len(recent_attacks) + 1,
        "timestamp": datetime.now().isoformat(),
        "origin": origin,
        "destination": destination,
        "attack_type": random.choice(attack_types),
        "severity": random.choices(severity_levels, weights=severity_weights)[0],
        "packets": random.randint(5000, 500000),
        "bandwidth": f"{random.randint(10, 1000)} Mbps",
        "duration": f"{random.randint(10, 3600)} seconds",
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "ip_version": ip_version,
        "real_data": False
    }
    
    return attack

def create_real_attack():
    """Create attack data from real threat intelligence with geographic balancing"""
    threat_ips = fetch_real_threat_data()
    
    if len(threat_ips) < 2:
        return None
    
    # Try to create geographically diverse attacks (70% of the time)
    # This helps balance global representation
    max_attempts = 15  # Try multiple IPs to find good geographic diversity
    
    if random.random() < 0.7:
        # Attempt to find diverse source/destination
        for _ in range(max_attempts):
            source_ip = random.choice(threat_ips)
            destination_ip = random.choice([ip for ip in threat_ips if ip != source_ip])
            
            # Quick check: try to avoid same /16 subnet for more diversity
            source_subnet = source_ip.split('.')[:2]
            dest_subnet = destination_ip.split('.')[:2]
            if source_subnet != dest_subnet:
                break
    else:
        # 30% of time, allow any pairing (including same region)
        source_ip = random.choice(threat_ips)
        destination_ip = random.choice([ip for ip in threat_ips if ip != source_ip])
    
    origin = get_ip_location(source_ip)
    destination = get_ip_location(destination_ip)
    
    if not origin or not destination:
        return None
    
    attack_types = [
        "SSH Brute Force", "HTTP Flood", "Port Scan", "DDoS Attack", 
        "Network Intrusion", "Apache Attack", "Mail Server Attack", 
        "FTP Brute Force", "SQL Injection Attempt"
    ]
    severity_levels = ["Low", "Medium", "High", "Critical"]
    severity_weights = [0.1, 0.2, 0.4, 0.3]
    
    attack = {
        "id": len(recent_attacks) + 1,
        "timestamp": datetime.now().isoformat(),
        "origin": origin,
        "destination": destination,
        "attack_type": random.choice(attack_types),
        "severity": random.choices(severity_levels, weights=severity_weights)[0],
        "packets": random.randint(5000, 500000),
        "bandwidth": f"{random.randint(10, 1000)} Mbps",
        "duration": f"{random.randint(10, 3600)} seconds",
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "ip_version": "IPv4",
        "real_data": True
    }
    
    return attack

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/attacks')
def get_attacks():
    """Get all recent attacks"""
    return jsonify(recent_attacks)

@app.route('/api/generate_attack')
def generate_new_attack():
    """Generate a new real attack"""
    attack = create_real_attack()
    
    if attack:
        recent_attacks.append(attack)
        
        # Save to database
        db.save_attack(attack)
        
        if len(recent_attacks) > MAX_ATTACKS:
            recent_attacks.pop(0)
        
        return jsonify(attack)
    else:
        return jsonify({"error": "Could not generate attack"}), 500

@app.route('/api/stats')
def get_stats():
    """Get attack statistics from database"""
    return jsonify(db.get_stats())

@app.route('/api/filter')
def filter_attacks():
    """Filter attacks by country, severity, or type"""
    country = request.args.get('country')
    severity = request.args.get('severity')
    attack_type = request.args.get('type')
    # SECURITY FIX: Validate limit parameter
    limit = validate_positive_int(request.args.get('limit'), default=100, max_value=1000)
    
    attacks = db.get_filtered_attacks(country, severity, attack_type, limit)
    return jsonify(attacks)

@app.route('/api/export/json')
@limiter.limit("10 per hour")  # RATE LIMIT: Restrictive for export operations
def export_json():
    """Export attacks as JSON"""
    # SECURITY FIX: Validate limit parameter
    limit = validate_positive_int(request.args.get('limit'), default=100, max_value=1000)
    attacks = db.export_to_dict(limit)
    
    return jsonify(attacks)

@app.route('/api/export/csv')
@limiter.limit("10 per hour")  # RATE LIMIT: Restrictive for export operations
def export_csv():
    """Export attacks as CSV"""
    # SECURITY FIX: Validate limit parameter
    limit = validate_positive_int(request.args.get('limit'), default=100, max_value=1000)
    attacks = db.export_to_dict(limit)
    
    # Create CSV in memory
    output = io.StringIO()
    if attacks:
        fieldnames = attacks[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(attacks)
    
    # Create response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'ddos_attacks_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/api/countries')
def get_countries():
    """Get list of countries for filtering"""
    # RESOURCE FIX: Use context manager for database connection
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT source_country FROM attacks UNION SELECT DISTINCT dest_country FROM attacks')
        countries = sorted([row[0] for row in cursor.fetchall() if row[0]])
    
    return jsonify(countries)

@app.route('/api/trends/frequency')
def get_attack_frequency():
    """Get attack frequency over time with adjustable time range"""
    # SECURITY FIX: Validate time_range parameter
    minutes = validate_time_range(request.args.get('range'))
    
    # Determine grouping based on time range
    if minutes <= 60:
        group_format = '%Y-%m-%d %H:%M'
        interval_label = 'minute'
    elif minutes <= 360:
        group_format = '%Y-%m-%d %H:%M'
        interval_label = '5-minute'
    else:
        group_format = '%Y-%m-%d %H:00'
        interval_label = 'hour'
    
    # RESOURCE FIX: Use context manager for database connection
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                strftime(?, REPLACE(timestamp, 'T', ' ')) as time_bucket,
                COUNT(*) as count
            FROM attacks
            WHERE REPLACE(timestamp, 'T', ' ') >= datetime('now', 'localtime', '-' || ? || ' minutes')
            GROUP BY time_bucket
            ORDER BY time_bucket ASC
        ''', (group_format, str(minutes)))
        results = cursor.fetchall()
    
    # If no results, return empty arrays
    if not results:
        return jsonify({
            'labels': [],
            'data': [],
            'interval': interval_label,
            'range_minutes': minutes
        })
    
    # Format labels for display
    if minutes <= 360:
        # Show only time for shorter ranges
        labels = [row[0].split(' ')[1] if ' ' in row[0] else row[0] for row in results]
    else:
        # Show date and time for longer ranges
        labels = [row[0].replace(' ', '\n') for row in results]
    
    return jsonify({
        'labels': labels,
        'data': [row[1] for row in results],
        'interval': interval_label,
        'range_minutes': minutes
    })

@app.route('/api/trends/severity')
def get_severity_trend():
    """Get severity distribution"""
    stats = db.get_stats()
    severity_data = stats['by_severity']
    
    return jsonify({
        'labels': list(severity_data.keys()),
        'data': list(severity_data.values())
    })

@app.route('/api/trends/types')
def get_types_trend():
    """Get attack types distribution"""
    stats = db.get_stats()
    types_data = stats['by_type']
    
    return jsonify({
        'labels': list(types_data.keys()),
        'data': list(types_data.values())
    })

@app.route('/api/threat/score')
def get_threat_score():
    """Get current threat score"""
    return jsonify(calculate_threat_score())

@app.route('/api/threat/history')
def get_threat_history():
    """Get threat score history"""
    return jsonify({
        'history': list(threat_score_history)[-30:],  # Convert deque to list, last 30 readings
        'current': calculate_threat_score()
    })

@app.route('/api/threat/countries')
def get_country_threats():
    """Get per-country threat scores"""
    return jsonify(calculate_country_threat_scores())

# ============================================================================
# OSINT / SHODAN API ENDPOINTS
# ============================================================================

@app.route('/api/osint/ip/<ip_address>')
@limiter.limit("20 per hour")  # RATE LIMIT: Shodan queries are expensive
def get_ip_intelligence(ip_address):
    """Get OSINT intelligence for an IP address using Shodan.
    
    Returns detailed information about the IP including:
    - Organization and ISP
    - Open ports and services
    - Known vulnerabilities
    - Device information
    """
    if not osint_service or not osint_service.is_shodan_available():
        return jsonify({
            "error": "Shodan OSINT integration not available",
            "message": "Please configure SHODAN_API_KEY in config.yaml or environment variables"
        }), 503
    
    try:
        enriched_data = osint_service.enrich_ip_data(ip_address)
        
        if not enriched_data.get('enriched'):
            return jsonify({
                "ip": ip_address,
                "enriched": False,
                "message": "No Shodan data available for this IP"
            }), 404
        
        return jsonify(enriched_data)
        
    except Exception as e:
        logger.error(f"Error enriching IP {ip_address}: {e}")
        return jsonify({
            "error": "Failed to retrieve IP intelligence",
            "message": str(e)
        }), 500

@app.route('/api/osint/search')
@limiter.limit("10 per hour")  # RATE LIMIT: Very restrictive for search queries
def search_threats():
    """Search for potential threats using Shodan.
    
    Query parameters:
    - q: Shodan search query (e.g., "port:22 country:CN")
    
    Example queries:
    - port:22 country:CN (SSH servers in China)
    - product:"Apache httpd" country:RU (Apache servers in Russia)
    - vuln:CVE-2021-44228 (Log4j vulnerability)
    """
    if not osint_service or not osint_service.is_shodan_available():
        return jsonify({
            "error": "Shodan OSINT integration not available",
            "message": "Please configure SHODAN_API_KEY in config.yaml or environment variables"
        }), 503
    
    query = request.args.get('q')
    if not query:
        return jsonify({
            "error": "Missing required parameter",
            "message": "Please provide 'q' parameter with Shodan search query"
        }), 400
    
    try:
        results = osint_service.search_threats(query)
        
        if results is None:
            return jsonify({
                "error": "Search failed",
                "message": "Shodan search request failed"
            }), 500
        
        return jsonify({
            "query": query,
            "result_count": len(results),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error searching Shodan: {e}")
        return jsonify({
            "error": "Search failed",
            "message": str(e)
        }), 500

@app.route('/api/osint/status')
def get_osint_status():
    """Get OSINT integration status and Shodan API information."""
    status = {
        "osint_enabled": osint_service is not None,
        "shodan_available": False,
        "shodan_credits": None
    }
    
    if osint_service and osint_service.is_shodan_available():
        status["shodan_available"] = True
        
        # Get API usage info
        api_info = osint_service.get_shodan_api_status()
        if api_info:
            status["shodan_credits"] = {
                "query_credits": api_info.get("query_credits", 0),
                "scan_credits": api_info.get("scan_credits", 0),
                "plan": api_info.get("plan", "Unknown")
            }
    
    return jsonify(status)

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers.
    
    Returns system health status including database connectivity,
    cache status, and application uptime.
    """
    try:
        # Check database connectivity
        db_status = 'ok'
        try:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM attacks LIMIT 1')
                cursor.fetchone()
        except Exception as e:
            db_status = f'error: {str(e)}'
            logger.error(f"Database health check failed: {e}")
        
        # Check cache status
        cache_status = 'ok' if ip_cache or threat_ips_cache else 'empty'
        
        # Calculate uptime (would need to track start time in production)
        health_data = {
            'status': 'healthy' if db_status == 'ok' else 'degraded',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': {
                'database': db_status,
                'cache': cache_status,
                'recent_attacks': len(recent_attacks),
                'threat_score_history': len(threat_score_history)
            },
            'version': '1.0.0'
        }
        
        status_code = 200 if health_data['status'] == 'healthy' else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e)
        }), 503

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket client connection.
    
    Emits connection confirmation and initial data to the newly connected client.
    Logs connection for monitoring purposes.
    """
    try:
        client_id = request.sid if hasattr(request, 'sid') else 'unknown'
        print(f"🔌 WebSocket client connected: {client_id}")
        
        # Send connection confirmation
        emit('connection_response', {
            'status': 'connected',
            'timestamp': datetime.now().isoformat(),
            'message': 'Successfully connected to attack tracker'
        })
        
        # Optionally send initial data to newly connected client
        if recent_attacks:
            emit('initial_attacks', recent_attacks[-10:])  # Send last 10 attacks
            
    except Exception as e:
        print(f"❌ Error in handle_connect: {e}")
        emit('connection_response', {
            'status': 'error',
            'message': 'Connection established with errors'
        })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket client disconnection.
    
    Logs disconnection for monitoring and cleanup purposes.
    Can be extended to clean up client-specific resources if needed.
    """
    try:
        client_id = request.sid if hasattr(request, 'sid') else 'unknown'
        print(f"🔌 WebSocket client disconnected: {client_id}")
        
        # Add any cleanup logic here if needed (e.g., removing from active clients list)
        
    except Exception as e:
        print(f"⚠️ Error in handle_disconnect: {e}")

def _get_intensity_emoji(intensity):
    """Get emoji representation based on attack intensity level.
    
    Maps intensity values to visual emoji indicators for better UX.
    Uses a tiered system to represent different threat levels.
    
    Args:
        intensity (float): Attack intensity value, typically range 0.3-2.0
            - > 1.5: Critical intensity (🔥)
            - > 1.2: High intensity (⚡)
            - <= 1.2: Normal intensity (📡)
        
    Returns:
        str: Single emoji character representing the intensity level
        
    Examples:
        >>> _get_intensity_emoji(1.8)
        '🔥'
        >>> _get_intensity_emoji(1.3)
        '⚡'
        >>> _get_intensity_emoji(0.5)
        '📡'
    """
    # Define intensity thresholds as constants for maintainability
    CRITICAL_THRESHOLD = 1.5
    HIGH_THRESHOLD = 1.2
    
    if intensity > CRITICAL_THRESHOLD:
        return "🔥"  # Critical intensity
    elif intensity > HIGH_THRESHOLD:
        return "⚡"  # High intensity
    else:
        return "📡"  # Normal intensity


def _broadcast_attack(attack, intensity=None):
    """Broadcast attack via WebSocket and persist to database.
    
    This function handles:
    - Adding attack to in-memory recent_attacks list
    - Persisting attack to database
    - Managing recent_attacks size limit (Note: deque with maxlen handles this automatically)
    - Broadcasting attack via WebSocket
    
    Args:
        attack: Dictionary containing attack data
        intensity: Optional float for attack intensity (currently unused)
        
    Note:
        Thread-safe: Uses locks to protect shared state
    """
    try:
        # Thread-safe addition to in-memory list
        with recent_attacks_lock:
            recent_attacks.append(attack)
            # Note: deque with maxlen automatically handles size limit
            # The unnecessary while loop has been removed (Quick Win #1)
        
        # Persist to database (may fail, handle gracefully)
        try:
            db.save_attack(attack)
        except Exception as db_error:
            logger.warning(f"Database save failed for attack {attack.get('id', 'unknown')}: {db_error}")
        
        # Broadcast via WebSocket (may fail if no clients connected)
        try:
            socketio.emit('new_attack', attack)
        except Exception as ws_error:
            logger.debug(f"WebSocket broadcast failed: {ws_error}")
            
    except Exception as e:
        logger.error(f"Error in _broadcast_attack: {e}", exc_info=True)

def _generate_burst_attacks(burst_count):
    """Generate burst attacks"""
    for _ in range(burst_count):
        attack = create_real_attack()
        if attack:
            _broadcast_attack(attack)
        time.sleep(0.3)

def _update_intensity(intensity, trend):
    """Update attack intensity with wave pattern"""
    trend += random.uniform(-0.15, 0.15)
    trend = max(-0.5, min(0.5, trend))
    intensity += trend
    intensity = max(0.3, min(2.0, intensity))
    return intensity, trend

def _calculate_sleep_time(intensity):
    """Calculate variable sleep time based on intensity"""
    base_sleep = 3.0 / intensity
    sleep_variation = random.uniform(-0.8, 0.8)
    return max(1.0, min(5.0, base_sleep + sleep_variation))

# Background threat score tracking
def update_threat_scores_background():
    """Background thread to continuously calculate and store threat scores"""
    while True:
        try:
            calculate_threat_score()
        except Exception:
            pass
        
        # Update every 5 seconds
        time.sleep(5)

# Background attack generation with WebSocket broadcasting
def generate_attacks_background():
    """Background thread to generate and broadcast attacks with dynamic patterns"""
    attack_intensity = 1.0
    intensity_trend = 0.0
    
    while True:
        # Update intensity
        attack_intensity, intensity_trend = _update_intensity(attack_intensity, intensity_trend)
        sleep_time = _calculate_sleep_time(attack_intensity)
        
        # Generate attacks - 30% US attacks, 10% burst, 60% international real threats
        rand = random.random()
        if rand < 0.1:
            _generate_burst_attacks(random.randint(2, 4))
        elif rand < 0.4:
            # Generate US attack (30% of attacks)
            attack = create_us_attack()
            _broadcast_attack(attack, attack_intensity)
        else:
            # Generate international real threat attack
            attack = create_real_attack()
            if attack:
                _broadcast_attack(attack, attack_intensity)
        
        time.sleep(sleep_time)

if __name__ == '__main__':
    print("🚀 DDOS Tracker starting with REAL-TIME threat intelligence...")
    print("📍 Access the application at: http://localhost:5000")
    print("⚠️  Note: Initial loading may take time as IPs are geolocated")
    print("🌐 Data sources: blocklist.de (SSH, Apache, Mail attacks)")
    print("💾 Database: attacks.db (persistent storage enabled)")
    print("⚡ WebSocket support enabled for real-time updates")
    print("📊 Threat scoring system enabled")
    
    # SECURITY FIX: Environment-based debug mode
    is_dev = os.environ.get('FLASK_ENV', 'production') == 'development'
    if is_dev:
        print("⚠️  Running in DEVELOPMENT mode")
    else:
        print("🔒 Running in PRODUCTION mode")
    
    # Start background threat score tracking
    Thread(target=update_threat_scores_background, daemon=True).start()
    
    # Pre-fetch threat data and start background attack generation
    def prefetch_and_start():
        time.sleep(2)
        fetch_real_threat_data()
        generate_attacks_background()
    
    Thread(target=prefetch_and_start, daemon=True).start()
    
    # Run with environment-appropriate settings
    socketio.run(app, debug=is_dev, port=5000, allow_unsafe_werkzeug=is_dev)
