import logging
import requests
from django.conf import settings
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .models import WithingsProfile
from .serializers import WithingsProfileSerializer

class WithingsConnectView(APIView):
    """
    Initiates the OAuth flow by redirecting the user to Withings' authorization page.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get the Withings authorization URL to begin OAuth flow",
        operation_summary="Get Withings authorization URL",
        tags=["wearables", "withings"],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Authorization URL",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'authorize_url': openapi.Schema(type=openapi.TYPE_STRING, description="URL to redirect user for authorization")
                    }
                )
            ),
            status.HTTP_401_UNAUTHORIZED: "Authentication credentials were not provided"
        }
    )
    def get(self, request):
        client_id = settings.WITHINGS_CLIENT_ID
        redirect_uri = settings.WITHINGS_REDIRECT_URI

        # See Withings docs for correct scopes:
        # https://developer.withings.com/oauth2/#operation/oauth2-authorize
        scope = 'user.metrics'  # example scope for reading user metrics
        state = 'random_state_string'  # you should generate a secure random string

        authorize_url = (
            'https://account.withings.com/oauth2_user/authorize'
            f'?response_type=code'
            f'&client_id={client_id}'
            f'&state={state}'
            f'&scope={scope}'
            f'&redirect_uri={redirect_uri}'
        )

        return Response({"authorize_url": authorize_url})


class WithingsCallbackView(APIView):
    """
    Handles the redirect from Withings: exchanges the code for an access token,
    then stores it in WithingsProfile.
    """
    @swagger_auto_schema(
        operation_description="OAuth callback handler for Withings authorization",
        operation_summary="Handle OAuth callback from Withings",
        tags=["wearables", "withings"],
        manual_parameters=[
            openapi.Parameter(
                name="code",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Authorization code from Withings",
                required=False
            ),
            openapi.Parameter(
                name="error",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Error message if authorization failed",
                required=False
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully connected Withings account",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Successfully linked Withings account!"
                        )
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: "Invalid request parameters",
            status.HTTP_403_FORBIDDEN: "User not authenticated"
        }
    )
    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        if not code:
            return Response({"error": "No code returned"}, status=status.HTTP_400_BAD_REQUEST)

        client_id = settings.WITHINGS_CLIENT_ID
        client_secret = settings.WITHINGS_CLIENT_SECRET
        redirect_uri = settings.WITHINGS_REDIRECT_URI

        # Exchange code for tokens
        token_url = 'https://wbsapi.withings.net/v2/oauth2'
        payload = {
            'action': 'requesttoken',
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }

        r = requests.post(token_url, data=payload)
        data = r.json()

        if r.status_code != 200 or data.get('status') != 0:
            return Response({"error": "Failed to fetch token", "details": data}, status=400)

        body = data.get('body', {})
        access_token = body.get('access_token')
        refresh_token = body.get('refresh_token')
        expires_in = body.get('expires_in')  # typically in seconds

        if not access_token or not refresh_token:
            return Response({"error": "Token fields missing"}, status=400)

        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "User not authenticated"}, status=403)

        # Upsert WithingsProfile
        withings_profile, created = WithingsProfile.objects.get_or_create(user=user)
        withings_profile.access_token = access_token
        withings_profile.refresh_token = refresh_token
        withings_profile.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
        withings_profile.save()

        return Response(
            {"message": "Successfully linked Withings account!"},
            status=status.HTTP_200_OK
        )


class WithingsProfileView(APIView):
    """
    Returns the current user's WithingsProfile details.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get the current user's Withings profile",
        operation_summary="Get Withings profile",
        tags=["wearables", "withings"],
        responses={
            status.HTTP_200_OK: WithingsProfileSerializer,
            status.HTTP_404_NOT_FOUND: "No Withings profile found"
        }
    )
    def get(self, request):
        try:
            profile = request.user.withings_profile
        except WithingsProfile.DoesNotExist:
            return Response({"detail": "No Withings profile found."}, status=404)

        serializer = WithingsProfileSerializer(profile)
        return Response(serializer.data, status=200)


class WithingsFetchDataView(APIView):
    """
    Fetches multiple data types from Withings in a single endpoint call.
    Example: Body composition, activity, sleep, heart data (ECG, SpO2, etc.).
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Fetch health data from Withings APIs",
        operation_summary="Fetch Withings health data",
        tags=["wearables", "withings"],
        manual_parameters=[
            openapi.Parameter(
                name="start_date",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                description="Start date for fetching data (YYYY-MM-DD)",
                required=False
            ),
            openapi.Parameter(
                name="end_date",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                description="End date for fetching data (YYYY-MM-DD)",
                required=False
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully fetched data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'saved_entries_ids': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_INTEGER),
                            description="IDs of saved measurements"
                        ),
                        'metrics_count': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'measurements': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'activity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'sleep': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'heart': openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        )
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: "Invalid parameters or token refresh failed",
            status.HTTP_404_NOT_FOUND: "No Withings profile found" 
        }
    )
    def get(self, request):
        user = request.user
        # Optional date range parameters
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        # Parse date parameters if provided
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                return Response({"error": "Invalid start_date format. Use YYYY-MM-DD"}, status=400)
        
        if end_date_str:
            try:
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                return Response({"error": "Invalid end_date format. Use YYYY-MM-DD"}, status=400)
        
        # Default to last 7 days if no dates provided
        if not start_date:
            end_date = end_date or timezone.now()
            start_date = end_date - timezone.timedelta(days=7)

        # 1) Retrieve user's Withings profile
        try:
            profile = user.withings_profile
        except WithingsProfile.DoesNotExist:
            return Response({"detail": "No Withings profile found."}, status=404)

        # 2) Check token expiration, refresh if needed
        if profile.token_expires_at and timezone.now() >= profile.token_expires_at:
            refreshed = self.refresh_token(profile)
            if not refreshed:
                return Response({"error": "Token refresh failed"}, status=400)

        # 3) Fetch data from each relevant Withings endpoint
        try:
            saved_ids = []
            saved_ids += self.fetch_measurements(profile, start_date, end_date)
            saved_ids += self.fetch_activity(profile, start_date, end_date)
            saved_ids += self.fetch_sleep(profile, start_date, end_date)
            saved_ids += self.fetch_heart_data(profile, start_date, end_date)

            # Return all newly created measurement IDs and summary
            result = {
                "saved_entries_ids": saved_ids,
                "metrics_count": {
                    "measurements": len([id for id in saved_ids if profile.measurements.get(id=id).measurement_type in self.get_measurement_types()]),
                    "activity": len([id for id in saved_ids if profile.measurements.get(id=id).measurement_type in ['steps', 'distance', 'calories']]),
                    "sleep": len([id for id in saved_ids if profile.measurements.get(id=id).measurement_type in ['sleep_state', 'sleep_segment_duration']]),
                    "heart": len([id for id in saved_ids if profile.measurements.get(id=id).measurement_type in ['heart_rate', 'ecg', 'spo2']])
                }
            }
            return Response(result, status=200)
        except requests.RequestException as e:
            return Response({"error": f"API request failed: {str(e)}"}, status=503)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=500)

    # -------------------------------------------------------------------------
    # Fetch Body Measurements with improved date handling
    # -------------------------------------------------------------------------
    def fetch_measurements(self, profile, start_date=None, end_date=None):
        """
        Fetch body measurements (weight, BMI, fat mass, heart rate, BP, etc.)
        from Withings 'measure' endpoint using action=getmeas.
        
        Args:
            profile: The WithingsProfile instance
            start_date: Optional start date for data fetching
            end_date: Optional end date for data fetching
            
        Returns:
            List of saved measurement IDs
        """
        url = "https://wbsapi.withings.net/measure"
        params = {
            "action": "getmeas",
            "access_token": profile.access_token,
        }
        
        # Add date range parameters if provided
        if start_date:
            params["startdate"] = int(start_date.timestamp())
        if end_date:
            params["enddate"] = int(end_date.timestamp())
            
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code != 200 or data.get('status') != 0:
            # Log the error but don't fail the entire request
            logging.error(f"Error fetching Withings measurements: {data}")
            return []

        measuregrps = data.get('body', {}).get('measuregrps', [])
        saved_ids = []

        for group in measuregrps:
            timestamp = group.get('date')
            measured_at = timezone.datetime.fromtimestamp(timestamp, tz=timezone.utc)

            for m in group.get('measures', []):
                measure_type = self.map_measure_type(m.get('type'))
                real_value = m.get('value') * (10 ** m.get('unit'))

                # Use get_or_create to avoid duplicates based on measure type and timestamp
                new_obj, created = profile.measurements.get_or_create(
                    measurement_type=measure_type,
                    measured_at=measured_at,
                    defaults={
                        'value': real_value,
                        'unit': self.map_measure_unit(m.get('type'))
                    }
                )
                
                # Update value if measurement exists but value changed
                if not created and new_obj.value != real_value:
                    new_obj.value = real_value
                    new_obj.save()
                    
                saved_ids.append(new_obj.id)

        return saved_ids

    # Helper method to get all measurement types for filtering
    def get_measurement_types(self):
        """Return all possible measure type codes that can be mapped"""
        return list(self.get_measure_type_mapping().values())
        
    def get_measure_type_mapping(self):
        """
        Provide all possible Withings measure type codes to descriptive strings.
        """
        return {
            1: 'weight',
            4: 'height',
            5: 'fat_free_mass',
            6: 'fat_ratio',
            8: 'fat_mass_weight',
            9: 'diastolic_blood_pressure',
            10: 'systolic_blood_pressure',
            11: 'heart_rate',
            12: 'temperature',
            71: 'spo2',
            73: 'body_temperature',
            76: 'muscle_mass',
            77: 'hydration',
            88: 'bone_mass',
            91: 'pulse_wave_velocity',
            # Add other measure types as needed
        }

    def map_measure_type(self, type_code):
        """Convert Withings measure type codes to a human-readable string."""
        return self.get_measure_type_mapping().get(type_code, f'unknown_{type_code}')
