#!/usr/bin/env python
"""
Debug script to test Elasticsearch integration
Run this from your project root: python debug_elasticsearch.py
"""

import os
import sys
import django
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'log_manager.settings')
django.setup()

# Now we can import our services
from services.elasticsearch_service import elasticsearch_service

def test_elasticsearch_connection():
    """Test all aspects of Elasticsearch integration"""
    print("🔍 Testing Elasticsearch Integration...")
    print("=" * 50)
    
    # Test 1: Basic connection
    print("1. Testing basic connection...")
    if elasticsearch_service.is_available():
        print("   ✅ Elasticsearch is available")
    else:
        print("   ❌ Elasticsearch is NOT available")
        return False
    
    # Test 2: Health status
    print("\n2. Getting health status...")
    health = elasticsearch_service.get_health_status()
    print(f"   Status: {health.get('status', 'unknown')}")
    print(f"   Available: {health.get('available', False)}")
    
    # Test 3: Check existing data
    print("\n3. Checking existing data...")
    try:
        import requests
        response = requests.get("http://localhost:9200/logops-logs-*/_count", timeout=5)
        if response.status_code == 200:
            count = response.json().get('count', 0)
            print(f"   📊 Total documents: {count}")
        else:
            print(f"   ❌ Failed to get count: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting count: {e}")
    
    # Test 4: Search for FOBPM logs
    print("\n4. Searching for FOBPM logs...")
    search_params = {
        'application': 'FOBPM',
        'cluster': 'Cluster Prod AKS 1',
        'bundle': 'Bulkdeviceenrollment',
        'size': 10
    }
    
    result = elasticsearch_service.search_logs(search_params)
    print(f"   📝 Search result: {len(result.get('logs', []))} logs found")
    print(f"   📊 Total available: {result.get('total', 0)}")
    
    if result.get('error'):
        print(f"   ❌ Search error: {result['error']}")
    
    # Test 5: Generate sample data if needed
    if result.get('total', 0) == 0:
        print("\n5. No data found - generating sample data...")
        
        # Generate sample logs
        sample_logs = []
        base_time = datetime.now()
        
        for i in range(10):
            log_entry = {
                '@timestamp': base_time.isoformat(),
                'timestamp': base_time.isoformat(),
                'application': 'FOBPM',
                'cluster': 'Cluster Prod AKS 1',
                'bundle': 'Bulkdeviceenrollment',
                'pod': f'fobpm-bulkdeviceenrollment-web-{i+1:03d}',
                'log_level': 'INFO',
                'log_message': f'Test log entry {i+1}',
                'message': f'Test log entry {i+1}',
                'source_file': 'elasticsearch'
            }
            sample_logs.append(log_entry)
        
        # Index the sample logs
        bulk_result = elasticsearch_service.bulk_index_logs(sample_logs)
        print(f"   ✅ Indexed {bulk_result['indexed']} sample logs")
        
        # Wait a moment for indexing
        import time
        time.sleep(2)
        
        # Search again
        result2 = elasticsearch_service.search_logs(search_params)
        print(f"   📝 After indexing: {len(result2.get('logs', []))} logs found")
    
    # Test 6: Test the views function
    print("\n6. Testing views integration...")
    try:
        from app.views import get_logs_from_elasticsearch, format_elasticsearch_logs
        
        logs = get_logs_from_elasticsearch('FOBPM', 'Cluster Prod AKS 1', 'Bulkdeviceenrollment')
        print(f"   📝 Views function returned: {len(logs.get('logs', []))} logs")
        
        if logs.get('logs'):
            formatted = format_elasticsearch_logs(logs['logs'])
            if '# Source: elasticsearch' in formatted:
                print("   ✅ Formatted logs show correct source")
            else:
                print("   ❌ Formatted logs do NOT show elasticsearch source")
                print("   📄 First few lines:")
                for line in formatted.split('\n')[:10]:
                    print(f"      {line}")
        else:
            print("   ❌ No logs returned from views function")
            
    except Exception as e:
        print(f"   ❌ Error testing views: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Debug complete!")
    
    return True

if __name__ == "__main__":
    test_elasticsearch_connection()