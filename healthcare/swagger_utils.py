# healthcare/swagger_utils.py
"""
Utilities for enhancing Swagger/OpenAPI documentation.
"""
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

def get_medical_record_responses():
    """Define standardized responses for medical record endpoints"""
    return {
        200: openapi.Response(
            description="Success",
            examples={
                "application/json": {
                    "id": 1,
                    "patient": 42,
                    "medical_record_number": "AB12345678",
                    "primary_physician": 5,
                    "date_of_birth": "1980-01-15",
                    "gender": "Female",
                    "blood_type": "O+",
                    "height": 170.5,
                    "weight": 65.3,
                    "created_at": "2023-01-01T10:00:00Z",
                    "updated_at": "2023-01-01T10:00:00Z",
                }
            }
        ),
        401: openapi.Response(
            description="Unauthorized",
            examples={
                "application/json": {
                    "detail": "Authentication credentials were not provided."
                }
            }
        ),
        403: openapi.Response(
            description="Forbidden",
            examples={
                "application/json": {
                    "detail": "You do not have permission to perform this action."
                }
            }
        ),
        404: openapi.Response(
            description="Not Found",
            examples={
                "application/json": {
                    "detail": "Not found."
                }
            }
        )
    }

def document_medical_record_view(view_class):
    """Decorator to document medical record views"""
    list_docs = swagger_auto_schema(
        operation_description="List medical records with filtering options.",
        operation_summary="List medical records",
        manual_parameters=[
            openapi.Parameter(
                'search', 
                openapi.IN_QUERY, 
                description="Search by patient name or MRN", 
                type=openapi.TYPE_STRING
            )
        ],
        responses=get_medical_record_responses()
    )
    
    retrieve_docs = swagger_auto_schema(
        operation_description="Retrieve a single medical record by ID.",
        operation_summary="Retrieve medical record",
        responses=get_medical_record_responses()
    )
    
    create_docs = swagger_auto_schema(
        operation_description="Create a new medical record.",
        operation_summary="Create medical record",
        responses=get_medical_record_responses()
    )
    
    update_docs = swagger_auto_schema(
        operation_description="Update an existing medical record.",
        operation_summary="Update medical record",
        responses=get_medical_record_responses()
    )
    
    partial_update_docs = swagger_auto_schema(
        operation_description="Partially update an existing medical record.",
        operation_summary="Partially update medical record",
        responses=get_medical_record_responses()
    )
    
    destroy_docs = swagger_auto_schema(
        operation_description="Delete a medical record.",
        operation_summary="Delete medical record",
        responses={
            204: openapi.Response(description="No content, record deleted"),
            401: get_medical_record_responses()[401],
            403: get_medical_record_responses()[403],
            404: get_medical_record_responses()[404]
        }
    )
    
    # Apply decorators to view methods
    view_class.list = list_docs(view_class.list)
    view_class.retrieve = retrieve_docs(view_class.retrieve)
    view_class.create = create_docs(view_class.create)
    view_class.update = update_docs(view_class.update)
    view_class.partial_update = partial_update_docs(view_class.partial_update)
    view_class.destroy = destroy_docs(view_class.destroy)
    
    return view_class
