# healthcare/schema.py
from rest_framework.schemas.openapi import AutoSchema

class HealthcareSchema(AutoSchema):
    """
    Custom schema class for generating OpenAPI documentation with
    improved descriptions and examples.
    """
    
    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        
        # Add additional metadata based on view and model
        view = self.view
        model_name = getattr(view, 'serializer_class', None)
        if model_name:
            model_name = model_name.__name__.replace('Serializer', '')
            
            # Add a more descriptive summary for operations
            if method == 'GET' and '{id}' not in path:
                operation['summary'] = f"List {model_name} records"
            elif method == 'GET' and '{id}' in path:
                operation['summary'] = f"Retrieve a {model_name} record"
            elif method == 'POST':
                operation['summary'] = f"Create a new {model_name} record"
            elif method == 'PUT':
                operation['summary'] = f"Update a {model_name} record"
            elif method == 'PATCH':
                operation['summary'] = f"Partially update a {model_name} record"
            elif method == 'DELETE':
                operation['summary'] = f"Delete a {model_name} record"
                
            # Add response examples if available
            if hasattr(view, 'get_example_response'):
                example = view.get_example_response(method)
                if example and 'content' in operation.get('responses', {}).get('200', {}):
                    operation['responses']['200']['content']['application/json']['example'] = example
        
        # Add additional security information
        operation['security'] = [{"bearerAuth": []}]
        
        return operation
    
    def get_components(self, path, method):
        components = super().get_components(path, method)
        
        # Add security component
        if 'securitySchemes' not in components:
            components['securitySchemes'] = {
                'bearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT'
                }
            }
            
        return components
