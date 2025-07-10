import os
import json
import re
import requests
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django.views import View

# Import our new services
from services.elasticsearch_service import elasticsearch_service

# Set up logging
logger = logging.getLogger(__name__)

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY") or getattr(settings, 'TOGETHER_API_KEY', None)

# Cache timeouts
APP_CONFIG_CACHE_TIMEOUT = 300
PODS_CACHE_TIMEOUT = 120
SEARCH_CACHE_TIMEOUT = 60


def sanitize_filename(value):
    """Sanitize filename to avoid path traversal and invalid characters."""
    if not value:
        return "unknown"
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', str(value))

def map_frontend_to_elasticsearch_values(app, cluster, bundle, pod):
    """Map frontend form values to Elasticsearch field values"""
    
    # Map cluster values from form to ES
    cluster_mapping = {
        'cluster1': 'Cluster Prod AKS 1',
        'cluster2': 'Cluster Prod AKS 2', 
        'cluster3': 'Cluster Prod AKS 3',
        'cluster4': 'Cluster Prod AKS 4'
    }
    
    # Map bundle values (fix casing)
    bundle_mapping = {
        'bulkdeviceenrollment': 'Bulkdeviceenrollment',
        'bulkordervalidation': 'Bulkordervalidation',
        'iotsubscription': 'IOTSubscription',
        'mobilitysubscription': 'MobilitySubscription',
        'mobilitypromotiontreatmentrules': 'MobilityPromotionTreatmentRules',
        'mobilitydevicetreatmentrules': 'MobilityDeviceTreatmentRules',
        'businessrules': 'BusinessRules',
        'customermanagement': 'CustomerManagement',
        'inventorytracking': 'InventoryTracking',
        'devicemanagement': 'DeviceManagement',
        'networkmonitoring': 'NetworkMonitoring'
    }
    
    # Apply mappings
    mapped_cluster = cluster_mapping.get(cluster, cluster)
    mapped_bundle = bundle_mapping.get(bundle.lower(), bundle)
    
    # Fix pod name casing (ES has lowercase pod names)
    mapped_pod = pod.lower() if pod else pod
    
    return app, mapped_cluster, mapped_bundle, mapped_pod

@require_GET
@csrf_exempt 
def get_app_config(request):
    """Get application configuration with multiple apps - UPDATED FOR NEW CONFIG"""
    try:
        # Try to read from static file first
        config_path = os.path.join(settings.BASE_DIR, 'app', 'static', 'app_config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info("✅ Loaded app config from file successfully")
            return JsonResponse(config)
        
        # Updated fallback config that matches your new app_config.json
        logger.warning("⚠️ App config file not found, using fallback config")
        fallback_config = {
            "FOBPM": {
                "clusters": ["Cluster Prod AKS 1", "Cluster Prod AKS 2", "Cluster Prod AKS 3", "Cluster Prod AKS 4"],
                "bundles": ["Bulkdeviceenrollment", "Bulkordervalidation", "IOTSubscription"]
            },
            "BOBPM": {
                "clusters": ["Cluster Prod AKS 1", "Cluster Prod AKS 2", "Cluster Prod AKS 3", "Cluster Prod AKS 4"],
                "bundles": ["IOTSubscription", "Bulkordervalidation", "MobilitySubscription"]
            },
            "BRMS": {
                "clusters": ["Cluster Prod AKS 1", "Cluster Prod AKS 2", "Cluster Prod AKS 3", "Cluster Prod AKS 4"],
                "bundles": ["MobilityPromotionTreatmentRules", "MobilityDeviceTreatmentRules", "BusinessRules"]
            },
        }
        
        return JsonResponse(fallback_config)
        
    except Exception as e:
        logger.error(f"❌ Error getting app config: {str(e)}")
        # Emergency fallback - minimal but consistent
        return JsonResponse({
            "FOBPM": {
                "clusters": ["Cluster Prod AKS 1", "Cluster Prod AKS 2"],
                "bundles": ["Bulkdeviceenrollment", "Bulkordervalidation"]
            },
            "BOBPM": {
                "clusters": ["Cluster Prod AKS 1", "Cluster Prod AKS 2"],
                "bundles": ["IOTSubscription", "Bulkordervalidation"]
            },
            "BRMS": {
                "clusters": ["Cluster Prod AKS 1", "Cluster Prod AKS 2"],
                "bundles": ["MobilityPromotionTreatmentRules", "MobilityDeviceTreatmentRules"]
            }
        })

def get_logs_from_elasticsearch_enhanced(app: str, cluster: str, bundle: str, limit: int = 100) -> Dict[str, Any]:
    """Get logs from Elasticsearch with proper value mapping - FIXED VERSION"""
    try:
        # First check if Elasticsearch is available
        if not elasticsearch_service.is_available():
            logger.error("❌ Elasticsearch is not available")
            return {'logs': [], 'total': 0, 'error': 'Elasticsearch not available'}
        
        # Map frontend values to Elasticsearch values
        mapped_app, mapped_cluster, mapped_bundle, mapped_pod = map_frontend_to_elasticsearch_values(
            app, cluster, bundle, None  # We'll handle pod separately
        )
        
        # Try exact match first with mapped values
        query_params = {
            'application': mapped_app,
            'cluster': mapped_cluster, 
            'bundle': mapped_bundle,
            'size': limit,
            'page': 1
        }
        
        logger.info(f"🔍 Searching Elasticsearch with MAPPED params: {query_params}")
        
        # Search in Elasticsearch with mapped values
        result = elasticsearch_service.search_logs(query_params)
        
        if result and result.get('logs') and len(result['logs']) > 0:
            logger.info(f"✅ Found {len(result['logs'])} logs from Elasticsearch (mapped values)")
            return result
        
        # If no mapped match, try original values (fallback)
        logger.info(f"🔍 No mapped match found, trying original values...")
        
        original_query_params = {
            'application': app,
            'cluster': cluster, 
            'bundle': bundle,
            'size': limit,
            'page': 1
        }
        
        result_original = elasticsearch_service.search_logs(original_query_params)
        
        if result_original and result_original.get('logs') and len(result_original['logs']) > 0:
            logger.info(f"✅ Found {len(result_original['logs'])} logs from Elasticsearch (original values)")
            return result_original
        
        logger.warning(f"⚠️ No logs found in Elasticsearch for {app}-{cluster}-{bundle} (tried both mapped and original)")
        return {'logs': [], 'total': 0, 'error': 'No logs found'}
        
    except Exception as e:
        logger.error(f"❌ Error getting logs from Elasticsearch: {str(e)}")
        return {'logs': [], 'total': 0, 'error': str(e)}

@csrf_exempt
def index(request):
    """Enhanced main view with ELK integration - UPDATED VERSION"""
    context = {}

    if request.method == 'POST':
        app = request.POST.get('application', '').strip()
        cluster = request.POST.get('cluster', '').strip()
        bundle = request.POST.get('testtype', '').strip()

        # Validate required fields
        if not all([app, cluster, bundle]):
            context['log'] = "❌ Error: Please select Application, Cluster, and Bundle before running the test."
            return render(request, 'app/index.html', context)

        logger.info(f"🚀 Processing request for: {app} - {cluster} - {bundle}")

        # FIRST: Check if Elasticsearch is available
        if elasticsearch_service.is_available():
            logger.info("✅ Elasticsearch is available - searching for logs")
            
            # Try to get logs from Elasticsearch with enhanced search
            es_logs = get_logs_from_elasticsearch_enhanced(app, cluster, bundle)
            
            # Check if we got actual logs from Elasticsearch
            if es_logs and es_logs.get('logs') and len(es_logs['logs']) > 0:
                # SUCCESS: We got logs from Elasticsearch
                formatted_logs = format_elasticsearch_logs(es_logs['logs'])
                context['log'] = formatted_logs
                context['log_source'] = 'elasticsearch'
                context['total_logs'] = es_logs.get('total', 0)
                logger.info(f"✅ Successfully loaded {len(es_logs['logs'])} logs from Elasticsearch")
            else:
                # No logs found in Elasticsearch, try to create some
                logger.warning(f"⚠️ No logs found in Elasticsearch for {app}-{cluster}-{bundle}")
                logger.info("📊 Creating sample data for this combination...")
                
                # Generate and index sample logs for this specific combination
                sample_logs = generate_specific_sample_logs(app, cluster, bundle)
                if sample_logs:
                    result = elasticsearch_service.bulk_index_logs(sample_logs)
                    logger.info(f"✅ Created {result['indexed']} sample logs")
                    
                    # Now try to get the logs again
                    es_logs = get_logs_from_elasticsearch_enhanced(app, cluster, bundle)
                    if es_logs and es_logs.get('logs'):
                        formatted_logs = format_elasticsearch_logs(es_logs['logs'])
                        context['log'] = formatted_logs
                        context['log_source'] = 'elasticsearch'
                        context['total_logs'] = es_logs.get('total', 0)
                    else:
                        # Still no logs, fallback
                        logger.warning("❌ Still no logs after creating samples, using fallback")
                        context.update(get_file_based_logs(app, cluster, bundle))
                else:
                    # Fallback to file-based logs
                    logger.warning("❌ Failed to create sample logs, using fallback")
                    context.update(get_file_based_logs(app, cluster, bundle))
        else:
            # Elasticsearch is not available
            logger.error("❌ Elasticsearch is not available, using fallback")
            context.update(get_file_based_logs(app, cluster, bundle))

        context.update({
            "selected_app": app,
            "selected_cluster": cluster,
            "selected_test": bundle,
        })

    return render(request, 'index.html', context)

def format_elasticsearch_logs(logs: List[Dict[str, Any]]) -> str:
    """Format Elasticsearch logs for display - ENHANCED FOR CLOUD"""
    try:
        if not logs:
            return "No logs found in Elasticsearch"
            
        formatted_lines = []
        
        # Enhanced header to show cloud vs local
        es_host = getattr(elasticsearch_service, 'base_url', 'Unknown')
        is_cloud = 'cloud.es.io' in es_host
        source_type = "☁️ Cloud Elasticsearch" if is_cloud else "🏠 Local Elasticsearch"
        
        formatted_lines.append("# ====================================")
        formatted_lines.append("# Source: elasticsearch")
        formatted_lines.append(f"# Type: {source_type}")
        formatted_lines.append(f"# Total logs: {len(logs)}")
        formatted_lines.append(f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if is_cloud:
            formatted_lines.append("# Endpoint: Elastic Cloud")
        formatted_lines.append("# ====================================")
        formatted_lines.append("")
        
        for log in logs:
            timestamp = log.get('@timestamp', log.get('timestamp', ''))
            level = log.get('log_level', 'INFO')
            message = log.get('log_message', log.get('message', ''))
            pod = log.get('pod', '')
            
            # Format timestamp properly
            if timestamp:
                try:
                    if 'T' in timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            # Format similar to original log format
            if timestamp and level and message:
                formatted_line = f"[{timestamp}] {level}: {message}"
                if pod:
                    formatted_line += f" [pod: {pod}]"
                formatted_lines.append(formatted_line)
        
        return "\n".join(formatted_lines)
        
    except Exception as e:
        logger.error(f"❌ Error formatting Elasticsearch logs: {str(e)}")
        return f"Error formatting logs: {str(e)}"

@require_GET
@csrf_exempt
def connection_status(request):
    """Get current connection status for debugging"""
    try:
        status = {
            'elasticsearch': {
                'available': elasticsearch_service.is_available(),
                'host': getattr(elasticsearch_service, 'base_url', 'Unknown'),
                'is_cloud': 'cloud.es.io' in getattr(elasticsearch_service, 'base_url', ''),
                'auth_configured': hasattr(elasticsearch_service, 'auth_headers')
            },
            'together_ai': {
                'configured': bool(TOGETHER_API_KEY),
                'key_preview': f"{TOGETHER_API_KEY[:10]}..." if TOGETHER_API_KEY else None
            },
            'environment': {
                'django_env': getattr(settings, 'DJANGO_ENV', 'unknown'),
                'debug': getattr(settings, 'DEBUG', False),
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Test Elasticsearch connection
        if elasticsearch_service.is_available():
            try:
                health = elasticsearch_service.get_health_status()
                status['elasticsearch']['cluster_name'] = health.get('cluster_name', 'Unknown')
                status['elasticsearch']['status'] = health.get('status', 'Unknown')
            except Exception as e:
                status['elasticsearch']['error'] = str(e)
        
        return JsonResponse(status)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def generate_specific_sample_logs(app: str, cluster: str, bundle: str) -> List[Dict[str, Any]]:
    """Generate sample logs for a specific app/cluster/bundle combination"""
    import random
    
    try:
        log_messages = {
            'INFO': [
                'Service started successfully',
                'Processing request completed',
                'Health check passed',
                'Database connection established',
                'User authenticated successfully',
                f'Request processed in {random.randint(50, 200)}ms',
                f'Cache hit for key: user_{random.randint(1000, 9999)}',
                'Background job completed',
                'Configuration loaded successfully',
                'Transaction completed successfully'
            ],
            'WARN': [
                f'High memory usage detected: {random.randint(75, 90)}%',
                f'Response time degradation: {random.uniform(1.5, 3.0):.1f}s',
                f'Queue backlog growing: {random.randint(50, 200)} pending items',
                f'Connection pool near capacity: {random.randint(80, 95)}%',
                f'Cache miss ratio high: {random.randint(25, 45)}%',
                f'Slow query detected: {random.randint(1000, 3000)}ms'
            ],
            'ERROR': [
                f'Database connection timeout after {random.randint(30, 60)}s',
                'Failed to process request: connection refused',
                'Authentication failed: invalid credentials',
                'OutOfMemoryError: Java heap space',
                'Network timeout: connection reset by peer',
                'Service temporarily unavailable',
                'Invalid request format'
            ]
        }
        
        sample_logs = []
        base_time = datetime.now() - timedelta(hours=2)
        
        # Generate 3 pods for this specific combination
        for pod_num in range(1, 4):
            pod_name = f"{app.lower()}-{bundle.lower()}-web-{pod_num:03d}"
            
            # Generate 20-30 logs per pod
            log_count = random.randint(20, 30)
            
            for _ in range(log_count):
                # Random time within the last 2 hours
                log_time = base_time + timedelta(
                    minutes=random.randint(0, 120),
                    seconds=random.randint(0, 59)
                )
                
                # Weight log levels: 70% INFO, 20% WARN, 10% ERROR
                level = random.choices(
                    ['INFO', 'WARN', 'ERROR'],
                    weights=[70, 20, 10]
                )[0]
                
                # Select message
                message = random.choice(log_messages[level])
                
                # Create log entry
                log_entry = {
                    '@timestamp': log_time.isoformat(),
                    'timestamp': log_time.isoformat(),
                    'application': app,
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
                    log_entry['response_time'] = round(random.uniform(0.1, 2.0), 3)
                
                if random.random() < 0.2:
                    log_entry['status_code'] = random.choice([200, 201, 400, 401, 404, 500])
                
                sample_logs.append(log_entry)
        
        logger.info(f"Generated {len(sample_logs)} sample logs for {app}-{cluster}-{bundle}")
        return sample_logs
        
    except Exception as e:
        logger.error(f"Error generating sample logs: {str(e)}")
        return []

def get_file_based_logs(app: str, cluster: str, bundle: str) -> Dict[str, Any]:
    """Fallback to original file-based log retrieval"""
    context = {}
    
    # Generate log file name with timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_name = f"{sanitize_filename(app)}-{sanitize_filename(bundle)}-{timestamp}.log"
    log_file_path = os.path.join("app", "static", "logs", log_file_name)

    # Try to find existing log file (without timestamp)
    simple_log_name = f"{sanitize_filename(app)}-{sanitize_filename(bundle)}.log"
    simple_log_path = os.path.join("app", "static", "logs", simple_log_name)

    try:
        if os.path.exists(simple_log_path):
            with open(simple_log_path, "r", encoding='utf-8') as f:
                log_content = f.read()
            context['log'] = log_content
            context['log_file_name'] = simple_log_name
            context['log_source'] = 'file'
            logger.info(f"Successfully loaded log file: {simple_log_path}")
        elif os.path.exists(log_file_path):
            with open(log_file_path, "r", encoding='utf-8') as f:
                log_content = f.read()
            context['log'] = log_content
            context['log_file_name'] = log_file_name
            context['log_source'] = 'file'
            logger.info(f"Successfully loaded log file: {log_file_path}")
        else:
            # Auto-generate logs
            log_content = auto_generate_pod_logs(app, cluster, bundle, f"{app}-{bundle}-pod")
            
            # Add header to show it's auto-generated
            header = f"""# ====================================
# Source: auto-generated
# Application: {app}
# Cluster: {cluster}
# Bundle: {bundle}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ====================================

"""
            context['log'] = header + log_content
            context['log_file_name'] = None
            context['log_source'] = 'auto-generated'
            
            logger.warning(f"Generated new logs for {app}-{cluster}-{bundle}")
            
    except UnicodeDecodeError:
        context['log'] = "❌ Error: Log file contains invalid characters. Please check the file encoding."
        context['log_file_name'] = None
        logger.error(f"Unicode decode error for log file: {simple_log_path}")
    except Exception as e:
        context['log'] = f"❌ Error reading log file: {str(e)}"
        context['log_file_name'] = None
        logger.error(f"Error reading log file {simple_log_path}: {str(e)}")

    return context

def index_generated_logs_to_elasticsearch(log_content: str, app: str, cluster: str, bundle: str):
    """Index newly generated logs to Elasticsearch"""
    try:
        lines = log_content.strip().split('\n')
        log_entries = []
        
        for line in lines:
            if line.strip() and not line.startswith('#'):
                log_entry = {
                    '@timestamp': datetime.now().isoformat(),
                    'timestamp': datetime.now().isoformat(),
                    'log_message': line,
                    'message': line,
                    'application': app,
                    'cluster': cluster,
                    'bundle': bundle,
                    'pod': f"{app}-{bundle}-pod",
                    'log_level': 'INFO',
                    'source_file': 'auto-generated'
                }
                log_entries.append(log_entry)
        
        if log_entries:
            result = elasticsearch_service.bulk_index_logs(log_entries)
            logger.info(f"Indexed {result['indexed']} generated logs to Elasticsearch")
            
    except Exception as e:
        logger.error(f"Error indexing generated logs: {str(e)}")

@require_POST
@csrf_exempt
def search_logs_elasticsearch(request):
    """Search logs in Elasticsearch with advanced filters"""
    try:
        # Get search parameters
        search_text = request.POST.get('search_text', '').strip()
        application = request.POST.get('application', '').strip()
        cluster = request.POST.get('cluster', '').strip()
        bundle = request.POST.get('bundle', '').strip()
        pod = request.POST.get('pod', '').strip()
        log_level = request.POST.get('log_level', '').strip()
        start_time = request.POST.get('start_time', '').strip()
        end_time = request.POST.get('end_time', '').strip()
        page = int(request.POST.get('page', 1))
        size = int(request.POST.get('size', 50))
        
        # Build query parameters
        query_params = {
            'page': page,
            'size': size
        }
        
        if search_text:
            query_params['search_text'] = search_text
        if application:
            query_params['application'] = application
        if cluster:
            query_params['cluster'] = cluster
        if bundle:
            query_params['bundle'] = bundle
        if pod:
            query_params['pod'] = pod
        if log_level:
            query_params['log_level'] = log_level
        if start_time:
            query_params['start_time'] = start_time
        if end_time:
            query_params['end_time'] = end_time
        
        # Search in Elasticsearch
        result = elasticsearch_service.search_logs(query_params)
        
        if result.get('error'):
            return JsonResponse({
                'success': False,
                'error': result['error'],
                'logs': []
            })
        
        # Format logs for frontend
        formatted_logs = []
        for log in result.get('logs', []):
            formatted_log = {
                'id': log.get('_id'),
                'timestamp': log.get('@timestamp', log.get('timestamp')),
                'application': log.get('application'),
                'cluster': log.get('cluster'),
                'bundle': log.get('bundle'),
                'pod': log.get('pod'),
                'log_level': log.get('log_level'),
                'message': log.get('log_message', log.get('message')),
                'response_time': log.get('response_time'),
                'status_code': log.get('status_code'),
                'error_type': log.get('error_type')
            }
            formatted_logs.append(formatted_log)
        
        return JsonResponse({
            'success': True,
            'logs': formatted_logs,
            'total': result.get('total', 0),
            'page': result.get('page', 1),
            'pages': result.get('pages', 1),
            'size': result.get('size', size)
        })
        
    except Exception as e:
        logger.error(f"Error searching logs in Elasticsearch: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'logs': []
        })

@require_POST
@csrf_exempt
def get_pods(request):
    """Enhanced pod discovery with Elasticsearch integration"""
    try:
        app = request.POST.get('application', '').strip()
        cluster = request.POST.get('cluster', '').strip()
        bundle = request.POST.get('bundle', '').strip()

        # Validate required fields
        if not all([app, cluster, bundle]):
            return JsonResponse({
                "error": "Missing required parameters",
                "pods": []
            }, status=400)

        # Create cache key for this specific combination
        cache_key = f"pods_{sanitize_filename(app)}_{sanitize_filename(cluster)}_{sanitize_filename(bundle)}"
        
        # Try to get from cache first
        cached_pods = cache.get(cache_key)
        if cached_pods:
            logger.debug(f"Returning cached pods for {app}-{cluster}-{bundle}")
            return JsonResponse({"pods": cached_pods})

        # Try to get pods from Elasticsearch first
        es_pods = get_pods_from_elasticsearch(app, cluster, bundle)
        
        if es_pods:
            pods = es_pods
            logger.info(f"Found {len(pods)} pods from Elasticsearch for {app}-{cluster}-{bundle}")
        else:
            # Fallback to configuration file
            pods = get_pods_from_config(app, cluster, bundle)
            
            if not pods:
                # Generate sample pods
                pods = generate_sample_pods(app, bundle)
                logger.info(f"Generated {len(pods)} sample pods for {app}-{cluster}-{bundle}")

        # Cache the pods for future requests
        cache.set(cache_key, pods, PODS_CACHE_TIMEOUT)
        
        return JsonResponse({"pods": pods})

    except Exception as e:
        logger.error(f"Error getting pods: {str(e)}")
        return JsonResponse({
            "error": f"Failed to get pods: {str(e)}",
            "pods": []
        }, status=500)

def get_pods_from_elasticsearch(app: str, cluster: str, bundle: str) -> List[Dict[str, str]]:
    """Get unique pod names from Elasticsearch with proper mapping"""
    try:
        # Map the values first
        mapped_app, mapped_cluster, mapped_bundle, _ = map_frontend_to_elasticsearch_values(
            app, cluster, bundle, None
        )
        
        # Get pod statistics from Elasticsearch with mapped values
        query_params = {
            'application': mapped_app,
            'cluster': mapped_cluster,
            'bundle': mapped_bundle
        }
        
        logger.info(f"🔍 Getting pods from ES with mapped values: {query_params}")
        
        stats = elasticsearch_service.get_log_statistics(query_params)
        
        if stats and 'pods' in stats:
            pods = []
            for pod_name, count in stats['pods'].items():
                # Create user-friendly display name
                display_name = pod_name.replace('-', ' ').title()
                display_name = f"{display_name} ({count} logs)"
                
                pods.append({
                    "name": pod_name,  # Keep original pod name for searches
                    "display_name": display_name
                })
            
            logger.info(f"✅ Found {len(pods)} pods from Elasticsearch")
            return pods
        
        logger.warning("⚠️ No pods found in Elasticsearch statistics")
        return []
        
    except Exception as e:
        logger.error(f"Error getting pods from Elasticsearch: {str(e)}")
        return []

def get_pods_from_config(app: str, cluster: str, bundle: str) -> List[Dict[str, str]]:
    """Get pods from configuration file"""
    try:
        pods_config_path = os.path.join("app", "static", "pods_config.json")
        
        if os.path.exists(pods_config_path):
            with open(pods_config_path, 'r', encoding='utf-8') as f:
                pods_config = json.load(f)
            
            # Navigate through the configuration hierarchy
            app_config = pods_config.get(app, {})
            cluster_config = app_config.get(cluster, {})
            bundle_pods = cluster_config.get(bundle, [])
            
            if isinstance(bundle_pods, list):
                return bundle_pods
        
        return []
        
    except Exception as e:
        logger.error(f"Error reading pods config: {str(e)}")
        return []

@require_POST
@csrf_exempt
def get_pod_logs(request):
    """Enhanced pod log retrieval with ELK integration"""
    try:
        app = request.POST.get('application', '').strip()
        cluster = request.POST.get('cluster', '').strip()
        bundle = request.POST.get('bundle', '').strip()
        pod = request.POST.get('pod', '').strip()

        # Validate required fields
        if not all([app, cluster, bundle, pod]):
            return JsonResponse({
                "error": "Missing required parameters",
                "logs": ""
            }, status=400)

        # Create cache key for this specific pod logs
        cache_key = f"pod_logs_{sanitize_filename(app)}_{sanitize_filename(cluster)}_{sanitize_filename(bundle)}_{sanitize_filename(pod)}"
        
        # Try to get from cache first
        cached_logs = cache.get(cache_key)
        if cached_logs:
            logger.debug(f"Returning cached logs for pod {pod}")
            return JsonResponse({"logs": cached_logs})

        # Try to get logs from Elasticsearch first
        es_logs = get_pod_logs_from_elasticsearch(app, cluster, bundle, pod)
        
        if es_logs:
            log_content = es_logs
            found_log_source = "elasticsearch"
        else:
            # Fallback to file-based logs
            log_content, found_log_source = get_pod_logs_from_files(app, cluster, bundle, pod)
            
            if not log_content:
                # Auto-generate logs
                log_content = auto_generate_pod_logs(app, cluster, bundle, pod)
                found_log_source = "auto-generated"
                
                # Index generated logs
                index_generated_logs_to_elasticsearch(log_content, app, cluster, bundle)

        # Add metadata to logs
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_metadata = f"""# LogOps - Enhanced Log Viewer
# Loaded: {timestamp}
# Source: {found_log_source}
# Pod: {pod}
# Application: {app}
# Cluster: {cluster}
# Bundle: {bundle}
# ====================================

"""
        
        final_log_content = log_metadata + log_content

        # Cache the logs for a short time
        cache.set(cache_key, final_log_content, 30)
        
        return JsonResponse({"logs": final_log_content})

    except Exception as e:
        logger.error(f"Error getting pod logs: {str(e)}")
        return JsonResponse({
            "error": f"Failed to get pod logs: {str(e)}",
            "logs": f"Error loading logs for pod {pod}: {str(e)}"
        }, status=500)

def get_pod_logs_from_elasticsearch(app: str, cluster: str, bundle: str, pod: str) -> Optional[str]:
    """Get pod logs from Elasticsearch with proper mapping"""
    try:
        # Map the values
        mapped_app, mapped_cluster, mapped_bundle, mapped_pod = map_frontend_to_elasticsearch_values(
            app, cluster, bundle, pod
        )
        
        query_params = {
            'application': mapped_app,
            'cluster': mapped_cluster,
            'bundle': mapped_bundle,
            'pod': mapped_pod,
            'size': 1000,  # Get more logs for pod view
            'page': 1
        }
        
        logger.info(f"🔍 Searching pod logs with mapped values: {query_params}")
        
        result = elasticsearch_service.search_logs(query_params)
        
        if result.get('logs'):
            return format_elasticsearch_logs(result['logs'])
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting pod logs from Elasticsearch: {str(e)}")
        return None

def get_pod_logs_from_files(app: str, cluster: str, bundle: str, pod: str) -> tuple:
    """Get pod logs from files (original implementation)"""
    # This is a placeholder - implement as needed
    return None, None

# AI Analysis Functions
@require_POST
@csrf_exempt
def summarize_logs(request):
    """Enhanced log summarization with Together.ai and local fallback"""
    log_text = request.POST.get("log_text", "").strip()
    use_together = request.POST.get("use_together", "true").lower() == "true"
    
    if not log_text or log_text in ["Waiting for execution...", "Fetching pod logs..."]:
        return JsonResponse({"summary": "❌ No logs available to summarize."})

    try:
        # Try Together.ai first if API key is available
        if TOGETHER_API_KEY and use_together:
            together_summary = get_together_ai_summary(log_text)
            if together_summary and not together_summary.startswith("❌"):
                return JsonResponse({
                    "summary": together_summary,
                    "ai_service": "together_ai",
                    "model": "meta-llama/Llama-3-8b-chat-hf"
                })
        
        # Fallback to local analysis
        local_summary = generate_local_summary(log_text)
        return JsonResponse({
            "summary": local_summary,
            "ai_service": "local_ai",
            "model": "LogOps Pattern Analysis Engine"
        })
        
    except Exception as e:
        logger.error(f"Error in log summarization: {str(e)}")
        return JsonResponse({"summary": f"❌ Unexpected error: {str(e)}"})

@csrf_exempt
def analyze_logs(request):
    """Enhanced root cause analysis with Together.ai and local fallback"""
    log_text = request.POST.get("log_text", "").strip()
    use_together = request.POST.get("use_together", "true").lower() == "true"
    
    if not log_text or log_text in ["Waiting for execution...", "Fetching pod logs..."]:
        return JsonResponse({"analysis": "❌ No logs available for root cause analysis."})

    try:
        # Try Together.ai first if API key is available
        if TOGETHER_API_KEY and use_together:
            together_analysis = get_together_ai_analysis(log_text)
            if together_analysis and not together_analysis.startswith("❌"):
                return JsonResponse({
                    "analysis": together_analysis,
                    "ai_service": "together_ai",
                    "model": "meta-llama/Llama-3-8b-chat-hf"
                })
        
        # Fallback to local analysis
        local_analysis = generate_local_rca(log_text)
        return JsonResponse({
            "analysis": local_analysis,
            "ai_service": "local_ai",
            "model": "LogOps RCA Engine"
        })
        
    except Exception as e:
        logger.error(f"Error in log analysis: {str(e)}")
        return JsonResponse({"analysis": f"❌ Unexpected error: {str(e)}"})

def get_together_ai_summary(log_text: str) -> str:
    """Get summary from Together.ai"""
    try:
        # Check for log text length
        if len(log_text) > 8000:
            log_text = log_text[:8000] + "\n... (truncated for analysis)"

        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "meta-llama/Llama-3-8b-chat-hf",
            "messages": [
                {
                    "role": "system",
                    "content": """You are an expert DevOps engineer who specializes in analyzing application logs. 
                    Provide a clear, concise summary that includes:
                    1. Overall status (Success/Failure/Warning)
                    2. Key events or operations performed
                    3. Any errors or warnings found
                    4. Performance metrics if available
                    5. Actionable recommendations
                    Keep the summary under 300 words and use bullet points for clarity."""
                },
                {
                    "role": "user",
                    "content": f"Analyze and summarize this application log:\n\n{log_text}"
                }
            ],
            "max_tokens": 500,
            "temperature": 0.3,
            "top_p": 0.9
        }
        
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions", 
            headers=headers, 
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            summary = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if summary:
                # Add Together.ai branding
                ai_summary = f"🤖 **Together.ai Analysis** (Llama-3-8b)\n\n{summary.strip()}"
                ai_summary += f"\n\n📊 **Analysis Metadata:**\n"
                ai_summary += f"• Model: meta-llama/Llama-3-8b-chat-hf\n"
                ai_summary += f"• Service: Together.ai Cloud AI\n"
                ai_summary += f"• Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                return ai_summary
            else:
                return "❌ Received empty response from Together.ai"
        else:
            logger.error(f"Together.ai API error: {response.status_code} - {response.text}")
            return f"❌ Together.ai API error {response.status_code}: {response.text[:200]}"
            
    except requests.exceptions.Timeout:
        logger.error("Together.ai request timeout")
        return "❌ Together.ai request timeout"
    except Exception as e:
        logger.error(f"Error with Together.ai summary: {str(e)}")
        return f"❌ Together.ai error: {str(e)}"

def get_together_ai_analysis(log_text: str) -> str:
    """Get root cause analysis from Together.ai"""
    try:
        # Check for log text length
        if len(log_text) > 8000:
            log_text = log_text[:8000] + "\n... (truncated for analysis)"

        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "meta-llama/Llama-3-8b-chat-hf",
            "messages": [
                {
                    "role": "system",
                    "content": """You are a senior DevOps engineer specializing in root cause analysis. 
                    Analyze the provided logs and identify:
                    1. Primary errors or failures and their root causes
                    2. Impact assessment (High/Medium/Low)
                    3. Recommended actions to resolve issues
                    4. Prevention strategies for the future
                    5. Timeline of critical events
                    
                    Be specific and actionable in your recommendations. 
                    If no errors are found, indicate successful execution and any optimization opportunities.
                    Provide step-by-step remediation where applicable."""
                },
                {
                    "role": "user",
                    "content": f"Perform comprehensive root cause analysis on this log:\n\n{log_text}"
                }
            ],
            "max_tokens": 600,
            "temperature": 0.3,
            "top_p": 0.9
        }
        
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions", 
            headers=headers, 
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            analysis = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if analysis:
                # Add Together.ai branding
                ai_analysis = f"🔬 **Together.ai Root Cause Analysis** (Llama-3-8b)\n\n{analysis.strip()}"
                ai_analysis += f"\n\n📊 **Analysis Metadata:**\n"
                ai_analysis += f"• Model: meta-llama/Llama-3-8b-chat-hf\n"
                ai_analysis += f"• Service: Together.ai Cloud AI\n"
                ai_analysis += f"• Analysis Method: Large Language Model\n"
                ai_analysis += f"• Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                return ai_analysis
            else:
                return "❌ Received empty response from Together.ai"
        else:
            logger.error(f"Together.ai API error: {response.status_code} - {response.text}")
            return f"❌ Together.ai API error {response.status_code}: {response.text[:200]}"
            
    except requests.exceptions.Timeout:
        logger.error("Together.ai request timeout")
        return "❌ Together.ai request timeout"
    except Exception as e:
        logger.error(f"Error with Together.ai analysis: {str(e)}")
        return f"❌ Together.ai error: {str(e)}"

def generate_local_summary(log_text: str) -> str:
    """Generate local summary when Together.ai is not available"""
    try:
        lines = log_text.split('\n')
        
        # Count log levels
        info_count = len([line for line in lines if 'INFO' in line])
        warn_count = len([line for line in lines if 'WARN' in line])
        error_count = len([line for line in lines if 'ERROR' in line])
        
        # Analyze patterns
        summary = f"📊 **Local Log Analysis Engine**\n\n"
        summary += f"**Log Summary:**\n"
        summary += f"• Total log entries: {len([line for line in lines if line.strip()])}\n"
        summary += f"• INFO messages: {info_count}\n"
        summary += f"• WARN messages: {warn_count}\n"
        summary += f"• ERROR messages: {error_count}\n\n"
        
        if error_count > 0:
            summary += f"**Status: ⚠️ ERRORS DETECTED**\n"
            summary += f"• {error_count} error(s) found requiring attention\n"
        elif warn_count > 0:
            summary += f"**Status: ⚡ WARNINGS PRESENT**\n"
            summary += f"• {warn_count} warning(s) detected\n"
        else:
            summary += f"**Status: ✅ HEALTHY**\n"
            summary += f"• No errors or warnings detected\n"
        
        summary += f"\n**Recommendations:**\n"
        if error_count > 0:
            summary += f"• Immediate investigation required for errors\n"
        if warn_count > 0:
            summary += f"• Monitor warnings for potential issues\n"
        summary += f"• Continue monitoring system health\n"
        
        summary += f"\n📈 **Analysis Engine:** LogOps Pattern Analyzer\n"
        summary += f"🕒 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return summary
        
    except Exception as e:
        return f"❌ Error generating local summary: {str(e)}"

def generate_local_rca(log_text: str) -> str:
    """Generate local root cause analysis when Together.ai is not available"""
    try:
        lines = log_text.split('\n')
        
        # Find errors and warnings
        errors = [line for line in lines if 'ERROR' in line]
        warnings = [line for line in lines if 'WARN' in line]
        
        analysis = f"🔍 **Local Root Cause Analysis Engine**\n\n"
        
        if errors:
            analysis += f"**🚨 Critical Issues Found ({len(errors)}):**\n"
            for i, error in enumerate(errors[:3], 1):  # Show first 3 errors
                analysis += f"{i}. {error.strip()}\n"
            if len(errors) > 3:
                analysis += f"... and {len(errors) - 3} more errors\n"
            analysis += f"\n"
            
            analysis += f"**Root Cause Assessment:**\n"
            if "timeout" in log_text.lower():
                analysis += f"• Connection timeouts detected - network or database issues\n"
            if "memory" in log_text.lower():
                analysis += f"• Memory-related issues detected - potential resource constraints\n"
            if "connection" in log_text.lower():
                analysis += f"• Connection issues detected - service availability problems\n"
            
            analysis += f"\n**Immediate Actions:**\n"
            analysis += f"1. Check service health and connectivity\n"
            analysis += f"2. Review system resources (CPU, memory, disk)\n"
            analysis += f"3. Verify database and network connectivity\n"
            analysis += f"4. Check for recent deployments or configuration changes\n"
        
        elif warnings:
            analysis += f"**⚠️ Warning Conditions ({len(warnings)}):**\n"
            for i, warning in enumerate(warnings[:3], 1):
                analysis += f"{i}. {warning.strip()}\n"
            if len(warnings) > 3:
                analysis += f"... and {len(warnings) - 3} more warnings\n"
            
            analysis += f"\n**Preventive Actions:**\n"
            analysis += f"1. Monitor system metrics closely\n"
            analysis += f"2. Consider scaling resources if needed\n"
            analysis += f"3. Review performance thresholds\n"
        
        else:
            analysis += f"**✅ System Operating Normally**\n"
            analysis += f"• No critical errors detected\n"
            analysis += f"• System appears healthy\n"
            analysis += f"\n**Optimization Opportunities:**\n"
            analysis += f"1. Continue monitoring for trends\n"
            analysis += f"2. Review performance metrics\n"
            analysis += f"3. Consider proactive maintenance\n"
        
        analysis += f"\n🔧 **Analysis Method:** Pattern Recognition & Keyword Analysis\n"
        analysis += f"🕒 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return analysis
        
    except Exception as e:
        return f"❌ Error generating local RCA: {str(e)}"

# Health and System Status Endpoints
@require_GET
@csrf_exempt
def test_together_ai(request):
    """Test Together.ai API connection"""
    try:
        if not TOGETHER_API_KEY:
            return JsonResponse({"status": "error", "message": "No API key configured"})
        
        test_summary = get_together_ai_summary("INFO: Test log entry for API validation")
        
        if test_summary and not test_summary.startswith("❌"):
            return JsonResponse({"status": "success", "message": "Together.ai API working"})
        else:
            return JsonResponse({"status": "error", "message": test_summary})
            
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

@require_GET
@csrf_exempt
def elasticsearch_health(request):
    """Get Elasticsearch health status"""
    try:
        health = elasticsearch_service.get_health_status()
        return JsonResponse(health)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@csrf_exempt
def system_overview(request):
    """Get comprehensive system overview"""
    try:
        overview = {
            'elasticsearch': elasticsearch_service.get_health_status(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Get log statistics
        if overview['elasticsearch']['status'] != 'error':
            overview['log_stats'] = elasticsearch_service.get_log_statistics()
        
        return JsonResponse(overview)
        
    except Exception as e:
        logger.error(f"Error getting system overview: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
def test_elasticsearch_connection(request):
    try:
        es = elasticsearch_service.get_elasticsearch_client()
        info = es.info()
        return JsonResponse({"status": "success", "cluster_name": info['cluster_name']})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

# Helper Functions
def generate_sample_pods(app, bundle):
    """Generate sample pods for demo purposes"""
    base_pods = [
        f"{sanitize_filename(app)}-{sanitize_filename(bundle)}-web-001",
        f"{sanitize_filename(app)}-{sanitize_filename(bundle)}-web-002", 
        f"{sanitize_filename(app)}-{sanitize_filename(bundle)}-api-001",
        f"{sanitize_filename(app)}-{sanitize_filename(bundle)}-worker-001",
        f"{sanitize_filename(app)}-{sanitize_filename(bundle)}-error-pod",
        f"{sanitize_filename(app)}-{sanitize_filename(bundle)}-warn-service"
    ]
    
    return [
        {
            "name": pod,
            "display_name": pod.replace('_', '-').replace('-error-pod', ' (Error Demo)').replace('-warn-service', ' (Warning Demo)')
        }
        for pod in base_pods
    ]

def auto_generate_pod_logs(app, cluster, bundle, pod):
    """Auto-generate realistic pod logs"""
    base_time = datetime.now() - timedelta(hours=1, minutes=30)
    logs = []
    
    # Add startup sequence
    logs.append(f"[{base_time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: Starting pod {pod}")
    logs.append(f"[{(base_time + timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')}] INFO: Application: {app}")
    logs.append(f"[{(base_time + timedelta(seconds=2)).strftime('%Y-%m-%d %H:%M:%S')}] INFO: Cluster: {cluster}")
    logs.append(f"[{(base_time + timedelta(seconds=3)).strftime('%Y-%m-%d %H:%M:%S')}] INFO: Bundle: {bundle}")
    
    # Add service-specific logs based on pod name
    current_time = base_time + timedelta(seconds=20)
    
    if "error" in pod.lower():
        logs.extend([
            f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: Processing incoming requests...",
            f"[{(current_time + timedelta(seconds=30)).strftime('%Y-%m-%d %H:%M:%S')}] WARN: High memory usage detected: 85%",
            f"[{(current_time + timedelta(seconds=60)).strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Database connection timeout after 30s",
            f"[{(current_time + timedelta(seconds=90)).strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to process request: connection refused",
            f"[{(current_time + timedelta(seconds=120)).strftime('%Y-%m-%d %H:%M:%S')}] FATAL: Critical error - service unavailable"
        ])
    elif "warn" in pod.lower():
        logs.extend([
            f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: Service operational - processing requests",
            f"[{(current_time + timedelta(seconds=45)).strftime('%Y-%m-%d %H:%M:%S')}] WARN: High CPU usage detected: 78%",
            f"[{(current_time + timedelta(seconds=90)).strftime('%Y-%m-%d %H:%M:%S')}] WARN: Response time degradation: 2.8s (SLA: 1s)",
            f"[{(current_time + timedelta(seconds=135)).strftime('%Y-%m-%d %H:%M:%S')}] WARN: Queue backlog growing: 150 pending items"
        ])
    else:
        logs.extend([
            f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: Service running normally",
            f"[{(current_time + timedelta(seconds=60)).strftime('%Y-%m-%d %H:%M:%S')}] INFO: Processed 250 requests in last minute",
            f"[{(current_time + timedelta(seconds=120)).strftime('%Y-%m-%d %H:%M:%S')}] INFO: Health check passed - all systems green",
            f"[{(current_time + timedelta(seconds=180)).strftime('%Y-%m-%d %H:%M:%S')}] INFO: Database queries avg response: 45ms"
        ])
    
    return "\n".join(logs)

# Preserved Legacy Functions
@require_POST
@csrf_exempt
def send_rca_email(request):
    """Send RCA analysis via email"""
    try:
        email = request.POST.get('email', '').strip()
        analysis = request.POST.get('analysis', '').strip()
        pod_name = request.POST.get('pod_name', 'Unknown Pod').strip()
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email address required'})
        
        if not analysis:
            return JsonResponse({'success': False, 'error': 'No analysis to send'})
        
        # Email subject and content
        subject = f"🔬 LogOps RCA Report - {pod_name}"
        
        # Create HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>LogOps RCA Report</title>
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden;">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 40px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: 700;">
                        LogOps Root Cause Analysis
                    </h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">
                        Automated Log Analysis Report
                    </p>
                </div>
                
                <!-- Analysis Details -->
                <div style="padding: 30px 40px;">
                    <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 30px; border-left: 4px solid #3b82f6;">
                        <h3 style="margin: 0 0 15px 0; color: #1f2937; font-size: 18px;"> Analysis Details</h3>
                        <table style="width: 100%; font-size: 14px;">
                            <tr>
                                <td style="padding: 5px 0; font-weight: 600; color: #6b7280; width: 120px;">Pod:</td>
                                <td style="padding: 5px 0; color: #111827;">{pod_name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px 0; font-weight: 600; color: #6b7280;">Generated:</td>
                                <td style="padding: 5px 0; color: #111827;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px 0; font-weight: 600; color: #6b7280;">Sent to:</td>
                                <td style="padding: 5px 0; color: #111827;">{email}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Analysis Content -->
                    <div style="background: white; padding: 25px; border: 2px solid #e5e7eb; border-radius: 12px; margin-bottom: 30px;">
                        <h3 style="color: #dc2626; margin: 0 0 20px 0; font-size: 20px; border-bottom: 2px solid #fee2e2; padding-bottom: 10px;">
                             Root Cause Analysis Results
                        </h3>
                        <div style="white-space: pre-wrap; font-family: 'Courier New', Consolas, Monaco, monospace; font-size: 13px; line-height: 1.6; background: #f9fafb; padding: 20px; border-radius: 6px; border: 1px solid #e5e7eb; overflow-x: auto;">
{analysis}
                        </div>
                    </div>
                    
                    <!-- Footer -->
                    <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <p style="margin: 0; font-size: 14px;">
                            Generated by <strong>LogOps</strong> - Enhanced Log Analysis Platform
                        </p>
                        <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.8;">
                            Powered by Elasticsearch Cloud & Together.ai
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version for email clients that don't support HTML
        text_content = f"""
LogOps Root Cause Analysis Report
================================

Pod: {pod_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Sent to: {email}

ROOT CAUSE ANALYSIS RESULTS:
{analysis}

---
This report was generated by LogOps - Enhanced Log Analysis Platform
Powered by Elasticsearch Cloud & Together.ai
        """
        
        # Send email using Django's EmailMultiAlternatives
        try:
            from django.core.mail import EmailMultiAlternatives
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"✅ RCA email sent successfully to {email} for pod {pod_name}")
            return JsonResponse({
                'success': True, 
                'message': f'RCA report sent successfully to {email}!'
            })
            
        except Exception as email_error:
            logger.error(f"❌ Failed to send email to {email}: {str(email_error)}")
            return JsonResponse({
                'success': False, 
                'error': f'Failed to send email: {str(email_error)}. Please check your email settings.'
            })
        
    except Exception as e:
        logger.error(f"❌ Error in send_rca_email: {str(e)}")
        return JsonResponse({
            'success': False, 
            'error': f'Email sending failed: {str(e)}'
        })

def track_download(request):
    """Download tracking preserved for backward compatibility"""
    return JsonResponse({'success': True, 'message': 'Download tracking preserved'})

def get_download_stats(request):
    """Download stats preserved for backward compatibility"""
    return JsonResponse({'success': True, 'stats': {}})

def health_check(request):
    """Basic health check endpoint"""
    return JsonResponse({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

