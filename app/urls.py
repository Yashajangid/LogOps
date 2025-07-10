
# Add these to your app/urls.py file:

from django.urls import path
from . import views

urlpatterns = [
    # Main page
    path('', views.index, name='index'),
    
    # API endpoints that your JavaScript is calling
    path('api/app-config/', views.get_app_config, name='get_app_config'),
    path('api/pods/', views.get_pods, name='get_pods'),
    path('api/pod-logs/', views.get_pod_logs, name='get_pod_logs'),
    
    # AI Analysis endpoints - THESE ARE MISSING!
    path('api/summarize/', views.summarize_logs, name='summarize_logs'),
    path('api/analyze/', views.analyze_logs, name='analyze_logs'),  # This one is failing
    
    # Other endpoints
    path('api/search-logs/', views.search_logs_elasticsearch, name='search_logs'),
    path('api/connection-status/', views.connection_status, name='connection_status'),
    
    # Health check endpoints
    path('api/elasticsearch-health/', views.elasticsearch_health, name='elasticsearch_health'),
    path('api/system-overview/', views.system_overview, name='system_overview'),
    
    # Legacy endpoints (preserved)
    path('api/send-rca-email/', views.send_rca_email, name='send_rca_email'),
    path('api/track-download/', views.track_download, name='track_download'),
    path('api/download-stats/', views.get_download_stats, name='get_download_stats'),
    path('api/test-together-ai/', views.test_together_ai, name='test_together_ai'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
    path("test-elasticsearch/", views.test_elasticsearch_connection, name="test_elasticsearch"),

]