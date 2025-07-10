import requests
import json
from datetime import datetime, timedelta
import random

# Elasticsearch connection
es_url = 'http://localhost:9200'

try:
    # Test connection
    response = requests.get(f'{es_url}/_cluster/health')
    if response.status_code != 200:
        print('Error: Cannot connect to Elasticsearch')
        exit(1)
    
    print('Connected to Elasticsearch successfully!')
    
    # Create sample log data
    applications = ['FOBPM', 'BOBPM', 'BRMS']
    clusters = ['cluster1', 'cluster2', 'cluster3', 'cluster4'] 
    bundles = ['Bulkdeviceenrollment', 'Bulkordervalidation', 'IOTSubscription']
    log_levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']
    
    sample_logs = []
    base_time = datetime.now() - timedelta(hours=24)
    
    for i in range(1000):  # Create 1000 sample logs
        app = random.choice(applications)
        cluster = random.choice(clusters)
        bundle = random.choice(bundles)
        level = random.choice(log_levels)
        
        # Weight log levels realistically
        if random.random() < 0.1:  # 10% errors
            level = 'ERROR'
        elif random.random() < 0.2:  # 20% warnings  
            level = 'WARN'
        else:  # 70% info/debug
            level = random.choice(['INFO', 'DEBUG'])
        
        log_time = base_time + timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        messages = {
            'INFO': [
                'Service started successfully',
                'Processing request completed', 
                'Health check passed',
                'Database connection established',
                'User authentication successful'
            ],
            'WARN': [
                'High memory usage detected: 85%',
                'Response time degradation: 2.8s',
                'Queue backlog growing: 150 pending items',
                'Connection pool exhausted',
                'Cache miss ratio high: 65%'
            ],
            'ERROR': [
                'Database connection timeout after 30s',
                'Failed to process request: connection refused',
                'Authentication failed: invalid credentials', 
                'OutOfMemoryError: Java heap space',
                'Network timeout: connection reset by peer'
            ],
            'DEBUG': [
                'Method execution started',
                'Variable state: processing=true',
                'Cache lookup performed',
                'Request parameters validated',
                'Session data retrieved'
            ]
        }
        
        message = random.choice(messages[level])
        
        # Add performance metrics for some logs
        if random.random() < 0.3:  # 30% have metrics
            response_time = round(random.uniform(0.1, 5.0), 2)
            message += f' [response_time: {response_time}s]'
        
        if random.random() < 0.2:  # 20% have status codes
            status_code = random.choice([200, 201, 400, 401, 404, 500, 503])
            message += f' [status: {status_code}]'
        
        log_entry = {
            '@timestamp': log_time.isoformat(),
            'application': app,
            'cluster': cluster,
            'bundle': bundle,
            'pod': f'{app.lower()}-{bundle.lower()}-{random.choice(["web", "api", "worker"])}-{random.randint(1,3):03d}',
            'log_level': level,
            'log_message': message,
            'source_file': 'sample_data'
        }
        
        sample_logs.append(log_entry)
    
    # Bulk index the logs
    today = datetime.now().strftime('%Y.%m.%d')
    index_name = f'logops-logs-{today}'
    
    bulk_data = []
    for log in sample_logs:
        # Add index action
        bulk_data.append(json.dumps({'index': {'_index': index_name}}))
        # Add document
        bulk_data.append(json.dumps(log))
    
    bulk_body = '\n'.join(bulk_data) + '\n'
    
    # Send bulk request
    headers = {'Content-Type': 'application/x-ndjson'}
    response = requests.post(f'{es_url}/_bulk', data=bulk_body, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        indexed = len([item for item in result['items'] if 'index' in item and item['index']['status'] in [200, 201]])
        print(f'Successfully indexed {indexed} sample logs into {index_name}')
        
        # Verify the data
        search_response = requests.get(f'{es_url}/{index_name}/_search?size=0')
        if search_response.status_code == 200:
            total = search_response.json()['hits']['total']['value']
            print(f'Total documents in index: {total}')
    else:
        print('Error indexing data:', response.text)
        
except Exception as e:
    print('Error:', e)
