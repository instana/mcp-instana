"""
Infrastructure Catalog MCP Tools Module

This module provides infrastructure catalog-specific MCP tools for Instana monitoring.
"""

import json
import logging
from typing import Any, Dict, List, Optional

# Import the necessary classes from the SDK
try:
    from instana_client.api.infrastructure_catalog_api import (
        InfrastructureCatalogApi,
    )
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    extract_tag_names_from_tree,
    register_as_tool,
    with_header_auth,
)

# Configure logger for this module
logger = logging.getLogger(__name__)

# Error message constants
ERROR_PLUGIN_REQUIRED = "plugin parameter is required"
_HINT_GET_PLUGINS = "First call get_plugins to discover available plugin IDs"
_MSG_PLUGIN_MISSING = "Missing required parameter 'plugin'. Call get_plugins first to discover valid plugin IDs."

# Static metric overrides for plugins whose tagged metrics are not exposed by the catalog API.
# The catalog endpoint GET /catalog/metrics/{plugin} only returns untagged/builtin definitions;
# tagged metrics (registered via the custom catalog path) are absent from its response.
# Add an entry here whenever a plugin's full metric set cannot be discovered via the API.
_STATIC_METRICS_OVERRIDE: Dict[str, List[str]] = {
    "oTelLLM": [
        "metrics.gauges.llm.usage.total_tokens",
        "metrics.gauges.llm.usage.input_tokens",
        "metrics.gauges.llm.usage.output_tokens",
        "metrics.gauges.llm.usage.cost",
        "metrics.gauges.llm.usage.input_cost",
        "metrics.gauges.llm.usage.output_cost",
        "metrics.gauges.llm.response.duration",
        "metrics.gauges.llm.latency.per_token",
        "metrics.sums.llm.request.count",
        "__message_size",
        "__message_count"
    ],
}

class InfrastructureCatalogMCPTools(BaseInstanaClient):
    """Tools for infrastructure catalog in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Infrastructure Catalog MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    # @register_as_tool(...)  # Disabled for future reference
    @with_header_auth(InfrastructureCatalogApi)
    async def get_available_payload_keys_by_plugin_id(self,
                                                      plugin_id: str,
                                                      ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get available payload keys for a specific plugin in Instana. This tool retrieves the list of payload keys that can be used to access detailed monitoring data
        for a particular plugin type. Use this when you need to understand what data is available for a specific entity type, want to explore the monitoring capabilities
        for a plugin, or need to find the correct payload key for accessing specific metrics or configuration data. This is particularly useful for preparing detailed
        queries, understanding available monitoring data structures, or when building custom dashboards or integrations. For example, use this tool when asked about
        'what data is available for Java processes', 'payload keys for Kubernetes', 'what metrics can I access for MySQL', or when someone wants to
        'find out what monitoring data is collected for a specific technology'.

        Args:
            plugin_id: The ID of the plugin to get payload keys for
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing payload keys or error information
        """
        try:
            logger.debug(f"get_available_payload_keys_by_plugin_id called with plugin_id={plugin_id}")

            if not plugin_id:
                return {"error": "plugin_id parameter is required"}

            # Try using the standard SDK method
            try:
                # Call the get_available_payload_keys_by_plugin_id method from the SDK
                result = api_client.get_available_payload_keys_by_plugin_id(
                    plugin_id=plugin_id
                )

                # Convert the result to a dictionary
                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict()
                elif isinstance(result, dict):
                    result_dict = result
                elif isinstance(result, list):
                    # Wrap list in a dictionary to match return type
                    items = [item.to_dict() if hasattr(item, 'to_dict') else item for item in result]
                    result_dict = {"payload_keys": items, "plugin_id": plugin_id}
                elif isinstance(result, str):
                    # Handle string response (special case for some plugins like db2Database)
                    logger.debug(f"Received string response for plugin_id={plugin_id}: {result}")
                    result_dict = {"message": result, "plugin_id": plugin_id}
                else:
                    # For any other type, convert to string representation
                    result_dict = {"data": str(result), "plugin_id": plugin_id}

                logger.debug(f"Result from get_available_payload_keys_by_plugin_id: {result_dict}")

                # Safety check: ensure we never return a raw list
                if isinstance(result_dict, list):
                    result_dict = {"payload_keys": result_dict, "plugin_id": plugin_id}

                return result_dict

            except Exception as sdk_error:
                logger.error(f"SDK method failed: {sdk_error}, trying fallback")

                # Use the without_preload_content version to get the raw response
                try:
                    response_data = api_client.get_available_payload_keys_by_plugin_id_without_preload_content(
                        plugin_id=plugin_id
                    )

                    # Check if the response was successful
                    if response_data.status != 200:
                        error_message = f"Failed to get payload keys: HTTP {response_data.status}"
                        logger.debug(error_message)
                        return {"error": error_message}

                    # Read the response content
                    response_text = response_data.data.decode('utf-8')

                    # Try to parse as JSON first
                    try:
                        parsed_result = json.loads(response_text)

                        # Ensure we always return a dictionary, not a raw list
                        if isinstance(parsed_result, list):
                            result_dict = {"payload_keys": parsed_result, "plugin_id": plugin_id}
                        elif isinstance(parsed_result, dict):
                            result_dict = parsed_result
                        else:
                            result_dict = {"data": parsed_result, "plugin_id": plugin_id}

                        logger.debug(f"Result from fallback method (JSON): {result_dict}")
                        return result_dict
                    except json.JSONDecodeError:
                        # If not valid JSON, return as string
                        logger.debug(f"Result from fallback method (string): {response_text}")
                        return {"message": response_text, "plugin_id": plugin_id}

                except Exception as fallback_error:
                    logger.warning(f"Fallback method failed: {fallback_error}")
                    raise

        except Exception as e:
            logger.error(f"Error in get_available_payload_keys_by_plugin_id: {e}", exc_info=True)
            return {"error": f"Failed to get payload keys: {e!s}", "plugin_id": plugin_id}


    def _extract_metric_name_from_item(self, item):
        """Extract metric name from a single item (string, dict, or other)."""
        if isinstance(item, str):
            return item
        elif isinstance(item, dict):
            return item.get('metricId') or item.get('label') or str(item)
        else:
            return str(item)

    def _process_metrics_list(self, metrics_list, plugin, limit=50):
        """Process a list of metrics and return formatted result."""
        metric_names = [
            self._extract_metric_name_from_item(item)
            for item in metrics_list[:limit]
        ]
        logger.debug(f"Received {len(metrics_list)} metrics for plugin {plugin}, returning first {len(metric_names)}")
        return {"metrics": metric_names, "plugin": plugin, "total": len(metric_names)}

    def _handle_list_result(self, result, plugin):
        """Handle result when it's a list."""
        return self._process_metrics_list(result, plugin)

    def _handle_dict_result(self, result_dict, plugin):
        """Handle result when it's a dict with metrics field."""
        if 'metrics' not in result_dict:
            return {"error": f"Unexpected dict structure for plugin {plugin}"}

        metrics_list = result_dict['metrics']
        if not isinstance(metrics_list, list):
            return {"error": f"Metrics field is not a list for plugin {plugin}"}

        return self._process_metrics_list(metrics_list, plugin)

    def _handle_sdk_object_result(self, result, plugin):
        """Handle result when it's an SDK object with to_dict method."""
        result_dict = result.to_dict()

        if isinstance(result_dict, list):
            return self._process_metrics_list(result_dict, plugin)
        elif isinstance(result_dict, dict):
            return self._handle_dict_result(result_dict, plugin)
        else:
            return {"error": f"Unable to parse metrics for plugin {plugin}"}

    # @register_as_tool(...)  # Disabled for future reference
    @with_header_auth(InfrastructureCatalogApi)
    async def get_infrastructure_catalog_metrics(self,
                                                 plugin: str,
                                                 filter: Optional[str] = None,
                                                 ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get metric catalog for a specific plugin in Instana. This tool retrieves all available metric definitions for a requested plugin type.
        Use this when you need to understand what metrics are available for a specific technology, want to explore the monitoring capabilities for a plugin,
        or need to find the correct metric names for queries or dashboards. This is particularly useful for building custom dashboards, setting up alerts based on specific metrics,
        or understanding the monitoring depth for a particular technology. For example, use this tool when asked about 'what metrics are available for hosts',
        'JVM metrics catalog', 'available metrics for Kubernetes', or when someone wants to 'see all metrics for a database'.

        Returns the first 50 metrics to keep the response manageable.

        Args:
            plugin: The plugin ID to get metrics for
            filter: Filter to restrict returned metric definitions ('custom' or 'builtin')
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing metrics list or error information
        """
        try:
            logger.debug(f"get_infrastructure_catalog_metrics called with plugin={plugin}, filter={filter}")

            if not plugin:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "plugin",
                            "issue": "plugin is required to get infrastructure catalog metrics",
                            "hint": _HINT_GET_PLUGINS
                        }
                    ],
                    "message": _MSG_PLUGIN_MISSING
                }

            # Call the get_infrastructure_catalog_metrics method from the SDK
            response = api_client.get_infrastructure_catalog_metrics_without_preload_content(
                plugin=plugin,
                filter=filter  # Pass the filter parameter to the SDK
            )

            # Check if the response was successful
            if response.status != 200:
                error_message = f"Failed to get infrastructure catalog metrics: HTTP {response.status}"
                logger.error(error_message)
                return {"error": error_message}

            # Read and parse the response content
            response_text = response.data.decode('utf-8')
            result = json.loads(response_text)

            # Handle different response types
            if isinstance(result, list):
                return self._handle_list_result(result, plugin)
            elif hasattr(result, 'to_dict'):
                return self._handle_sdk_object_result(result, plugin)
            else:
                logger.debug(f"Unexpected result type for plugin {plugin}: {type(result)}")
                return {"error": f"Unexpected response format for plugin {plugin}"}

        except Exception as e:
            logger.error(f"Error in get_infrastructure_catalog_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get metric catalog for plugin '{plugin}': {e!s}"}


    # @register_as_tool(...)  # Disabled for future reference
    async def get_infrastructure_catalog_plugins(self, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get plugin catalog from Instana. This tool retrieves ALL available plugin IDs for your monitored system, showing what types of entities Instana is monitoring in your environment.
        Use this when you need to understand what technologies are being monitored, want to explore the monitoring capabilities of your Instana installation,
        or need to find the correct plugin ID for other API calls. This is particularly useful for discovering what entity types are available for querying,
        understanding your monitoring coverage, or preparing for more detailed data retrieval. For example, use this tool when asked about
        'what technologies are monitored', 'available plugins in Instana', 'list of monitored entity types', or when someone wants to 'see what kinds of systems Instana is tracking'.

        Returns ALL plugins (422) without pagination limits.

        NOTE: This returns a static cached list since the plugin catalog is constant across all Instana installations.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary with complete plugin list and metadata
        """
        try:
            logger.debug("get_infrastructure_catalog_plugins called - returning cached response")

            # Static list of all 422 plugins - this is constant across all Instana installations
            plugin_ids = [
                "businessActivity", "azureManagedHSM", "kafkaConnectWorker", "awsDocumentDbInstance",
                "awsRds", "awsMq", "vsphereVM", "phpRuntimePlatform", "sapJavaNetWeaverInstanceSensor",
                "awsElb", "hAProxy", "kafkaConnectCluster", "nova", "zCics", "tuxedoAppApplication",
                "sapJavaNetWeaverSystemSensor", "packet", "processGroup", "awsLambdaFunction",
                "kubernetesReplicaSet", "consulCluster", "ec2TagsCollector", "kubernetesNamespace",
                "googleCloudRunServiceRevision", "googleCloudStorage", "powerVCComputeInstance",
                "cockroachDBNode", "googleCloudPubSub", "awsIotCore", "sapHana", "customEntity",
                "kubernetesPersistentVolumeClaim", "googleCloudRunServiceRevisionInstance", "abapInstance",
                "lxc", "ibmCloudFoundry", "clickHouseCluster", "db2Database", "kubernetesPod", "website",
                "tuxedoIpcQueue", "oTelDcgm", "ibmMqttChannel", "nutanixHost", "ibmMqMftCoordiQmgr",
                "awsS3", "neo4j", "otelHost", "mapRNode", "awsApiGateway", "kubernetesNode",
                "awsMskCluster", "zhmcConsole", "oTelK8sContainer", "f5", "couchbaseCluster",
                "googleCloudSQL", "hazelcastNode", "webSphereDeploymentManager", "vault",
                "fileMonitoringCondition", "zDb2", "kubernetesHorizontalPodAutoscaler", "azureRedisCache",
                "redisEnterpriseCluster", "webSphereCluster", "beeInstanaNode", "drbdConnection",
                "powerVCRegion", "nutanixVm", "aliCloudRocketMqGroup", "kubernetesScheduler", "containerd",
                "otelProcess", "tibcoBWProcess", "kafkaCluster", "awsAutoScaling", "ibmiDiskInfo",
                "postgreSqlCluster", "awsEmr", "openTelemetry", "awsMetricStreams", "ibmApiConnectSpace",
                "ibmCloudIsLoadBalancer", "zIms", "tuxedoDomain", "solrCloudCluster", "mongoDbShardedCluster",
                "solr", "jBossAsApplicationContainer", "xenServerVM", "aliCloudMysql", "drbdDevice",
                "tenantUnitEntity", "ibmCloudCloudant", "azureAppService", "phmcLPAR", "phmcConsole",
                "elasticsearchCluster", "drbdResource", "ibmDataPowerService", "azureSqlElasticPool",
                "zhmcCpc", "componentMetricsEntity", "ibmCloudFunctions", "service", "kubernetesPersistentVolume",
                "elasticsearchNode", "argocdRollout", "syntheticPoP", "remoteHost", "phmcSystem", "awsEs",
                "sparkApplication", "tibcoEMS", "ibmDataPowerEthernetInterface", "windowsHypervisorHost",
                "rabbitMq", "pCFSpace", "ibmOpenstack", "ibmDataPowerQueueManagerV9", "kubernetesDeployment",
                "oTelK8sCluster", "mule", "ibmDataPowerAppliance", "ibmIDb2", "openLDAP",
                "kubernetesCustomResourceDefinition", "linuxKVMHypervisorHost", "azureFunctionApp",
                "oTelMilvusDB", "azureDatabricks", "tanzuFoundationMember", "sybase", "mongoDbReplicaSet",
                "ibmCloudLoadBalancer", "kubernetesStatefulSet", "httpd", "openshiftDeploymentConfig",
                "googleCloudPubSubSubscription", "kubernetesControllerManager", "kafka", "azureEventHubNamespace",
                "mongoDb", "kafkaConnectTask", "oTelK8sPod", "oTelVLLM", "aliCloudRocketMqGroupPerTopic",
                "jiraApplication", "ping", "sapDbTenant", "ibmMqQueue", "pCFOrganization", "azureCosmosDb",
                "azureEventHubCluster", "jenkins", "azureDataFactory", "cassandraCluster", "jvmRuntimePlatform",
                "componentMetricsInstance", "snowflake", "aceIntegrationNode", "ibmDataPowerSqlDatasource",
                "statsd", "ibmMqMftMonitor", "tuxedoAppServiceBrokerProject", "nutanixDatacenter",
                "sapDbInstance", "syntheticTest", "kongApigateway", "regionEntity", "awsSns",
                "ibmOpenstackComputeInstance", "azureKeyVault", "azurePostgreSQL", "zhmc", "sapJavaInstance",
                "drbd", "googleCloudDatastore", "etcd", "tibcoBWAppNode", "sapAbapSystemSensor",
                "ibmMqQueueUsage", "pCFApplication", "awsDynamoDb", "crowdStrikeFalcon", "msSqlAlwaysOnAG",
                "azureServiceBusQueues", "webLogicApplicationContainer", "host", "perfCounters",
                "ibmDataPowerQueueManager", "hostWinService", "podman", "ibmCloudEtcd", "nginx",
                "linuxKVMHypervisorVM", "ibmCloudPostgreSql", "crystalRuntimePlatform", "rubyRuntimePlatform",
                "ibmIMessageQueueInfo", "entityStatistics", "tibcoASProxy", "redisEnterpriseShard",
                "jettyApplicationContainer", "phmc", "drbdPeerDevice", "ibmCloudRabbitMq", "awsTimestream",
                "phmcVIOS", "dropwizardApplicationContainer", "azureApiManagement", "awsKinesis", "traefik",
                "tibcoBWAppInst", "abapSystem", "kubernetesApiServer", "awsSqs", "kafkaConnectConnector",
                "haskellRuntimePlatform", "msiis", "ibmOpenstackHypervisor", "ibmIOs", "websiteHttpd",
                "rocketMqBroker", "azureServiceBusTopics", "ceph", "application", "awsEc", "awsRedshiftNode",
                "msmq", "ibmApiConnect", "crio", "ibmInfosphereCdcSubscription", "aliCloudOssBucket",
                "pingDirectory", "ibmiLicensedProgramInfo", "sapAbapInstanceSensor", "argocdApplication",
                "redisEnterpriseNode", "kubernetesDaemonSet", "clrRuntimePlatform", "liferayApplicationContainer",
                "azureQueue", "oracleDB", "redisEnterpriseDatabase", "sparkStandalone", "ibmCloudContainerRegistry",
                "memcached", "webSphereLibertyApplicationContainer", "kubernetesReplicationController",
                "ibmMqChannel", "hazelcastCluster", "azureApplicationGateway", "tuxedoMachine",
                "glassfishApplicationContainer", "clickHouseDatabase", "endpoint", "awsEcsContainer", "envoy",
                "ibmOpenstackRegion", "windowsHypervisorVM", "azureBlob", "activeMQ", "snowflakeOrganization",
                "kubernetesCluster", "azureServiceBus", "ibmMqMftZone", "entityStatisticsMember", "bizTalk",
                "nomadScheduler", "awsRedshiftCluster", "hBase", "kubernetes", "redisCluster",
                "ibmInfosphereCdc", "processingStatisticsMember", "powerVC", "ibmCloudMongoDb", "aliCloudOss",
                "rabbitMqCluster", "fileMonitoring", "sapDbms", "ibmApiConnectCatalog", "azureMySql",
                "activeDirectory", "opc", "netCoreRuntimePlatform", "mySqlDatabase", "powerVCHypervisor",
                "cockroachDBCluster", "aliCloudRocketMqTopic", "cassandraNode", "genericHardware",
                "ibmMqMftAgent", "ibmCos", "consul", "azureMachineLearning", "hadoopYARNNode", "keycloak",
                "kubernetesGPT", "activeMQArtemis", "awsLambdaVersion", "oTelLLM", "ibmMqTopic", "docker",
                "ibmCloudEventStream", "tanzuFoundation", "db2ZDatabase", "prometheus", "mapRCluster",
                "awsDocumentDbCluster", "varnish", "vsphereHost", "couchbaseNode", "awsMskBroker",
                "ibmCloudVpn4Vpc", "ibmMqMftTransfer", "azureStorage", "ibmMqQueueManager", "ibmVsi",
                "springbootApplicationContainer", "phpFpmRuntimePlatform", "ibmiNetworkInfo", "zCtg",
                "rocketMqTopic", "gce", "mongoDbCluster", "redis", "golangRuntimePlatform", "azure",
                "kubernetesCustomResource", "ec2Tags", "mariaDbDatabase", "mobileApp", "awsAppSync",
                "tibcoASNode", "xenServerHost", "processingStatistics", "azureFunction", "phmcSharedProcessorPool",
                "oTelJvm", "rocketMqCluster", "azureProductsAcrossTU", "kubeCostPlatform", "agentStatistics",
                "sapWebDispatcher", "log", "ibmiAuditJournalsInfo", "awsCloudFront", "microsoftPurview",
                "kubernetesEtcd", "ec2", "ibmCloudSqlQuery", "webSphereMember", "ibmiSystemValueInfo",
                "msSqlDatabase", "ibmCloudHPMongoDb", "aceIntegrationServer", "tibcoASDataGrid", "awsEbs",
                "aceMessageFlow", "businessProcess", "kubernetesService", "sapHanaSystem", "ibmiIndividualPtfInfo",
                "azureLoadBalancer", "garden", "azureSqlServer", "instanaAgent", "tuxedoServer", "ibmMqCluster",
                "oTelK8sNode", "tuxedoAppTuxedoService", "availabilityZone", "ibmMqListener",
                "tomcatApplicationContainer", "azureEventHubClusteredNamespace", "sapHost", "sapJavaSystem",
                "aliCloudRocketMq", "jbossDataGrid", "ibmCloudElasticsearch", "domino", "argocdCluster",
                "azureProducts", "azureSqlDb", "sapHanaPlatform", "zooKeeper", "hadoopYARN",
                "webSphereInfrastructureManager", "ibmCloudSchematics", "kubernetesEndpoints", "ibmiActiveJobsInfo",
                "oTelDatabase", "genericZone", "kubernetesCronJob", "ibmCloudRedis", "awsEcsTask",
                "nodeJsRuntimePlatform", "pythonRuntimePlatform", "tibcoEMSTopic", "postgreSqlDatabase",
                "azureSignalR", "tibcoEMSQueue", "ibmDataPowerDomain", "ibmDataPowerCluster", "tuxedoApp",
                "googleCloudPubSubTopic", "kubernetesJob", "ibmCloudHPPostgreSql", "zOS",
                "awsDocumentDbElasticCluster", "webSphereApplicationContainer", "process", "drbdReactor",
                "awsBeanstalk", "finagleApplicationContainer", "ibmMqSubscription", "steadyMetricExposureEntity",
                "vsphereDatacenter", "ibmCloudClinicalData"
            ]

            logger.debug(f"Returning {len(plugin_ids)} cached plugin IDs")

            # Return structured response with all plugins
            return {
                "message": f"Found {len(plugin_ids)} total plugins",
                "plugins": plugin_ids,
                "total_available": len(plugin_ids),
                "note": "These are ALL plugin IDs for different technologies monitored by Instana (cached response)"
            }

        except Exception as e:
            logger.error(f"Error in get_infrastructure_catalog_plugins: {e}", exc_info=True)
            return {"error": f"Failed to get plugin catalog: {e!s}"}



    # @register_as_tool(...)  # Disabled for future reference
    @with_header_auth(InfrastructureCatalogApi)
    async def get_infrastructure_catalog_plugins_with_custom_metrics(self, ctx=None, api_client=None) -> Dict[str, Any] | List[Dict[str, Any]]:
        """
        Get all plugins with custom metrics catalog from Instana. This tool retrieves information about which entity types (plugins) in your environment have custom metrics configured.
        Use this when you need to identify which technologies have custom monitoring metrics defined, want to explore custom monitoring capabilities,
        or need to find entities with extended metrics beyond the standard set. This is particularly useful for understanding your custom monitoring setup,
        identifying opportunities for additional custom metrics, or troubleshooting issues with custom metric collection. For example, use this tool when asked about 'which systems have custom metrics',
        'custom monitoring configuration', 'plugins with extended metrics', or when someone wants to 'find out where custom metrics are being collected'.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing plugins with custom metrics or error information
        """
        try:
            logger.debug("get_infrastructure_catalog_plugins_with_custom_metrics called")

            # Call the get_infrastructure_catalog_plugins_with_custom_metrics method from the SDK
            response = api_client.get_infrastructure_catalog_plugins_with_custom_metrics_without_preload_content()

            # Check if the response was successful
            if response.status != 200:
                error_message = f"Failed to get plugins with custom metrics: HTTP {response.status}"
                logger.error(error_message)
                return {"error": error_message}

            # Read and parse the response content
            response_text = response.data.decode('utf-8')
            result = json.loads(response_text)

            # Convert the result to a dictionary
            if isinstance(result, list):
                # Wrap list in a dictionary to match return type
                result_dict = {"plugins_with_custom_metrics": result}
            else:
                # Ensure we always return a dictionary
                result_dict = result if isinstance(result, dict) else {"data": result}

            logger.debug(f"Result from get_infrastructure_catalog_plugins_with_custom_metrics: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_infrastructure_catalog_plugins_with_custom_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get plugins with custom metrics: {e!s}"}


    # @register_as_tool(...)  # Disabled for future reference
    @with_header_auth(InfrastructureCatalogApi)
    async def get_tag_catalog(self, plugin: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get available tags for a particular plugin. This tool retrieves the tag catalog filtered by plugin.

        Args:
            plugin: The plugin name (e.g., 'host', 'jvm', 'openTelemetry')
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing available tags for the plugin or error information
        """
        try:
            logger.debug(f"get_tag_catalog called with plugin={plugin}")

            if not plugin:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "plugin",
                            "issue": "plugin is required to get tag catalog",
                            "hint": _HINT_GET_PLUGINS
                        }
                    ],
                    "message": _MSG_PLUGIN_MISSING
                }

            # Try calling the SDK method first
            try:
                # Call the get_tag_catalog method from the SDK
                result = api_client.get_tag_catalog(
                    plugin=plugin
                )

                # Convert the result to a dictionary
                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict()
                else:
                    # If it's already a dict or another format, use it as is
                    result_dict = result

                logger.debug(f"Result from get_tag_catalog: {result_dict}")
                return result_dict

            except Exception as sdk_error:
                logger.error(f"SDK method failed: {sdk_error}, evaluating fallback conditions")

                # Check if it's a 406 error
                is_406_error = False
                if hasattr(sdk_error, 'status') and sdk_error.status == 406 or "406" in str(sdk_error) and "Not Acceptable" in str(sdk_error):
                    is_406_error = True

                # Check for Pydantic ValidationError (SDK model deserialization issues)
                is_pydantic_error = False
                try:
                    from pydantic import (
                        ValidationError as _PydanticValidationError,  # type: ignore
                    )
                    is_pydantic_error = isinstance(sdk_error, _PydanticValidationError)
                except Exception:
                    # Fallback to string inspection if pydantic not importable in runtime
                    err_str = str(sdk_error).lower()
                    is_pydantic_error = ("pydantic" in err_str and "validation" in err_str) or ("validation error" in err_str)

                if is_406_error or is_pydantic_error:
                    # Try using the SDK's method with custom headers
                    # The SDK should have a method that allows setting custom headers
                    custom_headers = {
                        "Accept": "*/*"  # More permissive Accept header
                    }

                    # Use the without_preload_content version to get the raw response
                    response_data = api_client.get_tag_catalog_without_preload_content(
                        plugin=plugin,
                        _headers=custom_headers  # Pass custom headers to the SDK method
                    )

                    # Check if the response was successful
                    if response_data.status != 200:
                        error_message = f"Failed to get tag catalog: HTTP {response_data.status}"
                        logger.error(error_message)
                        return {"error": error_message}

                    # Read the response content
                    response_text = response_data.data.decode('utf-8')

                    # Parse the JSON manually
                    try:
                        result_dict = json.loads(response_text)
                        logger.debug(f"Result from SDK with custom headers: {result_dict}")
                        return result_dict
                    except json.JSONDecodeError as json_err:
                        error_message = f"Failed to parse JSON response: {json_err}"
                        logger.error(error_message)
                        return {"error": error_message}
                else:
                    # Re-raise if it's not a 406 or Pydantic validation error
                    raise

        except Exception as e:
            logger.error(f"Error in get_tag_catalog: {e}", exc_info=True)
            return {"error": f"Failed to get tag catalog: {e!s}"}



    # @register_as_tool(...)  # Disabled for future reference
    @with_header_auth(InfrastructureCatalogApi)
    async def get_plugin_schema(self,
                                plugin: str,
                                filter: Optional[str] = None,
                                ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get complete schema (metrics + tags) for a specific plugin in a single call.
        This combines get_infrastructure_catalog_metrics and get_tag_catalog to reduce API calls.

        IMPORTANT: The plugin parameter must be a valid plugin ID from get_plugins.
        Using an invalid plugin name will result in HTTP 400/404 errors with no diagnostic message.

        RECOMMENDED WORKFLOW:
        1. Call get_plugins to discover available entity types (e.g., 'host', 'containerd', 'jvmRuntimePlatform')
        2. Call get_plugin_schema with a valid plugin ID to get metrics and tags
        3. Use the returned metrics and tags to build analyze queries with proper filters

        This tool retrieves both available metrics and tags for a plugin type, providing
        a complete schema similar to the static schema files but dynamically from the API.

        Args:
            plugin: The plugin ID from get_plugins (e.g., 'host', 'containerd', 'jvmRuntimePlatform').
                   Must be a valid plugin ID - invalid names return HTTP 400 with no error details.
            filter: Filter to restrict returned metric definitions ('custom' or 'builtin')
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing:
            - plugin: The plugin ID
            - metrics: List of available metric names
            - tags: List of available tag names (simplified from hierarchical structure)
            - errors: List of any errors encountered (e.g., "HTTP 400" for invalid plugin)
            - summary: Summary statistics

        Example:
            # Step 1: Get available plugins
            plugins = await get_plugins()
            # Returns: [{"id": "host", ...}, {"id": "containerd", ...}, ...]

            # Step 2: Get schema for a specific plugin
            schema = await get_plugin_schema(plugin="containerd")
            # Returns: {"metrics": ["memory.usage", ...], "tags": ["host.name", ...]}

            # Step 3: Use in analyze query
            result = await get_entities(payload={
                "type": "containerd",
                "metrics": [{"metric": "memory.usage", "aggregation": "MEAN"}],
                "tagFilterExpression": {...}
            })
        """
        try:
            logger.debug(f"get_plugin_schema called with plugin={plugin}, filter={filter}")

            if not plugin:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "plugin",
                            "issue": "plugin is required to get plugin schema",
                            "hint": _HINT_GET_PLUGINS
                        }
                    ],
                    "message": _MSG_PLUGIN_MISSING
                }

            result = {
                "plugin": plugin,
                "metrics": [],
                "tags": [],
                "errors": []
            }

            # Get metrics — use static override for plugins whose tagged metrics are not
            # returned by the catalog API (e.g. oTelLLM uses the tagged-metrics path).
            if plugin in _STATIC_METRICS_OVERRIDE:
                result["metrics"] = _STATIC_METRICS_OVERRIDE[plugin]
                logger.debug(
                    "Using static metric override for plugin '%s' (%d metrics)",
                    plugin, len(result["metrics"])
                )
            else:
                try:
                    metrics = await self.get_infrastructure_catalog_metrics(
                        plugin=plugin,
                        filter=filter,
                        ctx=ctx,
                        api_client=api_client
                    )

                    # Check if metrics call returned an error
                    if isinstance(metrics, dict) and "error" in metrics:
                        result["errors"].append(f"Metrics: {metrics['error']}")
                        result["metrics"] = []
                    elif isinstance(metrics, dict) and "metrics" in metrics:
                        result["metrics"] = metrics["metrics"]
                    else:
                        result["metrics"] = []

                except Exception as e:
                    error_msg = f"Failed to get metrics: {e!s}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)

            # Get tags
            try:
                tags_response = await self.get_tag_catalog(
                    plugin=plugin,
                    ctx=ctx,
                    api_client=api_client
                )

                # Check if tags call returned an error
                if isinstance(tags_response, dict) and "error" in tags_response:
                    result["errors"].append(f"Tags: {tags_response['error']}")
                    result["tags"] = []
                else:
                    # Extract tag names from the hierarchical structure
                    result["tags"] = sorted(extract_tag_names_from_tree(tags_response))

            except Exception as e:
                error_msg = f"Failed to get tags: {e!s}"
                logger.error(error_msg, exc_info=True)
                result["errors"].append(error_msg)

            # Add summary
            result["summary"] = {
                "total_metrics": len(result["metrics"]),
                "total_tags": len(result["tags"]),
                "has_errors": len(result["errors"]) > 0
            }

            logger.debug(f"get_plugin_schema result: {result['summary']}")

            return result

        except Exception as e:
            logger.error(f"Error in get_plugin_schema: {e}", exc_info=True)
            return {
                "error": f"Failed to get plugin schema: {e!s}",
                "plugin": plugin
            }


    # @register_as_tool(...)  # Disabled for future reference
    @with_header_auth(InfrastructureCatalogApi)
    async def get_tag_catalog_all(self, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get all available tags. This tool retrieves the complete list of all tags available in your Instana-monitored environment. It returns every tag across all plugins, services, and technologies, allowing users to explore the full tagging taxonomy.

        Use when the user asks:
        "What tags are available in Instana?"
        "Show me all possible tags I can use for filtering or grouping"
        "What tags exist across all services or technologies?"
        "Give me the complete tag catalog from Instana"

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing a summarized view of available tags or error information
        """
        try:
            logger.debug("get_tag_catalog_all called")

            # Try using the standard SDK method first
            try:
                result = api_client.get_tag_catalog_all()

                # Convert the result to a dictionary
                if hasattr(result, 'to_dict'):
                    full_result = result.to_dict()
                else:
                    # If it's already a dict or another format, use it as is
                    full_result = result

                logger.debug(f"Full result from get_tag_catalog_all (standard method): {full_result}")

                # Create a summarized version of the response
                summarized_result = self._summarize_tag_catalog(full_result)
                return summarized_result

            except Exception as sdk_error:
                logger.error(f"Standard SDK method failed: {sdk_error}, trying fallback")

                # Fallback to using the without_preload_content method
                response_data = api_client.get_tag_catalog_all_without_preload_content()

                # Check if the response was successful
                if response_data.status != 200:
                    error_message = f"Failed to get tag catalog: HTTP {response_data.status}"
                    logger.debug(error_message)

                    if response_data.status in (401, 403):
                        return {"error": "Authentication failed. Please check your API token and permissions."}
                    else:
                        return {"error": error_message}

                # Read the response content
                response_text = response_data.data.decode('utf-8')

                # Parse the JSON manually
                try:
                    full_result = json.loads(response_text)
                    logger.debug(f"Full result from get_tag_catalog_all (fallback method): {full_result}")

                    # Create a summarized version of the response
                    summarized_result = self._summarize_tag_catalog(full_result)
                    return summarized_result

                except json.JSONDecodeError as json_err:
                    error_message = f"Failed to parse JSON response: {json_err}"
                    logger.error(f"Response text: {response_text}")
                    return {"error": error_message}

        except Exception as e:
            logger.error(f"Error in get_tag_catalog_all: {e}", exc_info=True)
            return {"error": f"Failed to get tag catalog: {e!s}"}

    def _summarize_tag_catalog(self, full_catalog: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summarized version of the tag catalog response that includes tag labels.

        Args:
            full_catalog: The complete tag catalog response

        Returns:
            A simplified version of the tag catalog with tag labels
        """
        summary = {
            "summary": "List of all available tag labels in Instana",
            "categories": {},
            "allLabels": []
        }

        # Extract tag tree if available
        tag_tree = full_catalog.get("tagTree", [])

        # Process each category in the tag tree
        for category in tag_tree:
            category_label = category.get("label", "Uncategorized")
            category_tags = []

            # Process children (actual tags)
            if "children" in category and isinstance(category["children"], list):
                for tag in category["children"]:
                    tag_label = tag.get("label")
                    if tag_label:
                        category_tags.append(tag_label)
                        summary["allLabels"].append(tag_label)

            # Add category to summary if it has tags
            if category_tags:
                summary["categories"][category_label] = sorted(category_tags)

        # Remove duplicates and sort the all labels list
        summary["allLabels"] = sorted(set(summary["allLabels"]))
        summary["count"] = len(summary["allLabels"])

        return summary


    # @register_as_tool(...)  # Disabled for future reference
    @with_header_auth(InfrastructureCatalogApi)
    async def get_infrastructure_catalog_search_fields(self, ctx=None, api_client=None) -> List[str] | Dict[str, Any]:
        """
        Get search field catalog from Instana. This tool retrieves all available search keywords and fields that can be used in dynamic focus queries for infrastructure monitoring.
        Use this when you need to understand what search criteria are available, want to build complex queries to filter entities, or need to find the correct search syntax for specific entity properties.
        This is particularly useful for constructing advanced search queries, understanding available filtering options, or discovering how to target specific entities in your environment.
        For example, use this tool when asked about 'what search fields are available', 'how to filter hosts by property', 'search syntax for Kubernetes pods', or when someone wants to 'learn how to build complex entity queries'.

        This endpoint retrieves all available search keywords for dynamic focus queries.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing search field keywords or error information
        """
        try:
            logger.debug("get_infrastructure_catalog_search_fields called")

            # Call the get_infrastructure_catalog_search_fields method from the SDK
            response = api_client.get_infrastructure_catalog_search_fields_without_preload_content()

            # Check if the response was successful
            if response.status != 200:
                error_message = f"Failed to get search fields: HTTP {response.status}"
                logger.error(error_message)
                return {"error": error_message}

            # Read and parse the response content
            response_text = response.data.decode('utf-8')
            result = json.loads(response_text)

            logger.debug(f"API call successful, got {len(result)} search fields")

            # Extract just 10 keywords to keep it very small
            keywords = []

            for field_obj in result[:10]:
                try:
                    if isinstance(field_obj, dict):
                        keyword = field_obj.get("keyword", "")
                    else:
                        keyword = getattr(field_obj, 'keyword', "")

                    if keyword:
                        keywords.append(keyword)

                except Exception:
                    continue

            # Wrap the keywords list in a dictionary to match return type
            return {"search_fields": keywords, "count": len(keywords)}

        except Exception as e:
            logger.error(f"Error: {e}")
            return {"error": str(e)}
