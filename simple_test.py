#!/usr/bin/env python
"""
Simple test to check Django-Elasticsearch integration
Run this: python simple_test.py
"""

import requests
import json

def test_direct_search():
    """Test direct Elasticsearch search for FOBPM data"""
    print("🔍 Testing Direct Elasticsearch Search...")
    
    # Search for FOBPM documents
    search_query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"application.keyword": "FOBPM"}},
                    {"term": {"cluster.keyword": "Cluster Prod AKS 1"}},
                    {"term": {"bundle.keyword": "Bulkdeviceenrollment"}}
                ]
            }
        },
        "size": 5,
        "sort": [{"@timestamp": {"order": "desc"}}]
    }
    
    try:
        response = requests.post(
            "http://localhost:9200/logops-logs-*/_search",
            json=search_query,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            hits = data['hits']['hits']
            total = data['hits']['total']['value']
            
            print(f"✅ Found {total} total documents")
            print(f"📝 Retrieved {len(hits)} documents")
            
            if hits:
                print("📄 Sample document:")
                doc = hits[0]['_source']
                print(f"   Application: {doc.get('application')}")
                print(f"   Cluster: {doc.get('cluster')}")
                print(f"   Bundle: {doc.get('bundle')}")
                print(f"   Pod: {doc.get('pod')}")
                print(f"   Message: {doc.get('log_message', doc.get('message', 'N/A'))}")
                
                return True
            else:
                print("❌ No documents found for FOBPM-Cluster Prod AKS 1-Bulkdeviceenrollment")
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def test_aggregations():
    """Test what applications/clusters/bundles exist"""
    print("\n🔍 Testing Available Data...")
    
    agg_query = {
        "query": {"match_all": {}},
        "size": 0,
        "aggs": {
            "applications": {"terms": {"field": "application.keyword", "size": 10}},
            "clusters": {"terms": {"field": "cluster.keyword", "size": 10}},
            "bundles": {"terms": {"field": "bundle.keyword", "size": 10}}
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:9200/logops-logs-*/_search",
            json=agg_query,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            aggs = data.get('aggregations', {})
            
            print("📊 Available Applications:")
            for bucket in aggs.get('applications', {}).get('buckets', []):
                print(f"   - {bucket['key']} ({bucket['doc_count']} logs)")
            
            print("📊 Available Clusters:")
            for bucket in aggs.get('clusters', {}).get('buckets', []):
                print(f"   - {bucket['key']} ({bucket['doc_count']} logs)")
            
            print("📊 Available Bundles:")
            for bucket in aggs.get('bundles', {}).get('buckets', []):
                print(f"   - {bucket['key']} ({bucket['doc_count']} logs)")
                
    except Exception as e:
        print(f"❌ Aggregation error: {e}")

def test_without_keyword():
    """Test search without .keyword fields"""
    print("\n🔍 Testing Search Without Keyword Fields...")
    
    search_query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"application": "FOBPM"}},
                    {"match": {"cluster": "Cluster Prod AKS 1"}},
                    {"match": {"bundle": "Bulkdeviceenrollment"}}
                ]
            }
        },
        "size": 5
    }
    
    try:
        response = requests.post(
            "http://localhost:9200/logops-logs-*/_search",
            json=search_query,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data['hits']['total']['value']
            print(f"✅ Found {total} documents with match queries")
            return total > 0
        else:
            print(f"❌ Match query failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Match query error: {e}")
    
    return False

if __name__ == "__main__":
    print("🚀 Testing Elasticsearch Data...")
    print("=" * 50)
    
    # Test 1: Check what data exists
    test_aggregations()
    
    # Test 2: Try exact search
    if not test_direct_search():
        # Test 3: Try without keyword fields
        test_without_keyword()
    
    print("\n" + "=" * 50)
    print("🏁 Test complete!")