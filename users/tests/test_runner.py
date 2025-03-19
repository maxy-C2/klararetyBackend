# users/tests/test_runner.py
import unittest
from django.test.runner import DiscoverRunner

class NoMigrationTestRunner(DiscoverRunner):
    """Test runner that disables migrations for faster tests"""
    
    def setup_databases(self, **kwargs):
        from django.db import connections
        
        # Create test databases
        old_names = []
        for connection in connections.all():
            # Disable migrations
            connection.disable_constraint_checking()
            old_names.append((connection, connection.settings_dict['NAME']))
            
            # Create test database
            test_db_name = connection.creation.create_test_db(
                autoclobber=True, 
                serialize=self.serialize
            )
        
        return old_names

class CategoryTestRunner(DiscoverRunner):
    """Test runner that allows running tests by category"""
    
    def __init__(self, category=None, **kwargs):
        self.category = category
        super().__init__(**kwargs)
    
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if test_labels is None:
            test_labels = []
        
        if self.category:
            if self.category == 'fast':
                test_labels = ['users.tests.test_models', 'users.tests.test_serializers']
            elif self.category == 'slow':
                test_labels = ['users.tests.test_views', 'users.tests.test_integration']
            elif self.category == 'security':
                test_labels = ['users.tests.test_auth', 'users.tests.test_permissions']
            elif self.category == 'admin':
                test_labels = ['users.tests.test_admin']
            elif self.category == 'api':
                test_labels = ['users.tests.test_api_docs']
            
        return super().build_suite(test_labels, extra_tests, **kwargs)

def fast_tests():
    """Run only fast tests (models and serializers)"""
    test_runner = CategoryTestRunner(category='fast')
    return test_runner.run_tests([])

def security_tests():
    """Run only security-related tests"""
    test_runner = CategoryTestRunner(category='security')
    return test_runner.run_tests([])

if __name__ == '__main__':
    unittest.main()
