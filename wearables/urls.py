from django.urls import path
from .views import (
    WithingsConnectView,
    WithingsCallbackView,
    WithingsProfileView,
    WithingsFetchDataView,
)

app_name = 'wearables'

urlpatterns = [
    # Step 1: Return the Withings authorization URL
    path('withings/connect/', 
         WithingsConnectView.as_view(), 
         name='withings-connect'),
    
    # Step 2: Withings will redirect the user here after authorization
    path('withings/callback/', 
         WithingsCallbackView.as_view(), 
         name='withings-callback'),
    
    # Step 3: Retrieve the user's WithingsProfile
    path('withings/profile/', 
         WithingsProfileView.as_view(), 
         name='withings-profile'),
    
    # Step 4: Retrieve the user's health details
    path('withings/fetch-data/', 
         WithingsFetchDataView.as_view(), 
         name='withings-fetch-data'),
]
