"""Type definitions for DDOS Tracker application.

This module provides complete type hints for all data structures
used throughout the application, ensuring type safety and better IDE support.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime


# Geographic Location Types
class Location(TypedDict):
    """Geographic location information.
    
    Attributes:
        name: City or location name
        country: Country name
        lat: Latitude coordinate
        lon: Longitude coordinate
        isp: Internet Service Provider (optional)
        org: Organization name (optional)
    """
    name: str
    country: str
    lat: float
    lon: float
    isp: Optional[str]
    org: Optional[str]


# Attack Severity and Type Literals
AttackSeverity = Literal["Low", "Medium", "High", "Critical"]
AttackType = Literal[
    "SSH Brute Force",
    "HTTP Flood",
    "Port Scan",
    "DDoS Attack",
    "Network Intrusion",
    "Apache Attack",
    "Mail Server Attack",
    "FTP Brute Force",
    "SQL Injection Attempt"
]
IPVersion = Literal["IPv4", "IPv6"]


# Attack Data Structure
class Attack(TypedDict):
    """Complete attack data structure.
    
    Attributes:
        id: Unique attack identifier
        timestamp: ISO format timestamp
        origin: Source location
        destination: Target location
        attack_type: Type of attack
        severity: Attack severity level
        packets: Number of packets
        bandwidth: Bandwidth usage (e.g., "500 Mbps")
        duration: Attack duration (e.g., "120 seconds")
        source_ip: Source IP address
        destination_ip: Destination IP address
        ip_version: IP protocol version
        real_data: Whether from real threat intelligence
    """
    id: int
    timestamp: str
    origin: Location
    destination: Location
    attack_type: AttackType
    severity: AttackSeverity
    packets: int
    bandwidth: str
    duration: str
    source_ip: str
    destination_ip: str
    ip_version: IPVersion
    real_data: bool


# Threat Scoring Types
ThreatLevel = Literal["Low", "Medium", "High", "Critical"]
ThreatTrend = Literal["stable", "escalating", "de-escalating"]


class ThreatScoreFactors(TypedDict):
    """Threat score component factors.
    
    Attributes:
        frequency: Attack frequency score (0-30)
        severity: Severity distribution score (0-40)
        diversity: Attack type diversity score (0-15)
        concentration: Geographic concentration score (0-15)
    """
    frequency: float
    severity: float
    diversity: float
    concentration: float


class ThreatScoreResult(TypedDict):
    """Complete threat score calculation result.
    
    Attributes:
        score: Overall threat score (0-100)
        level: Threat classification level
        trend: Score trend direction
        factors: Individual factor scores
        timestamp: Calculation timestamp (ISO format)
    """
    score: int
    level: ThreatLevel
    trend: ThreatTrend
    factors: ThreatScoreFactors
    timestamp: str


# Country Threat Score
class CountryThreatScore(TypedDict):
    """Per-country threat score summary.
    
    Attributes:
        country: Country name
        score: Threat score for this country (0-100)
        attack_count: Total number of attacks
        critical_count: Number of critical attacks
    """
    country: str
    score: int
    attack_count: int
    critical_count: int


# Database Statistics Types
class StatsByType(TypedDict):
    """Attack statistics grouped by type."""
    pass  # Keys are attack types, values are counts


class StatsBySeverity(TypedDict):
    """Attack statistics grouped by severity."""
    pass  # Keys are severity levels, values are counts


class DatabaseStats(TypedDict):
    """Complete database statistics.
    
    Attributes:
        total: Total number of attacks
        by_type: Attack counts by type
        by_severity: Attack counts by severity
        countries: Unique countries involved
    """
    total: int
    by_type: Dict[str, int]
    by_severity: Dict[str, int]
    countries: List[str]


# API Response Types
class ErrorResponse(TypedDict):
    """Standard error response.
    
    Attributes:
        error: Error message
        status: HTTP status code (optional)
    """
    error: str
    status: Optional[int]


class SuccessResponse(TypedDict):
    """Standard success response.
    
    Attributes:
        message: Success message
        data: Response data (optional)
    """
    message: str
    data: Optional[Any]


# Frequency Trend Data
class FrequencyTrendData(TypedDict):
    """Attack frequency trend data.
    
    Attributes:
        labels: Time labels for data points
        data: Attack counts per time period
        interval: Time interval type (e.g., 'minute', 'hour')
        range_minutes: Time range in minutes
    """
    labels: List[str]
    data: List[int]
    interval: str
    range_minutes: int


# Chart Data Types
class ChartData(TypedDict):
    """Generic chart data structure.
    
    Attributes:
        labels: Data point labels
        data: Data point values
    """
    labels: List[str]
    data: List[int]


# WebSocket Message Types
class ConnectionResponse(TypedDict):
    """WebSocket connection response.
    
    Attributes:
        status: Connection status
        timestamp: Connection timestamp
        message: Status message
    """
    status: str
    timestamp: str
    message: str


# US Cities Type
class USCity(TypedDict):
    """US city location data.
    
    Attributes:
        name: City name
        lat: Latitude
        lon: Longitude
        state: Two-letter state code
    """
    name: str
    lat: float
    lon: float
    state: str


# Configuration Types (for type hints in config usage)
class AppConfig(TypedDict):
    """Application configuration section."""
    secret_key: Optional[str]
    debug: bool
    port: int
    host: str


class SecurityConfig(TypedDict):
    """Security configuration section."""
    cors_origins: List[str]
    rate_limit: Dict[str, Any]


class ThreatScoringConfig(TypedDict):
    """Threat scoring configuration section."""
    score_precision: int
    analysis_window_seconds: int
    update_interval: int
    thresholds: Dict[str, int]
    trend_detection: Dict[str, int]


# Export these for use in other modules
__all__ = [
    # Location & Attack Types
    'Location',
    'Attack',
    'AttackSeverity',
    'AttackType',
    'IPVersion',
    
    # Threat Score Types
    'ThreatLevel',
    'ThreatTrend',
    'ThreatScoreFactors',
    'ThreatScoreResult',
    'CountryThreatScore',
    
    # Database Types
    'DatabaseStats',
    'StatsByType',
    'StatsBySeverity',
    
    # API Response Types
    'ErrorResponse',
    'SuccessResponse',
    'FrequencyTrendData',
    'ChartData',
    
    # WebSocket Types
    'ConnectionResponse',
    
    # Other Types
    'USCity',
    'AppConfig',
    'SecurityConfig',
    'ThreatScoringConfig',
]
