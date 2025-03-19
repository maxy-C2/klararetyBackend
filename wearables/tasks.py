from celery import shared_task
from django.utils import timezone
from .models import WithingsProfile
import logging
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

@shared_task
def fetch_withings_data_for_all_users():
    """
    Scheduled task to fetch health data for all users with Withings profiles.
    This task iterates through all active profiles, refreshes tokens if needed,
    and fetches data from Withings APIs.
    """
    logger.info(f"Starting scheduled Withings data fetch at {timezone.now()}")
    
    # Get all profiles with valid tokens
    profiles = WithingsProfile.objects.filter(access_token__isnull=False)
    logger.info(f"Found {profiles.count()} profiles with Withings integration")
    
    success_count = 0
    error_count = 0
    
    for profile in profiles:
        try:
            # Check if token needs refresh
            if profile.token_expires_at and timezone.now() >= profile.token_expires_at:
                logger.info(f"Refreshing token for user {profile.user.username}")
                from .views import WithingsFetchDataView
                view = WithingsFetchDataView()
                refreshed = view.refresh_token(profile)
                
                if not refreshed:
                    logger.error(f"Failed to refresh token for user {profile.user.username}")
                    error_count += 1
                    continue
            
            # Set default date range - last 7 days
            end_date = timezone.now()
            start_date = end_date - timezone.timedelta(days=7)
            
            # Fetch data from each relevant endpoint
            saved_ids = []
            
            # Create an instance of the view to reuse its methods
            from .views import WithingsFetchDataView
            view = WithingsFetchDataView()
            
            # Fetch all data types
            saved_ids += view.fetch_measurements(profile, start_date, end_date)
            saved_ids += view.fetch_activity(profile, start_date, end_date)
            saved_ids += view.fetch_sleep(profile, start_date, end_date)
            saved_ids += view.fetch_heart_data(profile, start_date, end_date)
            
            logger.info(f"Successfully fetched {len(saved_ids)} data points for user {profile.user.username}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error fetching data for user {profile.user.username}: {str(e)}")
            error_count += 1
    
    logger.info(f"Completed Withings data fetch: {success_count} successful, {error_count} failed")
    return f"Processed {profiles.count()} profiles: {success_count} successful, {error_count} failed"

@shared_task
def cleanup_old_withings_data(days_to_keep=90):
    """
    Removes Withings measurements older than the specified days_to_keep parameter.
    This helps manage database size and comply with data retention policies.
    
    Args:
        days_to_keep (int): Number of days of data to retain
    """
    from .models import WithingsMeasurement
    
    cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)
    logger.info(f"Cleaning up Withings measurements older than {cutoff_date}")
    
    # Count records before deletion for logging
    old_records_count = WithingsMeasurement.objects.filter(measured_at__lt=cutoff_date).count()
    
    # Delete old records
    result = WithingsMeasurement.objects.filter(measured_at__lt=cutoff_date).delete()
    
    logger.info(f"Deleted {old_records_count} old Withings measurements")
    return f"Deleted {old_records_count} old measurements"
