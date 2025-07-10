import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random
from elasticsearch import Elasticsearch
import base64

logger = logging.getLogger(__name__)

class ElasticsearchService:
    """Enhanced Elasticsearch service that works with both local and cloud Elasticsearch"""
    
    def __init__(self):
        # Cloud Elasticsearch configuration
        self.es_cloud_id = os.getenv('ELASTICSEARCH_CLOUD_ID')
        self.es_api_key = os.getenv('ELASTICSEARCH_API_KEY')
        self.es_host = os.getenv('ELASTICSEARCH_HOST')
        
        # Determine if we're using cloud or local ES
        if self.es_cloud_id or self.es_api_key or (self.es_host and 'cloud.es.io' in self.es_host):
            self.setup_cloud_connection()
        else:
            self.setup_local_connection()
        
        self.connection_retries = 0
        self.max_retries = 3
        self.setup_connection()
    
    def setup_cloud_connection(self):
        """Setup connection for Elastic Cloud - FORCE FIX VERSION"""
        
        # FORCE the correct URL - bypasses all caching issues
        correct_url = "https://ac3ac17baa504fe78bd6eef8734062c7.us-central1.gcp.cloud.es.io"
        correct_api_key = "bnE2V3o1Y0JneUp0Tk9Zd0toVE46V3dGYWl5ZXUtenhXcWdDRWk1WjBPUQ=="
        
        print(f"🔧 FORCE FIX: Using URL: {correct_url}")
        print(f"🔧 FORCE FIX: Using API Key: {correct_api_key[:20]}...")
        
        # Set the correct values directly
        self.base_url = correct_url
        self.auth_headers = {
            'Authorization': f'ApiKey {correct_api_key}',
            'Content-Type': 'application/json'
        }
        
        # Test the connection immediately
        try:
            response = requests.get(f"{self.base_url}/_cluster/health", headers=self.auth_headers)
            if response.status_code == 200:
                print("✅ FORCE FIX: Connection successful!")
                cluster_info = response.json()
                print(f"✅ Cluster Status: {cluster_info.get('status', 'unknown')}")
                print(f"✅ Nodes: {cluster_info.get('number_of_nodes', 0)}")
                logger.info(f"🌩️ Configured for Elastic Cloud: {self.base_url}")
                return True
            else:
                print(f"❌ FORCE FIX: Connection failed with status {response.status_code}")
                logger.error(f"❌ Failed to connect to Elasticsearch: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ FORCE FIX: Connection error: {e}")
            logger.error(f"❌ Error connecting to Elasticsearch: {str(e)}")
            return False

    def setup_local_connection(self):
        """Setup connection for local Elasticsearch"""
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost:9200')
        self.base_url = f"http://{self.es_host}"
        self.auth_headers = {'Content-Type': 'application/json'}
        logger.info(f"🏠 Configured for Local Elasticsearch: {self.base_url}")
    
    def setup_connection(self):
        """Test connection and create sample data"""
        try:
            response = requests.get(
                f"{self.base_url}/_cluster/health", 
                headers=self.auth_headers,
                timeout=10
            )
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ Successfully connected to Elasticsearch: {health_data.get('cluster_name', 'Unknown')}")
                self.create_sample_data()
            else:
                logger.error(f"❌ Failed to connect to Elasticsearch: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"❌ Error connecting to Elasticsearch: {str(e)}")
    
    def is_available(self) -> bool:
        """Quick availability check"""
        try:
            response = requests.get(
                f"{self.base_url}/_cluster/health", 
                headers=self.auth_headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    @staticmethod   
    def get_elasticsearch_client():
       username = os.getenv("ELASTICSEARCH_USERNAME")
       password = os.getenv("ELASTICSEARCH_PASSWORD")

       if not username or not password:
        raise ValueError("Elasticsearch username or password is not set.")

       return Elasticsearch(
        hosts=[{
            "host": os.getenv("ELASTICSEARCH_HOST", "3361399602e4406eb9fc6c6308f32ac8.us-central1.gcp.cloud.es.io"),
            "port": 443,
            "scheme": "https"
        }],
        basic_auth=(username, password),
        verify_certs=True,
        request_timeout=30,
        max_retries=10,
        retry_on_timeout=True
    )
    
    def create_sample_data(self):
        """Create sample data if none exists"""
        try:
            # Check if we have data - FIXED: Remove -*
            response = requests.get(
                f"{self.base_url}/logops-logs/_count", 
                headers=self.auth_headers,
                timeout=10
            )
            if response.status_code == 200:
                count = response.json().get('count', 0)
                if count > 100:  # Reduced threshold to allow regeneration for testing
                    logger.info(f"✅ Found {count} existing logs in Elasticsearch")
                    return
            
            # Create sample data
            logger.info("📊 Creating sample data for ALL 4 clusters in Elasticsearch...")
            sample_logs = self.generate_sample_data()
            result = self.bulk_index_logs(sample_logs)
            logger.info(f"✅ Created {result['indexed']} sample log entries covering all clusters")
                
        except Exception as e:
            logger.error(f"❌ Error creating sample data: {str(e)}")
    
    def generate_sample_data(self) -> List[Dict[str, Any]]:
        """Generate comprehensive sample data for ALL apps and ALL clusters"""
        applications = {
            'FOBPM': ['Bulkdeviceenrollment', 'Bulkordervalidation', 'IOTSubscription'],
            'BOBPM': ['IOTSubscription', 'Bulkordervalidation', 'MobilitySubscription'],
            'BRMS': ['MobilityPromotionTreatmentRules', 'MobilityDeviceTreatmentRules', 'BusinessRules'],
        }
        
        # ALL 4 clusters
        clusters = ['Cluster Prod AKS 1', 'Cluster Prod AKS 2', 'Cluster Prod AKS 3', 'Cluster Prod AKS 4']
        
        log_messages = {
            'INFO': [
                'Service started successfully',
                'Processing request completed',
                'Health check passed',
                'Database connection established',
                'User authenticated successfully',
                'Request processed in {}ms',
                'Cache hit for key: user_{}',
                'Background job completed',
                'Configuration loaded successfully',
                'Transaction completed successfully',
                'Backup process initiated'
            ],
            'WARN': [
                'High memory usage detected: {}%',
                'Response time degradation: {}s',
                'Queue backlog growing: {} pending items',
                'Connection pool near capacity: {}%',
                'Cache miss ratio high: {}%',
                'Slow query detected: {}ms',
                'Retry attempt {} for failed operation',
                'Low disk space warning: {}% full'
            ],
            'ERROR': [
                'Database connection timeout after {}s',
                'Failed to process request: connection refused',
                'Authentication failed: invalid credentials',
                'OutOfMemoryError: Java heap space',
                'Network timeout: connection reset by peer',
                'Service temporarily unavailable',
                'Invalid request format',
                'Transaction rollback due to error',
                'Critical service failure detected'
            ]
        }
        
        sample_logs = []
        base_time = datetime.now() - timedelta(days=1)
        
        # FIXED: Generate data for ALL clusters (removed slice)
        for app_name, bundles in applications.items():
            for cluster in clusters:  # ✅ NOW INCLUDES ALL 4 CLUSTERS
                for bundle in bundles:
                    for service_num in range(1, 6):  # 5 pods per bundle
                        pod_name = f"{app_name.lower()}-{bundle.lower()}-web-{service_num:03d}"
                        
                        # Generate more logs per pod for better demo
                        log_count = random.randint(60, 80)  # More logs per pod
                        
                        for _ in range(log_count):
                            # Random time within the last 24 hours
                            log_time = base_time + timedelta(
                                hours=random.randint(0, 23),
                                minutes=random.randint(0, 59),
                                seconds=random.randint(0, 59)
                            )
                            
                            # Weight log levels: 70% INFO, 20% WARN, 10% ERROR
                            level = random.choices(
                                ['INFO', 'WARN', 'ERROR'],
                                weights=[70, 20, 10]
                            )[0]
                            
                            # Select and format message
                            message_template = random.choice(log_messages[level])
                            
                            if '{}' in message_template:
                                if 'ms' in message_template:
                                    message = message_template.format(random.randint(50, 2000))
                                elif '%' in message_template:
                                    message = message_template.format(random.randint(70, 95))
                                elif 's' in message_template and 'timeout' in message_template:
                                    message = message_template.format(random.randint(30, 120))
                                elif 'pending' in message_template:
                                    message = message_template.format(random.randint(50, 500))
                                elif 'attempt' in message_template:
                                    message = message_template.format(random.randint(1, 5))
                                else:
                                    message = message_template.format(random.randint(100, 999))
                            else:
                                message = message_template
                            
                            # Create log entry compatible with views.py expectations
                            log_entry = {
                                '@timestamp': log_time.isoformat(),
                                'timestamp': log_time.isoformat(),
                                'application': app_name,
                                'cluster': cluster,
                                'bundle': bundle,
                                'pod': pod_name,
                                'log_level': level,
                                'log_message': message,
                                'message': message,
                                'source_file': 'elasticsearch'
                            }
                            
                            # Add performance metrics occasionally
                            if random.random() < 0.3:
                                log_entry['response_time'] = round(random.uniform(0.1, 5.0), 3)
                            
                            if random.random() < 0.2:
                                log_entry['status_code'] = random.choice([200, 201, 400, 401, 404, 500])
                            
                            sample_logs.append(log_entry)
        
        # Add some logs specifically for Cluster 4 to ensure it has data
        logger.info(f"📊 Generated {len(sample_logs)} logs covering all {len(clusters)} clusters")
        cluster_counts = {}
        for log in sample_logs:
            cluster = log['cluster']
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        
        for cluster, count in cluster_counts.items():
            logger.info(f"   - {cluster}: {count} logs")
        
        return sample_logs
    
    def search_logs(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search logs using direct HTTP requests - Compatible with views.py"""
        try:
            if not self.is_available():
                logger.error("❌ Elasticsearch not available for search")
                return {'logs': [], 'total': 0, 'error': 'Elasticsearch not available'}
            
            # Build search query
            query = {
                "query": {"bool": {"must": []}},
                "size": query_params.get('size', 100),
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
            
            # Add filters - exactly what views.py expects
            for field in ['application', 'cluster', 'bundle', 'pod', 'log_level']:
                if query_params.get(field):
                    query["query"]["bool"]["must"].append({
                        "term": {f"{field}.keyword": query_params[field]}
                    })
            
            # Text search
            if query_params.get('search_text'):
                query["query"]["bool"]["must"].append({
                    "multi_match": {
                        "query": query_params['search_text'],
                        "fields": ["log_message", "message"]
                    }
                })
            
            # If no filters, match all
            if not query["query"]["bool"]["must"]:
                query["query"] = {"match_all": {}}
            
            # Execute search - FIXED: Remove the -* pattern
            response = requests.post(
                f"{self.base_url}/logops-logs/_search",  # CHANGED: removed -* 
                json=query,
                headers=self.auth_headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                logs = []
                for hit in data['hits']['hits']:
                    log_entry = hit['_source']
                    log_entry['_id'] = hit['_id']
                    logs.append(log_entry)
                
                logger.info(f"✅ Found {len(logs)} logs for query: {query_params}")
                return {
                    'logs': logs,
                    'total': data['hits']['total']['value'],
                    'page': query_params.get('page', 1),
                    'size': len(logs)
                }
            else:
                logger.error(f"❌ Search failed with HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return {'logs': [], 'total': 0, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            logger.error(f"❌ Error searching logs: {str(e)}")
            return {'logs': [], 'total': 0, 'error': str(e)}
    
    def bulk_index_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk index logs using HTTP requests"""
        try:
            if not logs:
                return {'indexed': 0, 'errors': 0}
            
            # Prepare bulk data - use the existing index name
            bulk_data = []
            index_name = 'logops-logs'  # Use the index we created in cloud
            
            for log_entry in logs:
                bulk_data.append(json.dumps({'index': {'_index': index_name}}))
                bulk_data.append(json.dumps(log_entry))
            
            bulk_body = '\n'.join(bulk_data) + '\n'
            
            # Create headers for bulk request
            bulk_headers = self.auth_headers.copy()
            bulk_headers['Content-Type'] = 'application/x-ndjson'
            
            response = requests.post(
                f"{self.base_url}/_bulk",
                data=bulk_body,
                headers=bulk_headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                indexed = len([item for item in result['items'] 
                             if 'index' in item and item['index']['status'] in [200, 201]])
                errors = len(result['items']) - indexed
                
                logger.info(f"✅ Bulk indexed {indexed} logs with {errors} errors")
                return {'indexed': indexed, 'errors': errors}
            else:
                logger.error(f"❌ Bulk index failed with HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return {'indexed': 0, 'errors': len(logs)}
            
        except Exception as e:
            logger.error(f"❌ Bulk index error: {str(e)}")
            return {'indexed': 0, 'errors': len(logs)}
    
    def get_log_statistics(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get log statistics - Compatible with views.py"""
        try:
            query = {
                "query": {"match_all": {}},
                "size": 0,
                "aggs": {
                    "log_levels": {"terms": {"field": "log_level.keyword", "size": 10}},
                    "applications": {"terms": {"field": "application.keyword", "size": 20}},
                    "clusters": {"terms": {"field": "cluster.keyword", "size": 20}},
                    "pods": {"terms": {"field": "pod.keyword", "size": 100}},
                    "bundles": {"terms": {"field": "bundle.keyword", "size": 50}}
                }
            }
            
            if filters:
                must_filters = []
                for field in ['application', 'cluster', 'bundle']:
                    if filters.get(field):
                        must_filters.append({"term": {f"{field}.keyword": filters[field]}})
                
                if must_filters:
                    query["query"] = {"bool": {"must": must_filters}}
            
            # FIXED: Remove -* pattern
            response = requests.post(
                f"{self.base_url}/logops-logs/_search",
                json=query,
                headers=self.auth_headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                aggs = data.get('aggregations', {})
                
                return {
                    'total_logs': data['hits']['total']['value'],
                    'log_levels': {b['key']: b['doc_count'] for b in aggs.get('log_levels', {}).get('buckets', [])},
                    'applications': {b['key']: b['doc_count'] for b in aggs.get('applications', {}).get('buckets', [])},
                    'clusters': {b['key']: b['doc_count'] for b in aggs.get('clusters', {}).get('buckets', [])},
                    'pods': {b['key']: b['doc_count'] for b in aggs.get('pods', {}).get('buckets', [])},
                    'bundles': {b['key']: b['doc_count'] for b in aggs.get('bundles', {}).get('buckets', [])}
                }
            else:
                logger.error(f"❌ Statistics query failed with HTTP {response.status_code}")
                return {'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            logger.error(f"❌ Statistics error: {str(e)}")
            return {'error': str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get Elasticsearch health status"""
        try:
            response = requests.get(
                f"{self.base_url}/_cluster/health", 
                headers=self.auth_headers,
                timeout=10
            )
            if response.status_code == 200:
                health = response.json()
                
                # Get index statistics - FIXED: Use correct pattern
                stats_response = requests.get(
                    f"{self.base_url}/logops-logs/_stats", 
                    headers=self.auth_headers,
                    timeout=10
                )
                indices = {}
                if stats_response.status_code == 200:
                    stats_data = stats_response.json()
                    for name, stats in stats_data.get('indices', {}).items():
                        indices[name] = {
                            'doc_count': stats['total']['docs']['count'],
                            'store_size': stats['total']['store']['size_in_bytes']
                        }
                
                return {
                    'status': health['status'],
                    'cluster_name': health['cluster_name'],
                    'number_of_nodes': health['number_of_nodes'],
                    'indices': indices,
                    'available': True,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'status': 'error', 'available': False, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'status': 'error', 'available': False, 'error': str(e)}


# Global service instance
elasticsearch_service = ElasticsearchService()