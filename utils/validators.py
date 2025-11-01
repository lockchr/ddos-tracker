"""Input validation utilities for DDOS Tracker.

Provides validation functions for API inputs with proper error handling.
"""

from typing import Optional, Tuple


def validate_positive_int(
    value: Optional[str],
    default: int,
    max_value: int = 10000,
    field_name: str = "value"
) -> Tuple[int, Optional[str]]:
    """Validate and sanitize integer inputs.
    
    Args:
        value: String value to validate
        default: Default value if validation fails
        max_value: Maximum allowed value
        field_name: Name of field for error messages
        
    Returns:
        Tuple of (validated_value, error_message)
        error_message is None if validation succeeds
    """
    try:
        if value is None or value == '':
            return default, None
        
        num = int(value)
        
        if num < 1:
            return default, f"{field_name} must be positive"
        
        if num > max_value:
            return max_value, f"{field_name} capped at maximum {max_value}"
        
        return num, None
        
    except (ValueError, TypeError):
        return default, f"Invalid {field_name}: must be an integer"


def validate_time_range(
    value: Optional[str],
    default: int = 60,
    max_minutes: int = 1440,
    field_name: str = "time_range"
) -> Tuple[int, Optional[str]]:
    """Validate time range parameter.
    
    Args:
        value: String value representing minutes
        default: Default value (60 minutes)
        max_minutes: Maximum time range allowed
        field_name: Name of field for error messages
        
    Returns:
        Tuple of (validated_minutes, error_message)
    """
    try:
        if value is None or value == '':
            return default, None
        
        minutes = int(value)
        
        if minutes < 1:
            return default, f"{field_name} must be at least 1 minute"
        
        if minutes > max_minutes:
            return max_minutes, f"{field_name} capped at {max_minutes} minutes (24 hours)"
        
        return minutes, None
        
    except (ValueError, TypeError):
        return default, f"Invalid {field_name}: must be an integer"


def validate_string_field(
    value: Optional[str],
    field_name: str,
    max_length: int = 100,
    allow_empty: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    """Validate string field.
    
    Args:
        value: String value to validate
        field_name: Name of field for error messages
        max_length: Maximum allowed length
        allow_empty: Whether empty strings are allowed
        
    Returns:
        Tuple of (validated_value, error_message)
    """
    if value is None:
        if allow_empty:
            return None, None
        else:
            return None, f"{field_name} is required"
    
    value = value.strip()
    
    if not value and not allow_empty:
        return None, f"{field_name} cannot be empty"
    
    if len(value) > max_length:
        return value[:max_length], f"{field_name} truncated to {max_length} characters"
    
    return value, None


def validate_enum_field(
    value: Optional[str],
    field_name: str,
    allowed_values: list,
    case_sensitive: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    """Validate enum/choice field.
    
    Args:
        value: String value to validate
        field_name: Name of field for error messages
        allowed_values: List of allowed values
        case_sensitive: Whether comparison is case-sensitive
        
    Returns:
        Tuple of (validated_value, error_message)
    """
    if value is None:
        return None, None
    
    value = value.strip()
    
    if case_sensitive:
        if value in allowed_values:
            return value, None
    else:
        value_lower = value.lower()
        for allowed in allowed_values:
            if value_lower == allowed.lower():
                return allowed, None
    
    return None, f"Invalid {field_name}: must be one of {', '.join(allowed_values)}"
