"""
Tests for Entity Capability Registry

Tests schema loading, entity resolution, and metric/tag finding.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import responses

from src.infrastructure.entity_registry import (
    EntityCapability,
    EntityCapabilityRegistry,
)


@pytest.fixture
def sample_schema():
    """Sample schema for testing"""
    return {
        "type": "kubernetesPod",
        "api_endpoint": "/api/infrastructure-monitoring/analyze/entities",
        "parameters": {
            "metrics": {
                "metric": [
                    "cpuRequests",
                    "cpuLimits",
                    "cpuUsed",
                    "memoryRequests",
                    "memoryLimits",
                    "memoryUsed"
                ],
                "aggregation": {
                    "enum": ["mean", "sum", "max", "min"]
                }
            },
            "tagFilterElements": {
                "enum": [
                    "kubernetes.namespace.name",
                    "kubernetes.cluster.name",
                    "kubernetes.pod.name"
                ]
            }
        }
    }


@pytest.fixture
def temp_schema_dir(tmp_path, sample_schema):
    """Create temporary schema directory with test files"""
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()

    # Write sample schema
    schema_file = schema_dir / "kubernetesPod_schema.json"
    with open(schema_file, 'w') as f:
        json.dump(sample_schema, f)

    return schema_dir


class TestEntityCapability:
    """Test EntityCapability dataclass"""

    def test_entity_capability_creation(self):
        """Test creating EntityCapability"""
        capability = EntityCapability(
            entity_type="kubernetesPod",
            api_endpoint="/api/test",
            metrics=["cpu", "memory"],
            tag_filters=["namespace"],
            aggregations=["mean", "sum"]
        )

        assert capability.entity_type == "kubernetesPod"
        assert len(capability.metrics) == 2
        assert len(capability.tag_filters) == 1
        assert len(capability.aggregations) == 2


class TestEntityCapabilityRegistry:
    """Test EntityCapabilityRegistry"""

    def test_registry_initialization(self, temp_schema_dir):
        """Test registry initializes and loads schemas"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        assert "kubernetesPod" in registry._cache
        capability = registry._cache["kubernetesPod"]
        assert capability.entity_type == "kubernetesPod"
        assert len(capability.metrics) == 6
        assert len(capability.tag_filters) == 3
        # Should use fallback mapping when no API credentials provided
        assert len(registry.entity_type_mapping) > 0

    def test_registry_with_nonexistent_dir(self, tmp_path):
        """Test registry handles nonexistent directory gracefully"""
        nonexistent_dir = tmp_path / "nonexistent"
        registry = EntityCapabilityRegistry(schema_dir=nonexistent_dir)

        assert len(registry._cache) == 0

    def test_resolve_entity_success(self, temp_schema_dir):
        """Test resolving entity from normalized intent"""
        registry = EntityCapabilityRegistry(temp_schema_dir)

        capability = registry.resolve("kubernetes", "pod")

        assert capability is not None
        assert capability.entity_type == "kubernetesPod"
        assert len(capability.metrics) > 0

    def test_resolve_entity_unknown(self, temp_schema_dir):
        """Test resolving unknown entity returns None"""
        registry = EntityCapabilityRegistry(temp_schema_dir)

        capability = registry.resolve("unknown", "entity")

        assert capability is None

    def test_find_metric_exact_match(self, temp_schema_dir):
        """Test finding metric with exact category match"""
        registry = EntityCapabilityRegistry(temp_schema_dir)

        metric = registry.find_metric("kubernetesPod", "cpu")

        assert metric is not None
        assert "cpu" in metric.lower()

    def test_find_metric_with_aggregation(self, temp_schema_dir):
        """Test finding metric with aggregation hint"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        metric = registry.find_metric("kubernetesPod", "cpu", "used")

        assert metric is not None
        assert metric == "cpuUsed"

    def test_find_metric_no_match(self, temp_schema_dir):
        """Test finding metric with no matches"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        metric = registry.find_metric("kubernetesPod", "nonexistent")

        assert metric is None

    def test_find_metric_unknown_entity(self, temp_schema_dir):
        """Test finding metric for unknown entity"""
        EntityCapabilityRegistry(schema_dir=temp_schema_dir)


    def test_get_full_schema_success(self, temp_schema_dir):
        """Test getting full schema for entity type"""
        registry = EntityCapabilityRegistry(temp_schema_dir)

        schema = registry.get_full_schema("kubernetesPod")

        assert schema is not None
        assert schema["type"] == "kubernetesPod"
        assert "parameters" in schema
        assert "metrics" in schema["parameters"]
        assert "tagFilterElements" in schema["parameters"]

    def test_get_full_schema_unknown_entity(self, temp_schema_dir):
        """Test getting full schema for unknown entity type"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        schema = registry.get_full_schema("unknownEntity")

        assert schema is None

    def test_get_full_schema_missing_file(self, temp_schema_dir):
        """Test getting full schema when file doesn't exist"""
        registry = EntityCapabilityRegistry(temp_schema_dir)

        # Try to get schema for entity that was loaded but file was deleted
        # First verify entity exists in cache
        assert "kubernetesPod" in registry._cache

        # Delete the schema file
        schema_file = temp_schema_dir / "kubernetesPod_schema.json"
        schema_file.unlink()

        # Now try to get full schema - should return None
        schema = registry.get_full_schema("kubernetesPod")

        assert schema is None
        metric = registry.find_metric("unknownEntity", "cpu")

        assert metric is None

    def test_find_all_matching_metrics(self, temp_schema_dir):
        """Test finding all metrics matching a category"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        metrics = registry.find_all_matching_metrics("kubernetesPod", "cpu")

        assert len(metrics) == 3  # cpuRequests, cpuLimits, cpuUsed
        assert all("cpu" in m.lower() for m in metrics)

    def test_find_tag_filter_success(self, temp_schema_dir):
        """Test finding tag filter"""
        registry = EntityCapabilityRegistry(temp_schema_dir)

        tag = registry.find_tag_filter("kubernetesPod", "namespace")

        assert tag is not None
        assert "namespace" in tag.lower()
        assert tag == "kubernetes.namespace.name"

    def test_find_tag_filter_no_match(self, temp_schema_dir):
        """Test finding tag filter with no match"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        tag = registry.find_tag_filter("kubernetesPod", "nonexistent")

        assert tag is None

    def test_get_all_metrics(self, temp_schema_dir):
        """Test getting all metrics for entity"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        metrics = registry.get_all_metrics("kubernetesPod")

        assert len(metrics) == 6
        assert "cpuRequests" in metrics
        assert "memoryUsed" in metrics

    def test_get_all_tag_filters(self, temp_schema_dir):
        """Test getting all tag filters for entity"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        tags = registry.get_all_tag_filters("kubernetesPod")

        assert len(tags) == 3
        assert "kubernetes.namespace.name" in tags

    def test_get_entity_types(self, temp_schema_dir):
        """Test getting all loaded entity types"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        entity_types = registry.get_entity_types()

        assert "kubernetesPod" in entity_types
        assert len(entity_types) >= 1


class TestSchemaLoading:
    """Test schema loading edge cases"""

    def test_schema_missing_type_field(self, tmp_path):
        """Test handling schema without type field"""
        schema_dir = tmp_path / "schema"
        schema_dir.mkdir()

        invalid_schema = {
            "parameters": {
                "metrics": {"metric": ["test"]}
            }
        }

        schema_file = schema_dir / "invalid_schema.json"
        with open(schema_file, 'w') as f:
            json.dump(invalid_schema, f)

        registry = EntityCapabilityRegistry(schema_dir=schema_dir)

        # Should not crash, just skip invalid schema
        assert len(registry._cache) == 0

    def test_schema_with_empty_metrics(self, tmp_path):
        """Test handling schema with empty metrics"""
        schema_dir = tmp_path / "schema"
        schema_dir.mkdir()

        schema = {
            "type": "testEntity",
            "api_endpoint": "/api/test",
            "parameters": {
                "metrics": {
                    "metric": []
                }
            }
        }

        schema_file = schema_dir / "test_schema.json"
        with open(schema_file, 'w') as f:
            json.dump(schema, f)

        registry = EntityCapabilityRegistry(schema_dir=schema_dir)

        assert "testEntity" in registry._cache
        assert len(registry._cache["testEntity"].metrics) == 0

    def test_multiple_schemas_loaded(self, tmp_path):
        """Test loading multiple schema files"""
        schema_dir = tmp_path / "schema"
        schema_dir.mkdir()

        # Create two schemas
        for entity_type in ["entity1", "entity2"]:
            schema = {
                "type": entity_type,
                "api_endpoint": "/api/test",
                "parameters": {
                    "metrics": {"metric": [f"{entity_type}_metric"]}
                }
            }
            schema_file = schema_dir / f"{entity_type}_schema.json"
            with open(schema_file, 'w') as f:
                json.dump(schema, f)

        registry = EntityCapabilityRegistry(schema_dir=schema_dir)

        assert len(registry._cache) == 2
        assert "entity1" in registry._cache


class TestAPIEntityTypeMapping:
    """Test API-based entity type mapping"""

    @responses.activate
    def test_load_entity_type_mapping_from_api(self, temp_schema_dir):
        """Test loading entity type mapping from API"""
        # Mock API response
        mock_plugins = [
            {"plugin": "kubernetesPod"},
            {"plugin": "kubernetesDeployment"},
            {"plugin": "jvmRuntimePlatform"},
            {"plugin": "host"},
            {"plugin": "docker"},
            {"plugin": "db2Database"},
            {"plugin": "ibmMqQueue"},
            {"plugin": "oTelLLM"}
        ]

        responses.add(
            responses.GET,
            "https://test.instana.io/api/infrastructure-monitoring/catalog/plugins",
            json=mock_plugins,
            status=200
        )

        registry = EntityCapabilityRegistry(
            schema_dir=temp_schema_dir,
            base_url="https://test.instana.io",
            read_token="test-token"
        )

        # Verify mapping was loaded from API
        assert len(registry.entity_type_mapping) > 0
        assert registry.entity_type_mapping.get(("kubernetes", "pod")) == "kubernetesPod"
        assert registry.entity_type_mapping.get(("kubernetes", "deployment")) == "kubernetesDeployment"
        assert registry.entity_type_mapping.get(("jvm", "runtime")) == "jvmRuntimePlatform"
        assert registry.entity_type_mapping.get(("host", "host")) == "host"

    def test_fallback_to_hardcoded_mapping_no_credentials(self, temp_schema_dir):
        """Test fallback to hardcoded mapping when no API credentials provided"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        # Should use fallback mapping
        assert len(registry.entity_type_mapping) > 0
        assert registry.entity_type_mapping.get(("kubernetes", "pod")) == "kubernetesPod"

    @responses.activate
    def test_fallback_to_hardcoded_mapping_api_failure(self, temp_schema_dir):
        """Test fallback to hardcoded mapping when API call fails"""
        # Mock API failure
        responses.add(
            responses.GET,
            "https://test.instana.io/api/infrastructure-monitoring/catalog/plugins",
            json={"error": "Internal Server Error"},
            status=500
        )

        registry = EntityCapabilityRegistry(
            schema_dir=temp_schema_dir,
            base_url="https://test.instana.io",
            read_token="test-token"
        )

        # Should fall back to hardcoded mapping
        assert len(registry.entity_type_mapping) > 0
        assert registry.entity_type_mapping.get(("kubernetes", "pod")) == "kubernetesPod"

    def test_extract_normalized_mappings_kubernetes(self, temp_schema_dir):
        """Test extracting normalized mappings for Kubernetes entities"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        mappings = registry._extract_normalized_mappings("kubernetesPod")
        assert ("kubernetes", "pod") in mappings

        mappings = registry._extract_normalized_mappings("kubernetesDeployment")
        assert ("kubernetes", "deployment") in mappings

    def test_extract_normalized_mappings_special_cases(self, temp_schema_dir):
        """Test extracting normalized mappings for special cases"""
        registry = EntityCapabilityRegistry(schema_dir=temp_schema_dir)

        # Host should map to multiple tuples
        mappings = registry._extract_normalized_mappings("host")
        assert ("host", "host") in mappings
        assert ("infrastructure", "host") in mappings
        assert ("server", "host") in mappings

        # oTelLLM should map to multiple tuples
        mappings = registry._extract_normalized_mappings("oTelLLM")
        assert ("otelllm", "llm") in mappings
        assert ("genai", "llm") in mappings
        assert ("llm", "llm") in mappings
        assert ("ai", "llm") in mappings
        assert "entity2" in registry._cache


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

