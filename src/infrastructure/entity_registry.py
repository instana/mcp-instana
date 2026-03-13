"""
Entity Capability Registry Module

Manages entity type capabilities (metrics, tags, filters).
Loads from schema files and provides exact constant resolution.
"""
import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.core.utils import BaseInstanaClient
from src.infrastructure.infrastructure_catalog import InfrastructureCatalogMCPTools

logger = logging.getLogger(__name__)

@dataclass
class EntityCapability:
    """
    Represents capabilities of an entity type.
    Contains all metrics and tag filters available for that entity.
    """
    entity_type: str  # e.g. "kubernetesPod"
    api_endpoint: str  # e.g. "/api/infrastructure-monitoring/analyze/entities"
    metrics: List[str]  # e.g., ["cpuRequests", "cpuLimits", ...]
    tag_filters: List[str]  # e.g., ["kubernetes.namespace.name", ...]
    aggregations: List[str]  # e.g., ["mean", "sum", "max", "min"]

class EntityCapabilityRegistry(BaseInstanaClient):
    """
    Central registry for entity type capabilities.

    Responsibilities:
    1. Load schema files from disk
    2. Cache entity capabilities
    3. Resolve entity types from normalized intent
    4. Find exact metric names from categories
    5. Find exact tag filter names from simple names
    6. Load entity type mappings from Instana API
    """

    # Fallback mapping from normalized (class, kind) to entity type
    # Used only if API call fails
    _FALLBACK_ENTITY_TYPE_MAPPING = {
        ("kubernetes", "pod"): "kubernetesPod",
        ("kubernetes", "deployment"): "kubernetesDeployment",
        ("jvm", "runtime"): "jvmRuntimePlatform",
        ("docker", "container"): "docker",
        ("db2", "database"): "db2Database",
        ("ibmmq", "queue"): "ibmMqQueue",
        ("host", "host"): "host",
        ("infrastructure", "host"): "host",
        ("server", "host"): "host",
        ("otelllm", "llm"): "oTelLLM",
        ("genai", "llm"): "oTelLLM",
        ("llm", "llm"): "oTelLLM",
        ("ai", "llm"): "oTelLLM",
    }

    def __init__(self, schema_dir: Path, base_url: Optional[str] = None, read_token: Optional[str] = None) -> None:
        """
        Initialize the registry.
        Args:
            schema_dir: Path to directory containing schema JSON files
            base_url: Instana API base URL (optional, can be set via env var)
            read_token: Instana API read token (optional, can be set via env var)
        """
        # Initialize BaseInstanaClient with credentials
        super().__init__(read_token=read_token or "", base_url=base_url or "")

        self.schema_dir = Path(schema_dir)
        self._cache: Dict[str, EntityCapability] = {}

        # Dynamic entity type mapping (populated from API)
        self.entity_type_mapping: Dict[tuple, str] = {}

        # Load entity type mapping from API
        self._load_entity_type_mapping()

        # Load schemas
        self._load_schemas()

    def _load_schemas(self) -> None:
        """
        Load all entity schemas from JSON files.

        Looks for files matching pattern: *_schema.json
        """

        if not self.schema_dir.exists():
            logger.warning(f"Schema directory does not exist: {self.schema_dir}")
            return

        schema_files = list(self.schema_dir.glob("*_schema.json"))
        logger.info(f"Found {len(schema_files)} schema files in {self.schema_dir}")

        for schema_file in schema_files:
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    self._parse_schema(schema, schema_file.name)

            except Exception as e:
                logger.error(f"Error loading schema {schema_file}: {e}")

    def _parse_schema(self, schema: Dict, filename: str) -> None:
        """
        Parse a schema JSON and create EntityCapability.

        Args:
            schema: Parsed JSON schema
            filename: Name of the schema file (for logging)
        """

        try:
            entity_type = schema.get("type")
            if not entity_type:
                logger.warning(f"Schema {filename} missing 'type' field")
                return

            # Extract metrics
            metrics = []
            if "parameters" in schema and "metrics" in schema["parameters"]:
                metrics_data = schema["parameters"]["metrics"]
                if "metric" in metrics_data:
                    metrics = metrics_data["metric"]

            # Extract Tag Filters
            tag_filters = []
            if "parameters" in schema and "tagFilterElements" in schema["parameters"]:
                tag_data = schema["parameters"]["tagFilterElements"]
                if "enum" in tag_data:
                    tag_filters = tag_data["enum"]

            # Extract aggregations
            aggregations = []
            if "parameters" in schema and "metrics" in schema["parameters"]:
                metrics_data = schema["parameters"]["metrics"]
                if "aggregation" in metrics_data and "enum" in metrics_data["aggregation"]:
                    aggregations = metrics_data["aggregation"]["enum"]

            # Get API Endpoint
            api_endpoint = schema.get("api_endpoint", "")

            # Create EntityCapability
            capability = EntityCapability(
                entity_type=entity_type,
                metrics=metrics,
                aggregations=aggregations,
                tag_filters=tag_filters,
                api_endpoint=api_endpoint
            )

            self._cache[entity_type] = capability
            logger.info(f"Loaded {entity_type}: {len(metrics)} metrics, {len(tag_filters)} tag filters, {len(aggregations)} aggregations")
        except Exception as e:
            logger.error(f"Error loading schema {filename}: {e!s}")

    def _load_entity_type_mapping(self) -> None:
        """
        Load entity type mapping from Instana API.

        Fetches the plugin catalog using InfrastructureCatalogMCPTools.get_infrastructure_catalog_plugins
        and builds a mapping from normalized (class, kind) tuples to entity types.
        Falls back to hardcoded mapping if API call fails.
        """
        if not self.base_url or not self.read_token:
            logger.warning("Instana API credentials not provided, using fallback entity type mapping")
            self.entity_type_mapping = self._FALLBACK_ENTITY_TYPE_MAPPING.copy()
            return

        try:
            # Create InfrastructureCatalogMCPTools instance
            catalog_tools = InfrastructureCatalogMCPTools(
                read_token=self.read_token,
                base_url=self.base_url
            )

            # Create event loop if needed for async call
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Call get_infrastructure_catalog_plugins
            result = loop.run_until_complete(
                catalog_tools.get_infrastructure_catalog_plugins()
            )

            # Check for error response
            if isinstance(result, dict) and "error" in result:
                logger.warning(f"API request failed: {result['error']}")
                self.entity_type_mapping = self._FALLBACK_ENTITY_TYPE_MAPPING.copy()
                return

            # Extract plugin list from the structured response
            # The method returns: {"plugins": [...], "total_available": N, ...}
            plugins = result.get("plugins", [])

            if not plugins:
                logger.warning("No plugins returned from API")
                self.entity_type_mapping = self._FALLBACK_ENTITY_TYPE_MAPPING.copy()
                return

            logger.info(f"Fetched {len(plugins)} plugins from API")

            # Build the mapping from plugin data
            mapping = {}

            for plugin_id in plugins:
                if not plugin_id:
                    continue

                # Extract normalized class and kind from plugin ID
                # Common patterns: kubernetesPod, kubernetesDeployment, jvmRuntimePlatform, etc.
                normalized_mappings = self._extract_normalized_mappings(plugin_id)

                for class_kind_tuple in normalized_mappings:
                    mapping[class_kind_tuple] = plugin_id

            # Add fallback mappings for any missing entries
            for key, value in self._FALLBACK_ENTITY_TYPE_MAPPING.items():
                if key not in mapping:
                    mapping[key] = value

            self.entity_type_mapping = mapping
            logger.info(f"Built entity type mapping with {len(mapping)} entries")

        except Exception as e:
            logger.warning(f"Failed to fetch entity type mapping from API: {e}")
            logger.info("Using fallback entity type mapping")
            self.entity_type_mapping = self._FALLBACK_ENTITY_TYPE_MAPPING.copy()

    def _extract_normalized_mappings(self, plugin_id: str) -> List[tuple]:
        """
        Extract normalized (class, kind) tuples from a plugin ID.

        Args:
            plugin_id: Plugin ID (e.g., "kubernetesPod", "jvmRuntimePlatform")

        Returns:
            List of (class, kind) tuples that map to this plugin

        Examples:
            "kubernetesPod" -> [("kubernetes", "pod")]
            "kubernetesDeployment" -> [("kubernetes", "deployment")]
            "jvmRuntimePlatform" -> [("jvm", "runtime")]
            "host" -> [("host", "host"), ("infrastructure", "host"), ("server", "host")]
        """
        mappings = []
        plugin_lower = plugin_id.lower()

        # Handle special cases first
        if plugin_id == "host":
            mappings.extend([
                ("host", "host"),
                ("infrastructure", "host"),
                ("server", "host")
            ])
        elif plugin_id == "oTelLLM":
            mappings.extend([
                ("otelllm", "llm"),
                ("genai", "llm"),
                ("llm", "llm"),
                ("ai", "llm")
            ])
        elif plugin_id == "docker":
            mappings.append(("docker", "container"))
        elif plugin_lower.startswith("kubernetes"):
            # Extract kind from plugin ID (e.g., kubernetesPod -> pod)
            kind = plugin_id[10:]  # Remove "kubernetes" prefix
            if kind:
                kind_lower = kind[0].lower() + kind[1:] if len(kind) > 1 else kind.lower()
                mappings.append(("kubernetes", kind_lower))
        elif plugin_lower.startswith("jvm"):
            # jvmRuntimePlatform -> ("jvm", "runtime")
            mappings.append(("jvm", "runtime"))
        elif plugin_lower.startswith("db2"):
            # db2Database -> ("db2", "database")
            mappings.append(("db2", "database"))
        elif plugin_lower.startswith("ibmmq"):
            # ibmMqQueue -> ("ibmmq", "queue")
            kind = plugin_id[5:]  # Remove "ibmMq" prefix
            if kind:
                kind_lower = kind[0].lower() + kind[1:] if len(kind) > 1 else kind.lower()
                mappings.append(("ibmmq", kind_lower))
        else:
            # Generic fallback: use plugin_id as both class and kind
            mappings.append((plugin_lower, plugin_lower))

        return mappings

    def resolve(self, entity_class: str, entity_kind: str) -> Optional[EntityCapability]:
        """
        Resolve normalized intent to entity capability.

        Args:
            entity_class: Entity class from normalizer (e.g., "kubernetes")
            entity_kind: Entity kind from normalizer (e.g., "pod")

        Returns:
            EntityCapability if found, None otherwise

        Examples:
            resolve("kubernetes", "pod") → kubernetesPod capability
            resolve("jvm", "runtime") → jvmRuntimePlatform capability
        """
        # Look up entity type from dynamic mapping
        entity_type = self.entity_type_mapping.get((entity_class, entity_kind))
        if not entity_type:
            logger.warning(f"No entity type mapping found for {entity_class}/{entity_kind}")
            return None

        # Get capability from cache
        capability = self._cache.get(entity_type)
        if not capability:
            logger.warning(f"No capability found for entity type {entity_type}")
            return None
        return capability

    def find_metric(self,
                    entity_type: str,
                    metric_category: str,
                    aggregation: Optional[str] = None) -> Optional[str]:
        """
        Find exact metric name from category.

        This is the KEY method that resolves categories to exact metrics!

        Args:
            entity_type: Entity type (e.g., "kubernetesPod")
            metric_category: Metric category from normalizer (e.g., "cpu")
            aggregation: Optional aggregation hint (e.g., "usage")

        Returns:
            Exact metric name if found, None otherwise

        Examples:
            find_metric("kubernetesPod", "cpu", "usage") → "cpuRequests"
            find_metric("jvmRuntimePlatform", "memory", "usage") → "memory.used"
            find_metric("kubernetesPod", "threads", "blocked") → None (not applicable)
        """
        capability = self._cache.get(entity_type)
        if not capability:
            logger.warning(f"No capability found for entity type {entity_type}")
            return None

        # Search for metrics containg the category
        matches = []
        category_lower = metric_category.lower()
        for metric in capability.metrics:
            metric_lower = metric.lower()
            # Check if category is contained in metric name
            if category_lower in metric_lower:
                matches.append(metric)
        if not matches:
            logger.debug(f"No metrics found for category {metric_category} in entity type {entity_type}")
            return None

        #If only one match, return it
        if len(matches) == 1:
            logger.debug(f"Found exact match: {matches[0]}")
            return matches[0]

        #Multiple matches - try to narrow down with the aggregation
        if aggregation:
            agg_lower = aggregation.lower()
            for match in matches:
                if agg_lower in match.lower():
                    logger.debug(f"Found match with aggregation: {match}")
                    return match

        # Return first match (caller can handle multiple matches via elicitation)
        logger.debug(f"Multiple matches found, returning first: {matches[0]}")
        return matches[0]

    def find_all_matching_metrics(self, entity_type: str, metric_category: str) -> List[str]:
        """
        Find ALL metrics matching a category.

        Used by elicitation handler when multiple matches exist.

        Args:
            entity_type: Entity type
            metric_category: Metric category

        Returns:
            List of all matching metric names
        """
        capability = self._cache.get(entity_type)
        if not capability:
            return []
        matches = []
        category_lower = metric_category.lower()
        for metric in capability.metrics:
            if category_lower in metric.lower():
                matches.append(metric)
        return matches

    def find_tag_filter(self, entity_type: str, filter_name: str) -> Optional[str]:
        """
        Find exact tag filter name from simple name.

        Args:
            entity_type: Entity type (e.g., "kubernetesPod")
            filter_name: Simple filter name (e.g., "namespace")

        Returns:
            Exact tag filter name if found, None otherwise

        Examples:
            find_tag_filter("kubernetesPod", "namespace") → "kubernetes.namespace.name"
            find_tag_filter("kubernetesPod", "cluster") → "kubernetes.cluster.name"
            find_tag_filter("jvmRuntimePlatform", "host") → "host.name"
        """
        capability = self._cache.get(entity_type)
        if not capability:
            return None

        #Search for tag filters containing the filter name
        filter_lower = filter_name.lower()
        for tag in capability.tag_filters:
            tag_lower = tag.lower()
            #Check if filter name is in tag
            if filter_lower in tag_lower:
                logger.debug(f"Found tag filter {tag} for entity type {entity_type} and filter name {filter_name}")
                return tag

        logger.debug(f"No tag filter found for entity type {entity_type} and filter name {filter_name}")
        return None

    def get_all_metrics(self, entity_type: str) -> List[str]:
        """
        Get all available metrics for an entity type.

        Used for displaying options to user.
        """
        capability = self._cache.get(entity_type)
        return capability.metrics if capability else []

    def get_all_tag_filters(self, entity_type: str) -> List[str]:
        """
        Get all available tag filters for an entity type.

        Used for displaying options to user.
        """
        capability = self._cache.get(entity_type)
        return capability.tag_filters if capability else []

    def get_entity_types(self) -> List[str]:
        """Get list of all loaded entity types."""
        return list(self._cache.keys())

    def get_full_schema(self, entity_type: str) -> Optional[dict]:
        """
        Get complete raw schema for an entity type.

        Used for machine-facing elicitation - returns the full schema
        that will be passed to LLM for selection.

        Args:
            entity_type: Entity type (e.g., "jvmRuntimePlatform")

        Returns:
            Complete schema dict if found, None otherwise
        """

        if entity_type not in self._cache:
            logger.warning(f"Entity type {entity_type} not found in registry")
            return None
        schema_file = self.schema_dir/f"{entity_type}_schema.json"

        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return None

        try:
            with open(schema_file, 'r') as f:
                schema = json.load(f)
                return schema
        except Exception as e:
            logger.error(f"Error loading schema file {schema_file}: {e}")
            return None
