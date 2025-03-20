"""
Service for interacting with the Cal.com API.
Provides a unified interface for all Cal.com API operations.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
import threading

from ..utils.api_utils import get_api_key, make_api_request

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventType:
    """
    Represents an event type in the Cal.com API.
    """
    def __init__(self, id: int, title: str, slug: str):
        self.id = id
        self.slug = slug
        self.title = title
    
    def __str__(self):
        return f"EventType(id={self.id}, title={self.title}, slug={self.slug})"

    def __repr__(self):
        return self.__str__()


class UserProfile:
    """
    Represents a user's profile in the Cal.com API.
    """
    def __init__(self, id: int, username: str, email: str, time_zone: str):
        self.id = id
        self.username = username
        self.email = email
        self.time_zone = time_zone
    
    def __str__(self):
        return f"UserProfile(id={self.id}, username={self.username}, email={self.email}, time_zone={self.time_zone})"

    def __repr__(self):
        return self.__str__()

class CalApiService:
    """
    Service for interacting with the Cal.com API.
    Implements all Cal.com API operations in a well-organized class.
    Implemented as a singleton to ensure only one instance is created.
    """
    
    # Singleton instance
    _instance = None
    
    # API constants
    API_BASE_URL = "https://api.cal.com/v2"
    API_KEY_ENV_VAR = "CAL_DOT_COM_API_KEY"
    USERNAME_ENV_VAR = "CAL_DOT_COM_USERNAME"
    
    def __new__(cls) -> 'CalApiService':
        """Thread-safe singleton implementation."""
        with threading.Lock():
            if cls._instance is None:
                cls._instance = super(CalApiService, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the Cal.com API service with API key."""
        # Only initialize once
        if getattr(self, '_initialized', False):
            return
        
        self.api_key = get_api_key(self.API_KEY_ENV_VAR)
        self.username = os.environ.get(self.USERNAME_ENV_VAR)
        event_types_result = self.get_all_event_types()
        self.my_profile = self.get_my_profile()
        
        # Store event types if successful, otherwise store empty list
        if isinstance(event_types_result, list):
            self.all_event_types = event_types_result
        else:
            logger.warning("Failed to initialize event types, using empty list")
            self.all_event_types = []
            
        self._initialized = True
        
    def _get_headers(self) -> Dict[str, str]:
        """Get the headers required for Cal.com API requests."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _get_headers_with_api_version(self, api_version: str) -> Dict[str, str]:
        """Get the headers required for Cal.com API requests with a specific API version."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "cal-api-version": api_version
        }
    
    def _check_api_key(self) -> Optional[Dict[str, str]]:
        """Check if the API key is available and return an error dictionary if not."""
        if not self.api_key:
            error_msg = f"{self.API_KEY_ENV_VAR} not found in environment variables"
            logger.error(error_msg)
            return {"error": error_msg}
        return None
    
    def get_bookable_slots(
        self,
        start: str,
        end: str,
        event_type_slug: str,
        time_zone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all bookable slots from Cal.com within a specified date-time range.
        
        Args:
            start: Start time from which available slots should be checked (ISO 8601)
            end: End time until which available slots should be checked (ISO 8601)
            time_zone: Time zone for available slots (defaults to UTC)
            event_type_slug: The slug of the event type
            
        Returns:
            A dictionary containing available slots grouped by date
        """
        # Check API key
        error = self._check_api_key()
        if error:
            return error
        
        # Check required parameters
        if not start or not end:
            error_msg = "Missing required parameters: start and end"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Build query parameters
        params = {
            "start": start,
            "end": end,
            "eventTypeSlug": event_type_slug
        }
        
        if time_zone:
            params["timeZone"] = time_zone
            
        if self.username:
            params["username"] = self.username
        
        # Make API request
        url = f"{self.API_BASE_URL}/slots"
        logger.info(f"Fetching bookable slots from {url}")
        response_data, error_msg = make_api_request(
            method="GET",
            url=url,
            headers=self._get_headers_with_api_version("2024-09-04"),
            params=params,
            action_description="Fetching bookable slots"
        )
        
        return response_data if not error_msg else {"error": error_msg}
    
    def create_new_booking(
        self,
        event_type_id: int,
        start: str,
        attendee: Dict[str, Any],
        length_in_minutes: Optional[int] = None,
        location: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new booking on Cal.com.
        
        Args:
            event_type_id: ID of the event type to book
            start: Start time of the event in ISO format
            attendee: Attendee information (name, email, timeZone required)
            length_in_minutes: Duration of the meeting in minutes
            location: Meeting location details
            metadata: Any metadata associated with the booking
            
        Returns:
            A dictionary containing the booking details if successful
        """
        # Check API key
        error = self._check_api_key()
        if error:
            return error
        
        # Validate required fields
        if not event_type_id or not start or not attendee:
            missing_fields = []
            if not event_type_id:
                missing_fields.append("event_type_id")
            if not start:
                missing_fields.append("start")
            if not attendee:
                missing_fields.append("attendee")
            
            error_msg = f"Missing required parameters: {', '.join(missing_fields)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Validate attendee fields
        required_attendee_fields = ["name", "email", "timeZone"]
        missing_attendee_fields = [field for field in required_attendee_fields if field not in attendee]
        if missing_attendee_fields:
            error_msg = f"Missing required attendee fields: {', '.join(missing_attendee_fields)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Prepare the request payload
        payload = {
            "eventTypeId": event_type_id,
            "start": start,
            "attendee": attendee
        }
        
        # Add optional fields if provided
        if length_in_minutes:
            payload["lengthInMinutes"] = length_in_minutes
        
        if location:
            payload["location"] = location
            
        if metadata:
            payload["metadata"] = metadata
        else:
            payload["metadata"] = {}
            
        # Add source metadata
        payload["metadata"]["source"] = "calchat"
        
        # Make API request
        url = f"{self.API_BASE_URL}/bookings"
        response_data, error_msg = make_api_request(
            method="POST",
            url=url,
            headers=self._get_headers_with_api_version("2024-08-13"),
            json_data=payload,
            action_description="Creating new booking"
        )
        
        return response_data if not error_msg else {"error": error_msg}
    
    def get_all_event_types(self) -> Union[List[EventType], Dict[str, str]]:
        """
        Get all event types from Cal.com.
        
        Returns:
            A list of EventType objects if successful, or an error dictionary if failed
        """
        # Check API key
        error = self._check_api_key()
        if error:
            return error
        
        # Make API request
        url = f"{self.API_BASE_URL}/event-types"
        response_data, error_msg = make_api_request(
            method="GET",
            url=url,
            headers=self._get_headers_with_api_version("2024-06-14"),
            action_description="Fetching event types",
            params={"username": self.username}
        )
        
        # Handle API error
        if error_msg:
            return {"error": error_msg}
        
        # Parse response and convert to EventType objects
        event_types = []
        
        try:
            if response_data.get("status") == "success" and "data" in response_data:
                for event_type_data in response_data["data"]:
                    event_type = EventType(
                        id=event_type_data["id"],
                        title=event_type_data["title"],
                        slug=event_type_data["slug"]
                    )
                    event_types.append(event_type)
                
                logger.info(f"Successfully parsed {len(event_types)} event types")
                return event_types
            else:
                error_msg = "Invalid response format from Cal.com API"
                logger.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error parsing event types: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def get_all_bookings(
        self,
        attendee_email: Optional[str] = None,
        attendee_name: Optional[str] = None,
        take: Optional[int] = None,
        skip: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all bookings from Cal.com with optional filtering.
        
        Args:
            attendee_email: Filter bookings by attendee email
            attendee_name: Filter bookings by attendee name
            take: Number of items to return (pagination)
            skip: Number of items to skip (pagination)
            
        Returns:
            A dictionary containing bookings matching the filter criteria
        """
        # Check API key
        error = self._check_api_key()
        if error:
            return error
        
        # Build query parameters
        params = {}
        
        if attendee_email:
            params["attendeeEmail"] = attendee_email
            
        if attendee_name:
            params["attendeeName"] = attendee_name
            
        if take:
            params["take"] = take
            
        if skip:
            params["skip"] = skip
        
        # Make API request
        url = f"{self.API_BASE_URL}/bookings"
        response_data, error_msg = make_api_request(
            method="GET",
            url=url,
            headers=self._get_headers_with_api_version("2024-08-13"),
            params=params,
            action_description="Fetching bookings"
        )
        
        return response_data if not error_msg else {"error": error_msg}
    
    def get_booking(self, booking_uid: str) -> Dict[str, Any]:
        """
        Get a specific booking from Cal.com by its UID.
        
        Args:
            booking_uid: The unique identifier for the booking
            
        Returns:
            A dictionary containing the booking details
        """
        # Check API key
        error = self._check_api_key()
        if error:
            return error
        
        if not booking_uid:
            error_msg = "Booking UID is required"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Make API request
        url = f"{self.API_BASE_URL}/bookings/{booking_uid}"
        response_data, error_msg = make_api_request(
            method="GET",
            url=url,
            headers=self._get_headers_with_api_version("2024-08-13"),
            action_description=f"Fetching booking with UID: {booking_uid}"
        )
        
        return response_data if not error_msg else {"error": error_msg}
    
    def reschedule_booking(
        self,
        booking_uid: str,
        start: str,
        rescheduled_by: Optional[str] = None,
        rescheduling_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reschedule an existing booking to a new time.
        
        Args:
            booking_uid: The unique identifier of the booking to reschedule
            start: New start time in ISO 8601 format for the booking
            rescheduled_by: Email of the person who is rescheduling
            rescheduling_reason: Reason for rescheduling the booking
            
        Returns:
            A dictionary containing the updated booking details
        """
        # Check API key
        error = self._check_api_key()
        if error:
            return error
        
        # Validate required fields
        if not booking_uid:
            error_msg = "Booking UID is required"
            logger.error(error_msg)
            return {"error": error_msg}
            
        if not start:
            error_msg = "New start time is required"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Prepare the request payload
        payload = {
            "start": start
        }
        
        # Add optional fields if provided
        if rescheduled_by:
            payload["rescheduledBy"] = rescheduled_by
            
        if rescheduling_reason:
            payload["reschedulingReason"] = rescheduling_reason
        
        # Make API request
        url = f"{self.API_BASE_URL}/bookings/{booking_uid}/reschedule"
        response_data, error_msg = make_api_request(
            method="POST",
            url=url,
            headers=self._get_headers_with_api_version("2024-08-13"),
            json_data=payload,
            action_description=f"Rescheduling booking {booking_uid}"
        )
        
        return response_data if not error_msg else {"error": error_msg}
    
    def cancel_booking(
        self,
        booking_uid: str,
        cancellation_reason: Optional[str] = None,
        cancel_subsequent_bookings: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Cancel a booking using the Cal.com API.
        
        Args:
            booking_uid: The unique identifier of the booking to cancel
            cancellation_reason: Reason for cancelling the booking
            cancel_subsequent_bookings: For recurring bookings, if True, cancels 
                                      this recurrence and all future ones
            
        Returns:
            A dictionary containing the updated booking details
        """
        # Check API key
        error = self._check_api_key()
        if error:
            return error
        
        # Validate required fields
        if not booking_uid:
            error_msg = "Booking UID is required"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Prepare the request payload
        payload = {}
        
        # Add optional fields if provided
        if cancellation_reason:
            payload["cancellationReason"] = cancellation_reason
            
        if cancel_subsequent_bookings is not None:
            payload["cancelSubsequentBookings"] = cancel_subsequent_bookings
        
        # Make API request
        url = f"{self.API_BASE_URL}/bookings/{booking_uid}/cancel"
        response_data, error_msg = make_api_request(
            method="POST",
            url=url,
            headers=self._get_headers_with_api_version("2024-08-13"),
            json_data=payload,
            action_description=f"Cancelling booking with UID: {booking_uid}"
        )
        
        return response_data if not error_msg else {"error": error_msg}

    @classmethod
    def get_instance(cls):
        """Get or create the CalApiService instance."""
        if cls._instance is None:
            return cls()
        return cls._instance 
        
    def get_my_profile(self) -> Union[UserProfile, Dict[str, str]]:
        """
        Get the user's profile information from Cal.com API.
        
        Returns:
            A UserProfile object if successful, or an error dictionary if failed
            
        Response format:
        {
            "status": "success",
            "data": {
                "id": 123,
                "username": "<string>",
                "email": "<string>",
                "timeFormat": 123,
                "defaultScheduleId": 123,
                "weekStart": "<string>",
                "timeZone": "<string>",
                "organizationId": 123,
                "organization": {
                    "isPlatform": true,
                    "id": 123
                }
            }
        }
        """
        # Check API key
        error = self._check_api_key()
        if error:
            return error
        
        # Make API request
        url = f"{self.API_BASE_URL}/me"
        response_data, error_msg = make_api_request(
            method="GET",
            url=url,
            headers=self._get_headers(),
            action_description="Fetching user profile"
        )
        
        # Return error if request failed
        if error_msg:
            logger.error(f"Error fetching profile: {error_msg}")
            return {"error": error_msg}
        
        # Parse response into UserProfile object
        try:
            if response_data.get("status") == "success" and "data" in response_data:
                profile_data = response_data["data"]
                user_profile = UserProfile(
                    id=profile_data["id"],
                    username=profile_data["username"],
                    email=profile_data["email"],
                    time_zone=profile_data.get("timeZone", "UTC")  # Default to UTC if not provided
                )
                logger.info(f"Successfully parsed user profile: {user_profile}")
                return user_profile
            else:
                error_msg = "Invalid response format from Cal.com API"
                logger.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error parsing user profile: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg} 