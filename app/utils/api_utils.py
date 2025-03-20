import os
import logging
import requests
from typing import Dict, Any, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_api_key(api_key_env_var: str) -> Optional[str]:
    """
    Get an API key from environment variables and validate it.
    
    Args:
        api_key_env_var: The name of the environment variable containing the API key
        
    Returns:
        The API key if found, None otherwise
    """
    api_key = os.environ.get(api_key_env_var)
    if not api_key:
        logger.error(f"Missing API key: {api_key_env_var} environment variable not found")
        return None
    return api_key

def make_api_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    action_description: str = "API request",
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Make an API request with proper error handling.
    
    Args:
        method: HTTP method ('GET', 'POST', etc.)
        url: The URL to make the request to
        headers: HTTP headers for the request
        params: URL parameters for the request (for GET requests)
        json_data: JSON data for the request body (for POST requests)
        action_description: A description of the action for logging
        
    Returns:
        Tuple of (response_data, error_message)
    """
    try:
        logger.info(f"Making {method} request to {url}")
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=json_data)
        else:
            return None, f"Unsupported HTTP method: {method}"
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        response_data = response.json()
        logger.info(f"Successfully completed {action_description}")
        return response_data, None
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error making {action_description}: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_msg += f" - Details: {error_details}"
            except Exception as e:
                error_msg += f" - Status code: {e.response.status_code}"
        
        logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error during {action_description}: {str(e)}"
        logger.error(error_msg)
        return None, error_msg 