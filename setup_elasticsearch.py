import requests
import json
from datetime import datetime

def setup_elasticsearch_mapping():
    """Setup proper Elasticsearch mapping for LogOps"""
    
    base_url = "http://localhost:9200"
    
    # Create index template for logops-logs-*
    template = {
        "index_patterns": ["logops-logs-*"],
        "template": {
            "mappings": {
                "properties": {
                    "@timestamp": {
                        "type": "date"
                    },
                    "timestamp": {
                        "type": "date"
                    },
                    "application": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "cluster": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "bundle": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "pod": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "log_level": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "log_message": {
                        "type": "text"
                    },
                    "message": {
                        "type": "text"
                    },
                    "source_file": {
                        "type": "keyword"
                    },
                    "response_time": {
                        "type": "float"
                    },
                    "status_code": {
                        "type": "integer"
                    }
                }
            }
        }
    }
    
    try:
        # Delete old template if exists
        requests.delete(f"{base_url}/_index_template/logops-template")
        
        # Create new template
        response = requests.put(
            f"{base_url}/_index_template/logops-template",
            json=template,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code in [200, 201]:
            print("✅ Index template created successfully!")
            return True
        else:
            print(f"❌ Failed to create template: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up mapping: {e}")
        return False

if __name__ == "__main__":
    setup_elasticsearch_mapping()