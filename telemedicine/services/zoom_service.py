# telemedicine/services/zoom_service.py
import time
import jwt
import requests
import random
import string
from django.conf import settings
from datetime import datetime, timedelta

class ZoomService:
    """Service for creating and managing Zoom meetings for telehealth consultations"""

    def __init__(self):
        self.api_key = settings.ZOOM_API_KEY
        self.api_secret = settings.ZOOM_API_SECRET
        self.base_url = 'https://api.zoom.us/v2'
    
    def generate_token(self):
        """
        Generate a JWT token for Zoom API authentication
        
        Returns:
            str: JWT token for Zoom API
        """
        token = jwt.encode(
            {
                'iss': self.api_key,
                'exp': int(time.time() + 3600)  # Token expires in 1 hour
            },
            self.api_secret,
            algorithm='HS256'
        )
        
        # Handle different return types between PyJWT versions
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token
    
    def create_meeting(self, topic, start_time, duration_minutes, provider_email):
        """
        Create a Zoom meeting for a consultation
        
        Args:
            topic (str): Meeting topic/title
            start_time (datetime or str): Start time of the meeting
            duration_minutes (int): Duration of the meeting in minutes
            provider_email (str): Email of the healthcare provider
            
        Returns:
            dict: Zoom meeting details
            
        Raises:
            Exception: If meeting creation fails
        """
        headers = {
            'Authorization': f'Bearer {self.generate_token()}',
            'Content-Type': 'application/json'
        }
        
        # Format start time for Zoom API (YYYY-MM-DDThh:mm:ss)
        if isinstance(start_time, datetime):
            start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            start_time_str = start_time
            
        data = {
            'topic': topic,
            'type': 2,  # Scheduled meeting
            'start_time': start_time_str,
            'duration': duration_minutes,
            'timezone': 'UTC',
            'password': self._generate_password(),  # Generate a random password
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': False,
                'mute_upon_entry': True,
                'waiting_room': True,
                'meeting_authentication': True,
                'encryption_type': 'enhanced',  # For HIPAA compliance
                'audio': 'both',
                'auto_recording': 'none'
            },
            'schedule_for': provider_email  # Schedule on behalf of the provider
        }
        
        response = requests.post(f'{self.base_url}/users/{provider_email}/meetings', 
                                headers=headers, json=data)
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create Zoom meeting: {response.text}")
    
    def update_meeting(self, meeting_id, topic=None, start_time=None, duration_minutes=None):
        """
        Update an existing Zoom meeting
        
        Args:
            meeting_id (str): The Zoom meeting ID
            topic (str, optional): New meeting topic
            start_time (datetime or str, optional): New start time
            duration_minutes (int, optional): New duration
            
        Returns:
            bool: True if update was successful
            
        Raises:
            Exception: If meeting update fails
        """
        headers = {
            'Authorization': f'Bearer {self.generate_token()}',
            'Content-Type': 'application/json'
        }
        
        data = {}
        if topic:
            data['topic'] = topic
            
        if start_time:
            # Format start time for Zoom API
            if isinstance(start_time, datetime):
                start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                start_time_str = start_time
            data['start_time'] = start_time_str
            
        if duration_minutes:
            data['duration'] = duration_minutes
        
        response = requests.patch(f'{self.base_url}/meetings/{meeting_id}', 
                                headers=headers, json=data)
        
        if response.status_code == 204:
            return True
        else:
            raise Exception(f"Failed to update Zoom meeting: {response.text}")
    
    def delete_meeting(self, meeting_id):
        """
        Delete a Zoom meeting
        
        Args:
            meeting_id (str): The Zoom meeting ID
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            Exception: If meeting deletion fails
        """
        headers = {
            'Authorization': f'Bearer {self.generate_token()}'
        }
        
        response = requests.delete(f'{self.base_url}/meetings/{meeting_id}', 
                                headers=headers)
        
        if response.status_code == 204:
            return True
        else:
            raise Exception(f"Failed to delete Zoom meeting: {response.text}")
    
    def get_meeting(self, meeting_id):
        """
        Get details of a Zoom meeting
        
        Args:
            meeting_id (str): The Zoom meeting ID
            
        Returns:
            dict: Meeting details
            
        Raises:
            Exception: If getting meeting details fails
        """
        headers = {
            'Authorization': f'Bearer {self.generate_token()}'
        }
        
        response = requests.get(f'{self.base_url}/meetings/{meeting_id}', 
                              headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get Zoom meeting: {response.text}")
    
    def _generate_password(self, length=10):
        """
        Generate a random password for Zoom meetings
        
        Args:
            length (int, optional): Length of the password. Defaults to 10.
            
        Returns:
            str: Random password
        """
        chars = string.ascii_letters + string.digits + '!@#$%^&*()'
        return ''.join(random.choice(chars) for _ in range(length))
