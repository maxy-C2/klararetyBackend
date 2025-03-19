from rest_framework import serializers
from .models import WithingsProfile, WithingsMeasurement

class WithingsProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the WithingsProfile model.
    Excludes sensitive token information.
    """
    class Meta:
        model = WithingsProfile
        fields = [
            'id',
            'user',
            # 'access_token',
            # 'refresh_token',
            'token_expires_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

class WithingsMeasurementSerializer(serializers.ModelSerializer):
    """
    Serializer for the WithingsMeasurement model.
    Includes all fields for detailed view of health measurements.
    """
    class Meta:
        model = WithingsMeasurement
        fields = [
            'id',
            'withings_profile',
            'measurement_type',
            'value',
            'unit',
            'measured_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class WithingsMeasurementSummarySerializer(serializers.ModelSerializer):
    """
    Summary serializer for WithingsMeasurement model.
    Provides a condensed view for listing measurements.
    """
    class Meta:
        model = WithingsMeasurement
        fields = [
            'id',
            'measurement_type',
            'value',
            'unit',
            'measured_at',
        ]
        read_only_fields = ['id']
