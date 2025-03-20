"""
Tool functions for interacting with Cal.com calendar functionality.
These functions are used by the LangChain agent to perform calendar operations.
"""

import logging
from typing import Dict, Any, Optional

from langchain_core.tools import tool
from ..services.cal_api_service import CalApiService
from ..utils.date_utils import validate_and_format_datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Cal.com API service
cal_api_service = CalApiService.get_instance()

@tool
def get_available_slots(
    start: str,
    end: str,
    event_type_slug: str,
    time_zone: Optional[str] = "America/Los_Angeles",
) -> Dict[str, Any]:
    """
    Get available time slots for scheduling a meeting within a date range.
    
    Args:
        start: Start time from which to check availability (ISO 8601 format, e.g., '2023-05-24T13:00:00-07:00')
        end: End time until which to check availability (ISO 8601 format, e.g., '2023-05-31T13:00:00-07:00')
        time_zone: Time zone for the slots (default: America/Los_Angeles)
        event_type_slug: The slug of the event type
        
    Returns:
        Dictionary with available slots grouped by date
    """
    # Validate and format the datetime strings
    start_formatted, start_error = validate_and_format_datetime(start, time_zone)
    if start_error:
        return {"error": start_error}
    
    end_formatted, end_error = validate_and_format_datetime(end, time_zone, is_end_time=True)
    if end_error:
        return {"error": end_error}
    
    # Call the service to get available slots
    result = cal_api_service.get_bookable_slots(
        start=start_formatted,
        end=end_formatted,
        event_type_slug=event_type_slug,
        time_zone=time_zone,
    )
    
    return result

@tool
def book_new_appointment(
    event_type_id: int,
    start_time: str,
    attendee_name: str,
    attendee_email: str,
    attendee_timezone: str = "America/Los_Angeles",
    title: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Book a new appointment with the specified details.
    
    Args:
        event_type_id: ID of the event type to book
        start_time: Start time of the event (ISO 8601 format, e.g., '2023-05-24T13:00:00-07:00')
        attendee_name: Full name of the attendee
        attendee_email: Email of the attendee
        attendee_timezone: Timezone of the attendee (default: America/Los_Angeles)
        title: Custom title for the booking (optional)
        description: Description for the booking (optional)
        location: Location for the booking (optional)
        
    Returns:
        Dictionary with booking details or error message
    """
    # Validate the event_type_id
    if not event_type_id or not isinstance(event_type_id, int):
        return {"error": "Invalid event_type_id. Must be a valid integer."}
    
    # Validate and format the start time
    start_formatted, start_error = validate_and_format_datetime(start_time, attendee_timezone)
    if start_error:
        return {"error": start_error}
    
    # Prepare attendee information
    attendee = {
        "name": attendee_name,
        "email": attendee_email,
        "timeZone": attendee_timezone,
    }
    
    # Prepare location if provided
    location_payload = {}
    if location:
        location_payload["location"] = location
        location_payload["type"] = "attendeeDefined"
    else:
        location_payload["location"] = "To be determined"
        location_payload["type"] = "attendeeDefined"
        
    # Prepare metadata for title and description
    metadata = {}
    if title:
        metadata["title"] = title
    if description:
        metadata["description"] = description
    
    # Create the booking
    result = cal_api_service.create_new_booking(
        event_type_id=event_type_id,
        start=start_formatted,
        attendee=attendee,
        location=location_payload,
        metadata=metadata,
    )
    
    return result

@tool
def get_user_bookings(
    attendee_email: Optional[str] = None,
    attendee_name: Optional[str] = None,
    take: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get bookings for a user with optional filtering.
    
    Args:
        attendee_email: Filter bookings by attendee email
        attendee_name: Filter bookings by attendee name
        take: Number of items to return (pagination)
        
    Returns:
        Dictionary with filtered bookings
    """
    # Ensure at least one filter is provided
    if not any([attendee_email, attendee_name]):
        return {
            "error": "At least one filter must be provided (attendee_email, attendee_name, status, after_start, before_end, or event_type_id)"
        }
    
    
    # Get bookings with filters
    result = cal_api_service.get_all_bookings(
        attendee_email=attendee_email,
        attendee_name=attendee_name,
        take=take
    )
    
    return result

@tool
def get_booking_by_uid(booking_uid: str) -> Dict[str, Any]:
    """
    Get a specific booking by its unique identifier.
    
    Args:
        booking_uid: The unique identifier of the booking
        
    Returns:
        Dictionary with booking details
    """
    if not booking_uid:
        return {"error": "Booking UID is required"}
    
    return cal_api_service.get_booking(booking_uid)

@tool
def reschedule_appointment(
    booking_uid: str,
    new_start_time: str,
    time_zone: str = "America/Los_Angeles",
    rescheduled_by_email: Optional[str] = None,
    rescheduling_reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reschedule an existing booking to a new time.
    
    Args:
        booking_uid: The unique identifier of the booking to reschedule
        new_start_time: New start time in ISO 8601 format
        time_zone: Time zone for the new start time (default: America/Los_Angeles)
        rescheduled_by_email: Email of the person who is rescheduling (optional)
        rescheduling_reason: Reason for rescheduling (optional)
        
    Returns:
        Dictionary with updated booking details
    """
    if not booking_uid:
        return {"error": "Booking UID is required"}
    
    # Validate and format the new start time
    start_formatted, start_error = validate_and_format_datetime(new_start_time, time_zone)
    if start_error:
        return {"error": start_error}
    
    return cal_api_service.reschedule_booking(
        booking_uid=booking_uid,
        start=start_formatted,
        rescheduled_by=rescheduled_by_email,
        rescheduling_reason=rescheduling_reason
    )

@tool
def cancel_appointment(
    booking_uid: str,
    cancellation_reason: Optional[str] = None,
    cancel_subsequent_bookings: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Cancel a booking by its unique identifier.
    
    Args:
        booking_uid: The unique identifier of the booking to cancel
        cancellation_reason: Reason for cancelling the booking (optional)
        cancel_subsequent_bookings: For recurring bookings, whether to cancel all future occurrences (optional)
        
    Returns:
        Dictionary with cancellation details
    """
    if not booking_uid:
        return {"error": "Booking UID is required"}
    
    # First check if this is a recurring booking
    booking_info = cal_api_service.get_booking(booking_uid)
    
    # If there was an error getting the booking details
    if "error" in booking_info:
        return booking_info
    
    # If it's a recurring booking and cancel_subsequent_bookings isn't specified,
    # return a special response requiring confirmation
    booking_data = booking_info.get("data", {})
    if booking_data.get("recurringEventId") and cancel_subsequent_bookings is None:
        return {
            "confirmation_required": True,
            "message": "This is a recurring booking. Do you want to cancel just this occurrence or all future occurrences?",
            "booking_details": booking_data,
            "options": [
                {"label": "Just this occurrence", "value": False},
                {"label": "All future occurrences", "value": True}
            ]
        }
    
    # Proceed with cancellation
    return cal_api_service.cancel_booking(
        booking_uid=booking_uid,
        cancellation_reason=cancellation_reason,
        cancel_subsequent_bookings=cancel_subsequent_bookings
    )
    