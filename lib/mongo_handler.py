"""
MongoDB Handler for Behave Test Results
"""
from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict, Any, Optional


class TestDataHandler:
    def __init__(self, connection_string: str, database_name: str = "test_results"):
        """Initialize MongoDB connection"""
        self.client = MongoClient(connection_string)
        self.db = self.client[database_name]
        self.collection = self.db["test_executions"]
        self._create_indexes()
    
    def _create_indexes(self):
        """Create indexes for faster querying"""
        self.collection.create_index([
            ("router_mac", 1),
            ("feature_name", 1),
            ("number_of_clients", 1)
        ])
        self.collection.create_index("test_time")
    
    def store_test_result(self, context) -> str:
        """Store test result from behave context"""
        document = {
            "router_mac": getattr(context, 'router_mac', None),
            "router_firmware": getattr(context, 'router_firmware', None),
            "router_name": getattr(context, 'router_name', None),
            "router_model": getattr(context, 'router_model', None),
            "status": getattr(context, 'status', None),
            "scenario_name": getattr(context, 'scenario_name', None),
            "feature_name": getattr(context, 'feature_name', None),
            "linux_avg_cpu_creation": getattr(context, 'linux_avg_cpu_creation', None),
            "linux_avg_cpu_test": getattr(context, 'linux_avg_cpu_test', None),
            "router_avg_cpu_creation": getattr(context, 'router_avg_cpu_creation', None),
            "router_avg_cpu_test": getattr(context, 'router_avg_cpu_test', None),
            "number_of_clients": getattr(context, 'number_of_clients', None),
            "time_taken": getattr(context, 'time_taken', None),
            "metrics": getattr(context, 'metrics', {}),
            "test_time": getattr(context, 'test_time', datetime.utcnow()),
            "inserted_at": datetime.utcnow()
        }
        
        result = self.collection.insert_one(document)
        return str(result.inserted_id)
    
    def get_filtered_results(
        self, 
        router_mac: str, 
        feature_name: str, 
        number_of_clients: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve filtered test results"""
        query = {
            "router_mac": router_mac,
            "feature_name": feature_name,
            "number_of_clients": number_of_clients
        }
        
        cursor = self.collection.find(query).sort("test_time", -1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        return list(cursor)
    
    def get_all_test_results(self) -> List[Dict[str, Any]]:
        """
        Retrieve all test results from the database
        
        Returns:
            List of all test documents
        """
        return list(self.collection.find({}))
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()

    