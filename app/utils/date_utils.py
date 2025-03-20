import pytz
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_and_format_datetime(
    datetime_str: str, 
    timezone_str: str = "America/Los_Angeles",
    is_end_time: bool = False
):
    """
    Validate and format a datetime string to ensure it includes timezone information.
    Returns the formatted datetime string and any error message.
    
    Args:
        datetime_str: A datetime string to validate and format
        timezone_str: The timezone to use if not in the datetime string
        is_end_time: Whether this is an end time (for default value purposes)
        
    Returns:
        A tuple of (formatted_datetime_str, error_message)
    """
    try:
        # If empty, set default value
        if not datetime_str:
            # Create a datetime with the specified timezone
            tz = pytz.timezone(timezone_str)
            if is_end_time:
                # Default to a week from now for end time
                dt = datetime.now(tz) + timedelta(days=7)
            else:
                # Default to now for start time
                dt = datetime.now(tz)
            
            # Format in ISO 8601 with timezone offset
            formatted = dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            # Insert the colon in the timezone offset (e.g., -0700 to -07:00)
            formatted = f"{formatted[:-2]}:{formatted[-2:]}"
            
            logger.info(f"Using default {'end' if is_end_time else 'start'} time: {formatted}")
            return formatted, None
            
        # Handle 'Z' UTC timezone marker
        if datetime_str.endswith('Z'):
            # Convert 'Z' to +00:00 format
            datetime_str = datetime_str[:-1] + '+00:00'
        
        # Check if timezone info is already in the string
        if '+' in datetime_str or '-' in datetime_str and datetime_str.rfind('-') > 10:
            # Already has timezone info, validate it
            dt = datetime.fromisoformat(datetime_str)
        else:
            # No timezone info, add the specified timezone
            dt_naive = datetime.fromisoformat(datetime_str)
            tz = pytz.timezone(timezone_str)
            dt = tz.localize(dt_naive)
        
        # Format in ISO 8601 with timezone offset
        formatted = dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        # Insert the colon in the timezone offset (e.g., -0700 to -07:00)
        formatted = f"{formatted[:-2]}:{formatted[-2:]}"
        logger.info(f"Formatted datetime for {datetime_str} {timezone_str}: {formatted}")
        
        return formatted, None
    
    except ValueError as e:
        error_msg = f"Invalid datetime format: {str(e)}. Expected format like '2025-03-21T11:00:00-07:00'"
        logger.error(error_msg)
        return None, error_msg
    except pytz.exceptions.UnknownTimeZoneError as e:
        error_msg = f"Unknown timezone: {str(e)}"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Error processing datetime: {str(e)}"
        logger.error(error_msg)
        return None, error_msg 