# app/management/commands/setup_elasticsearch.py
import os
import json
import logging
from django.core.management.base import BaseCommand
from services.elasticsearch_service import elasticsearch_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Setup Elasticsearch indices and mappings for LogOps'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recreate',
            action='store_true',
            help='Delete existing indices and recreate them',
        )
        parser.add_argument(
            '--load-sample-data',
            action='store_true',
            help='Load sample log data after setup',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Elasticsearch setup...'))
        
        try:
            # Check if Elasticsearch is available
            if not elasticsearch_service.client:
                self.stdout.write(
                    self.style.ERROR('Elasticsearch is not available. Please ensure it is running.')
                )
                return
            
            # Test connection
            if not elasticsearch_service.client.ping():
                self.stdout.write(
                    self.style.ERROR('Cannot connect to Elasticsearch. Please check your configuration.')
                )
                return
            
            self.stdout.write(self.style.SUCCESS('✓ Connected to Elasticsearch'))
            
            # Recreate indices if requested
            if options['recreate']:
                self.delete_existing_indices()
            
            # Setup indices
            elasticsearch_service.setup_indices()
            self.stdout.write(self.style.SUCCESS('✓ Elasticsearch indices setup completed'))
            
            # Load sample data if requested
            if options['load_sample_data']:
                self.load_sample_data()
            
            # Show index status
            self.show_index_status()
            
            self.stdout.write(
                self.style.SUCCESS('Elasticsearch setup completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during Elasticsearch setup: {str(e)}')
            )
            logger.error(f"Elasticsearch setup error: {str(e)}")
    
    def delete_existing_indices(self):
        """Delete existing LogOps indices"""
        self.stdout.write('Deleting existing indices...')
        
        indices = ['logops-logs', 'logops-metrics', 'logops-alerts']
        
        for index in indices:
            try:
                if elasticsearch_service.client.indices.exists(index=index):
                    elasticsearch_service.client.indices.delete(index=index)
                    self.stdout.write(f'  ✓ Deleted index: {index}')
                else:
                    self.stdout.write(f'  - Index does not exist: {index}')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  ! Could not delete index {index}: {str(e)}')
                )
    
    def load_sample_data(self):
        """Load sample log data into Elasticsearch"""
        self.stdout.write('Loading sample log data...')
        
        from datetime import datetime, timedelta
        import random
        
        sample_logs = []
        base_time = datetime.now() - timedelta(hours=24)
        
        applications = ['FOBPM', 'BOBPM', 'BRMS']
        clusters = ['cluster1', 'cluster2', 'cluster3', 'cluster4']
        bundles = ['Bulkdeviceenrollment', 'Bulkordervalidation', 'IOTSubscription']
        log_levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']
        
        for i in range(1000):  # Generate 1000 sample logs
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
            if random.random() < 0.3:  # 30% of logs have performance metrics
                response_time = round(random.uniform(0.1, 5.0), 2)
                message += f" [response_time: {response_time}s]"
            
            if random.random() < 0.2:  # 20% of logs have status codes
                status_code = random.choice([200, 201, 400, 401, 404, 500, 503])
                message += f" [status: {status_code}]"
            
            log_entry = {
                'timestamp': log_time,
                'application': app,
                'cluster': cluster,
                'bundle': bundle,
                'pod': f"{app.lower()}-{bundle.lower()}-{random.choice(['web', 'api', 'worker'])}-{random.randint(1,3):03d}",
                'message': message,
                'source_file': 'sample_data'
            }
            
            sample_logs.append(log_entry)
        
        # Bulk index the sample logs
        result = elasticsearch_service.bulk_index_logs(sample_logs)
        
        self.stdout.write(
            f'  ✓ Loaded {result["indexed"]} sample logs (errors: {result["errors"]})'
        )
    
    def show_index_status(self):
        """Show status of all LogOps indices"""
        self.stdout.write('\nIndex Status:')
        
        try:
            indices_stats = elasticsearch_service.client.indices.stats(index='logops-*')
            
            for index_name, stats in indices_stats['indices'].items():
                doc_count = stats['total']['docs']['count']
                store_size = stats['total']['store']['size_in_bytes']
                store_size_mb = round(store_size / (1024 * 1024), 2)
                
                self.stdout.write(
                    f'  {index_name}: {doc_count} documents, {store_size_mb} MB'
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not get index status: {str(e)}')
            )


# ======================================================================
# app/management/commands/setup_mongodb.py
import os
import logging
from django.core.management.base import BaseCommand
from services.mongodb_service import mongodb_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Setup MongoDB collections and indexes for LogOps'

    def add_arguments(self, parser):
        parser.add_argument(
            '--load-sample-data',
            action='store_true',
            help='Load sample archived data',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting MongoDB setup...'))
        
        try:
            # Check if MongoDB is available
            if not mongodb_service.client:
                self.stdout.write(
                    self.style.ERROR('MongoDB is not available. Please ensure it is running.')
                )
                return
            
            self.stdout.write(self.style.SUCCESS('✓ Connected to MongoDB'))
            
            # Setup collections and indexes
            mongodb_service.setup_collections()
            self.stdout.write(self.style.SUCCESS('✓ MongoDB collections and indexes setup completed'))
            
            # Load sample data if requested
            if options['load_sample_data']:
                self.load_sample_archived_data()
            
            # Show collection status
            self.show_collection_status()
            
            self.stdout.write(
                self.style.SUCCESS('MongoDB setup completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during MongoDB setup: {str(e)}')
            )
            logger.error(f"MongoDB setup error: {str(e)}")
    
    def load_sample_archived_data(self):
        """Load sample archived log data"""
        self.stdout.write('Loading sample archived data...')
        
        from datetime import datetime, timedelta
        import random
        
        # Generate older sample logs for archival
        sample_archived_logs = []
        base_time = datetime.now() - timedelta(days=90)  # 90 days old
        
        applications = ['FOBPM', 'BOBPM', 'BRMS']
        clusters = ['cluster1', 'cluster2']
        bundles = ['Legacy_Bundle', 'Archive_Test']
        
        for i in range(500):  # Generate 500 archived logs
            app = random.choice(applications)
            cluster = random.choice(clusters)
            bundle = random.choice(bundles)
            
            log_time = base_time + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            log_entry = {
                'timestamp': log_time,
                'application': app,
                'cluster': cluster,
                'bundle': bundle,
                'pod': f"{app.lower()}-{bundle.lower()}-archived-{random.randint(1,5)}",
                'log_level': random.choice(['INFO', 'WARN', 'ERROR']),
                'message': f'Archived log entry {i+1} from {app}',
                'source_file': 'archived_sample_data'
            }
            
            sample_archived_logs.append(log_entry)
        
        # Archive the logs
        result = mongodb_service.archive_logs(sample_archived_logs, "sample_data_load")
        
        self.stdout.write(
            f'  ✓ Archived {result["archived"]} sample logs (errors: {result["errors"]})'
        )
    
    def show_collection_status(self):
        """Show status of all LogOps collections"""
        self.stdout.write('\nCollection Status:')
        
        try:
            collections = [
                'archived_logs', 'log_metadata', 'analysis_cache', 
                'external_sources', 'user_sessions'
            ]
            
            for collection_name in collections:
                try:
                    stats = mongodb_service.db.command('collStats', collection_name)
                    count = stats.get('count', 0)
                    size = stats.get('size', 0)
                    size_mb = round(size / (1024 * 1024), 2) if size > 0 else 0
                    
                    self.stdout.write(
                        f'  {collection_name}: {count} documents, {size_mb} MB'
                    )
                except Exception:
                    self.stdout.write(f'  {collection_name}: Collection not found or empty')
                    
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not get collection status: {str(e)}')
            )


# ======================================================================
# app/management/commands/setup_ollama.py
import os
import logging
import time
from django.core.management.base import BaseCommand
from services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Setup Ollama models for LogOps AI analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            nargs='+',
            default=['llama3.2:latest', 'codellama:7b', 'mistral:latest'],
            help='List of models to pull and setup',
        )
        parser.add_argument(
            '--test-models',
            action='store_true',
            help='Test models after setup',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Ollama setup...'))
        
        try:
            # Check if Ollama is available
            if not ollama_service.is_available():
                self.stdout.write(
                    self.style.ERROR('Ollama service is not available. Please ensure it is running.')
                )
                self.stdout.write('You can start Ollama with: ollama serve')
                return
            
            self.stdout.write(self.style.SUCCESS('✓ Connected to Ollama service'))
            
            # List current models
            current_models = ollama_service.list_models()
            self.stdout.write(f'Current models: {len(current_models)}')
            for model in current_models:
                self.stdout.write(f'  - {model["name"]}')
            
            # Pull required models
            models_to_pull = options['models']
            self.stdout.write(f'\nPulling models: {models_to_pull}')
            
            for model in models_to_pull:
                if not any(model in m['name'] for m in current_models):
                    self.stdout.write(f'Pulling {model}... (this may take several minutes)')
                    success = ollama_service.pull_model(model)
                    
                    if success:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Successfully pulled {model}'))
                    else:
                        self.stdout.write(self.style.ERROR(f'  ✗ Failed to pull {model}'))
                else:
                    self.stdout.write(f'  - {model} already available')
            
            # Test models if requested
            if options['test_models']:
                self.test_models()
            
            # Show final status
            self.show_model_status()
            
            self.stdout.write(
                self.style.SUCCESS('Ollama setup completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during Ollama setup: {str(e)}')
            )
            logger.error(f"Ollama setup error: {str(e)}")
    
    def test_models(self):
        """Test model functionality"""
        self.stdout.write('\nTesting models...')
        
        test_prompt = "Summarize this log entry: [2024-01-01 10:00:00] INFO: Service started successfully"
        
        models = ollama_service.list_models()
        
        for model in models[:3]:  # Test first 3 models
            model_name = model['name']
            self.stdout.write(f'Testing {model_name}...')
            
            start_time = time.time()
            response = ollama_service.generate_response(model_name, test_prompt)
            end_time = time.time()
            
            if response:
                response_time = round(end_time - start_time, 2)
                response_preview = response[:100] + "..." if len(response) > 100 else response
                self.stdout.write(
                    f'  ✓ Response in {response_time}s: {response_preview}'
                )
            else:
                self.stdout.write(f'  ✗ No response from {model_name}')
    
    def show_model_status(self):
        """Show status of all available models"""
        self.stdout.write('\nModel Status:')
        
        try:
            models = ollama_service.list_models()
            
            if not models:
                self.stdout.write('  No models available')
                return
            
            for model in models:
                name = model['name']
                size = model.get('size', 0)
                size_gb = round(size / (1024**3), 2) if size > 0 else 0
                modified = model.get('modified_at', 'Unknown')
                
                self.stdout.write(f'  {name}: {size_gb} GB (modified: {modified})')
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not get model status: {str(e)}')
            )


# ======================================================================
# app/management/commands/load_sample_data.py
import os
import json
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Load comprehensive sample data for LogOps demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--elasticsearch',
            action='store_true',
            help='Load sample data into Elasticsearch',
        )
        parser.add_argument(
            '--mongodb',
            action='store_true',
            help='Load sample data into MongoDB',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Load sample data into all systems',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading sample data for LogOps...'))
        
        if options['all'] or options['elasticsearch']:
            self.load_elasticsearch_data()
        
        if options['all'] or options['mongodb']:
            self.load_mongodb_data()
        
        self.create_sample_config_files()
        
        self.stdout.write(
            self.style.SUCCESS('Sample data loading completed successfully!')
        )
    
    def load_elasticsearch_data(self):
        """Load sample data into Elasticsearch"""
        from django.core.management import call_command
        
        self.stdout.write('Loading Elasticsearch sample data...')
        call_command('setup_elasticsearch', '--load-sample-data')
    
    def load_mongodb_data(self):
        """Load sample data into MongoDB"""
        from django.core.management import call_command
        
        self.stdout.write('Loading MongoDB sample data...')
        call_command('setup_mongodb', '--load-sample-data')
    
    def create_sample_config_files(self):
        """Create sample configuration files"""
        self.stdout.write('Creating sample configuration files...')
        
        # Create enhanced app_config.json
        app_config = {
            "FOBPM": {
                "clusters": ["cluster1", "cluster2", "cluster3", "cluster4"],
                "bundles": ["Bulkdeviceenrollment", "Bulkordervalidation", "DeviceManagement"]
            },
            "BOBPM": {
                "clusters": ["cluster1", "cluster2", "cluster3", "cluster4"],
                "bundles": ["IOTSubscription", "Bulkordervalidation", "CustomerOnboarding"]
            },
            "BRMS": {
                "clusters": ["cluster1", "cluster2", "cluster3", "cluster4"],
                "bundles": ["MobilityPromotionTreatmentRules", "MobilityDeviceTreatmentRules", "BusinessRuleEngine"]
            },
            "PaymentService": {
                "clusters": ["cluster1", "cluster2", "cluster5"],
                "bundles": ["PaymentProcessing", "FraudDetection", "TransactionValidation"]
            }
        }
        
        # Create pods_config.json
        pods_config = {}
        for app, app_data in app_config.items():
            pods_config[app] = {}
            for cluster in app_data["clusters"]:
                pods_config[app][cluster] = {}
                for bundle in app_data["bundles"]:
                    pods_config[app][cluster][bundle] = [
                        {
                            "name": f"{app.lower()}-{bundle.lower()}-web-001",
                            "display_name": f"{app} {bundle} Web Server 1"
                        },
                        {
                            "name": f"{app.lower()}-{bundle.lower()}-web-002",
                            "display_name": f"{app} {bundle} Web Server 2"
                        },
                        {
                            "name": f"{app.lower()}-{bundle.lower()}-api-001",
                            "display_name": f"{app} {bundle} API Server"
                        },
                        {
                            "name": f"{app.lower()}-{bundle.lower()}-worker-001",
                            "display_name": f"{app} {bundle} Worker"
                        },
                        {
                            "name": f"{app.lower()}-{bundle.lower()}-error-pod",
                            "display_name": f"{app} {bundle} Error Demo Pod"
                        }
                    ]
        
        # Write configuration files
        config_dir = os.path.join("app", "static")
        os.makedirs(config_dir, exist_ok=True)
        
        with open(os.path.join(config_dir, "app_config.json"), "w") as f:
            json.dump(app_config, f, indent=2)
        
        with open(os.path.join(config_dir, "pods_config.json"), "w") as f:
            json.dump(pods_config, f, indent=2)
        
        self.stdout.write('  ✓ Created enhanced configuration files')


# ======================================================================
# app/management/commands/system_health.py
import logging
from django.core.management.base import BaseCommand
from services.elasticsearch_service import elasticsearch_service
from services.mongodb_service import mongodb_service
from services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check health status of all LogOps systems'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('LogOps System Health Check'))
        self.stdout.write('=' * 50)
        
        # Check Elasticsearch
        self.check_elasticsearch()
        
        # Check MongoDB
        self.check_mongodb()
        
        # Check Ollama
        self.check_ollama()
        
        # Overall status
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Health check completed'))
    
    def check_elasticsearch(self):
        """Check Elasticsearch health"""
        self.stdout.write('\n🔍 Elasticsearch:')
        
        try:
            health = elasticsearch_service.get_health_status()
            
            if health.get('status') == 'error':
                self.stdout.write(f'  ❌ Error: {health.get("error")}')
            else:
                status = health.get('status', 'unknown')
                nodes = health.get('number_of_nodes', 0)
                shards = health.get('active_shards', 0)
                
                status_color = self.style.SUCCESS if status == 'green' else (
                    self.style.WARNING if status == 'yellow' else self.style.ERROR
                )
                
                self.stdout.write(f'  Status: {status_color(status)}')
                self.stdout.write(f'  Nodes: {nodes}')
                self.stdout.write(f'  Active Shards: {shards}')
                
                # Show indices
                if 'indices' in health:
                    self.stdout.write('  Indices:')
                    for index, stats in health['indices'].items():
                        docs = stats.get('doc_count', 0)
                        size_mb = round(stats.get('store_size', 0) / (1024*1024), 2)
                        self.stdout.write(f'    {index}: {docs} docs, {size_mb} MB')
                
        except Exception as e:
            self.stdout.write(f'  ❌ Error checking Elasticsearch: {str(e)}')
    
    def check_mongodb(self):
        """Check MongoDB health"""
        self.stdout.write('\n🗄️  MongoDB:')
        
        try:
            health = mongodb_service.get_health_status()
            
            if health.get('status') == 'error':
                self.stdout.write(f'  ❌ Error: {health.get("error")}')
            else:
                version = health.get('version', 'unknown')
                uptime = health.get('uptime', 0)
                
                self.stdout.write(f'  Status: {self.style.SUCCESS("connected")}')
                self.stdout.write(f'  Version: {version}')
                self.stdout.write(f'  Uptime: {uptime}s')
                
                # Show collections
                if 'collections' in health:
                    self.stdout.write('  Collections:')
                    for collection, stats in health['collections'].items():
                        count = stats.get('count', 0)
                        size_mb = round(stats.get('size', 0) / (1024*1024), 2)
                        self.stdout.write(f'    {collection}: {count} docs, {size_mb} MB')
                
        except Exception as e:
            self.stdout.write(f'  ❌ Error checking MongoDB: {str(e)}')
    
    def check_ollama(self):
        """Check Ollama health"""
        self.stdout.write('\n🤖 Ollama:')
        
        try:
            health = ollama_service.get_service_health()
            
            if health.get('status') == 'error':
                self.stdout.write(f'  ❌ Error: {health.get("error")}')
            elif health.get('status') == 'unavailable':
                self.stdout.write(f'  ⚠️  Service unavailable: {health.get("error")}')
            else:
                host = health.get('host', 'unknown')
                models_count = health.get('models_available', 0)
                test_status = health.get('test_generation', 'unknown')
                
                self.stdout.write(f'  Status: {self.style.SUCCESS("healthy")}')
                self.stdout.write(f'  Host: {host}')
                self.stdout.write(f'  Models Available: {models_count}')
                self.stdout.write(f'  Test Generation: {test_status}')
                
                # Show models
                if 'models' in health:
                    self.stdout.write('  Models:')
                    for model in health['models'][:5]:  # Show first 5 models
                        self.stdout.write(f'    - {model}')
                
        except Exception as e:
            self.stdout.write(f'  ❌ Error checking Ollama: {str(e)}')