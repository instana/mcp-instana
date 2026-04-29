"""
Infrastructure Analyze MCP Prompts Module

This module provides infrastructure analyze-specific MCP prompts for Instana monitoring.
"""

from typing import Callable, Dict, List, Optional, Tuple

from src.prompts import auto_register_prompt


class InfrastructureAnalyzePrompts:
    """Class containing prompts for infrastructure analysis in Instana."""

    @auto_register_prompt
    @staticmethod
    def infra_available_metrics(
        type: str,
        query: Optional[str] = None,
        var_from: Optional[int] = None,
        to: Optional[int] = None,
        windowSize: Optional[int] = None) -> str:
        """Get available infrastructure metrics for a given entity type"""
        return f"""
        Get available infrastructure metrics:
        - Type: {type}
        - Query: {query if query is not None else 'None'}
        - From: {var_from if var_from is not None else 'None'}
        - To: {to if to is not None else 'None'}
        - Window size: {windowSize if windowSize is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def infra_get_entities(
        type: str,
        metrics: Optional[str] = None,
        windowSize: Optional[int] = None,
        to: Optional[int] = None) -> str:
        """Fetch infrastructure entities and their metrics"""
        return f"""
        Get infrastructure entities:
        - Type: {type}
        - Metrics: {metrics if metrics is not None else 'None'}
        - Window size: {windowSize if windowSize is not None else 'None'}
        - To: {to if to is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def infra_available_plugins(
        offline: bool,
        query: Optional[str] = None,
        windowSize: Optional[int] = None,
        to: Optional[int] = None) -> str:
        """List available infrastructure monitoring plugins"""
        return f"""
        Get available infrastructure plugins:
        - Query: {query if query is not None else 'None'}
        - Offline: {offline}
        - Window size: {windowSize if windowSize is not None else 'None'}
        - To: {to if to is not None else 'None'}
        """

    # IBM MQ Debugging Workflow Prompts with Cross-Tool Integration

    @auto_register_prompt
    @staticmethod
    def debug_ibmmq_queue_full(
        queue_name: str,
        queue_manager: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Debug IBM MQ queue full issue (MQRC 2053) - Applications cannot put messages"""
        return f"""
        Debug IBM MQ queue full issue:
        - Queue name: {queue_name}
        - Queue manager: {queue_manager or '(will query all)'}
        - Time range: {time_range or '1h'}
        - Error code: MQRC 2053 (MQRC_Q_FULL)

        Infrastructure Analysis Steps:
        1. Check queue depth and capacity using entity "ibm mq queue"
           - Metrics: ibmmq.queue.depth, ibmmq.queue.max_depth
           - Filter by queue name: {queue_name}
        
        2. Analyze message flow patterns (messages in vs out)
           - Metrics: ibmmq.queue.messages_in, ibmmq.queue.messages_out
        
        3. Verify queue utilization percentage using entity "ibm mq queue usage"
           - Metrics: ibmmq.queue.usage.percentage
        
        4. Check if consumers are active
           - Group by host.name to identify consumer hosts

        Cross-Tool Integration:
        5. **Check for related Instana events** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 5a - Specific search (try first):**
           - operation: "get_events"
           - params: {{
               "entity_name": "{queue_name}",
               "problem": "queue",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Searches for events with queue name in entity label
           
           **Step 5b - If no results, broaden search:**
           - operation: "get_events"
           - params: {{
               "problem": "queue",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Removes entity_name filter to find any queue-related events
           
           **Step 5c - If still no results, search all IBM MQ events:**
           - operation: "get_events"
           - params: {{
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Then manually filter results for IBM MQ-related events by checking:
             * entityLabel contains queue manager names (e.g., "QM217205@gollum1")
             * entityLabel contains queue names (e.g., "SYSTEM.RETAINED.PUB.QUEUE")
             * problem field contains MQ-related keywords
           
           **Example successful query from real scenario:**
           - Found event for SYSTEM.RETAINED.PUB.QUEUE on QM217205@gollum1
           - Event had: entityType="INFRASTRUCTURE", problem="The oldest message on the queue..."
           - Key insight: Queue full issues often manifest as "oldest message" or "not consumed" events
           
           - Benefit: Correlates infrastructure metrics with event timeline
           - Note: Always start specific and progressively broaden if no results found

        6. **Check recent releases** (manage_releases):
           - operation: "get_all_releases"
           - params: {{"time_range": "{time_range or '1h'}"}}
           - Look for deployments that may have increased message volume
           - Benefit: Links queue issues to code deployments

        7. **Analyze application traces** (manage_applications):
           - resource_type: "analyze", operation: "get_all_traces"
           - Filter by services that produce to {queue_name}
           - Check for increased error rates or latency
           - Benefit: Identifies if application behavior changed

        Resolution: Increase MAXDEPTH, add consumers, or implement rate limiting
        """

    @auto_register_prompt
    @staticmethod
    def debug_ibmmq_invalid_queue(
        queue_name: str,
        queue_manager: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Debug IBM MQ invalid queue (MQRC 2085) - Queue does not exist"""
        return f"""
        Debug IBM MQ invalid queue issue:
        - Queue name: {queue_name}
        - Queue manager: {queue_manager or '(will query all)'}
        - Time range: {time_range or '1h'}
        - Error code: MQRC 2085 (MQRC_UNKNOWN_OBJECT_NAME)

        Infrastructure Analysis Steps:
        1. Verify queue exists using entity "ibm mq queue"
           - List all queues under queue manager
           - Search for queue name: {queue_name}
           - Expected: Queue NOT found in list
        
        2. Check connection errors at queue manager level
           - Entity: "ibm mq queue manager"
           - Metrics: ibmmq.queue_manager.connection_errors
           - Look for MQOPEN failures
        
        3. Analyze failed MQOPEN attempts
           - Metrics: ibmmq.queue_manager.mqi_failures
           - Filter by error code 2085
           - Group by application/host to identify source
        
        4. List valid queues for comparison
           - Entity: "ibm mq queue"
           - Get all queue names under {queue_manager or 'all queue managers'}
           - Benefit: Helps identify typos or naming issues

        Cross-Tool Integration:
        5. **Check for related Instana events** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 5a - Specific search (try first):**
           - operation: "get_events"
           - params: {{
               "problem": "unknown",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Searches for "unknown object" or "not found" type events
           
           **Step 5b - If no results, search for MQI failures:**
           - operation: "get_events"
           - params: {{
               "problem": "failure",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Looks for general MQI failure events that may include MQRC 2085
           
           **Step 5c - If still no results, search all events and filter:**
           - operation: "get_events"
           - params: {{
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Then manually check for events with:
             * entityLabel containing queue manager names
             * problem field mentioning "object", "queue", or "not found"
           
           - Benefit: See if Instana detected the invalid queue access
           - Note: MQRC 2085 errors may not always generate events, check application traces

        6. **Analyze application traces** (manage_applications):
           - resource_type: "analyze", operation: "get_all_traces"
           - Filter by error status and MQ operations
           - Look for error traces with MQRC 2085
           - Check error message for queue name: {queue_name}
           - Benefit: Identifies which application is using wrong queue name

        7. **Check recent releases** (manage_releases):
           - operation: "get_all_releases"
           - Look for deployments that may have changed queue configuration
           - Benefit: Determines if queue was renamed or removed

        8. **Verify queue configuration**:
           - Check if queue was recently deleted
           - Check if queue name has typo (case-sensitive)
           - Check if queue is on different queue manager
           - Benefit: Identifies configuration drift

        Resolution: Create missing queue, fix queue name in application, or update configuration
        """

    @auto_register_prompt
    @staticmethod
    def debug_ibmmq_qmgr_down(
        queue_manager: str,
        time_range: Optional[str] = None
    ) -> str:
        """Debug IBM MQ queue manager unavailable (MQRC 2059) - Cannot connect"""
        return f"""
        Debug IBM MQ queue manager down:
        - Queue manager: {queue_manager}
        - Time range: {time_range or '1h'}
        - Error code: MQRC 2059 (MQRC_Q_MGR_NOT_AVAILABLE)

        Infrastructure Analysis Steps:
        1. Check queue manager status using entity "ibm mq queue manager"
           - Metrics: ibmmq.queue_manager.status, ibmmq.queue_manager.connection_count
           - Filter by queue manager name: {queue_manager}
        
        2. Verify active channels
           - Metrics: ibmmq.queue_manager.channel_count
        
        3. Check message flow disruption
           - Metrics: ibmmq.queue_manager.mqi_failures
        
        4. Identify all affected queues under this queue manager
           - Use entity "ibm mq queue" with filter

        5. Check host-level resources using entity "host"
           - Metrics: cpu.used_percent, memory.used_percent
           - Filter by host running {queue_manager}
           - Benefit: Identifies if resource exhaustion caused failure

        Cross-Tool Integration:
        6. **Check for related Instana events** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 6a - Specific search (try first):**
           - operation: "get_events"
           - params: {{
               "entity_name": "{queue_manager}",
               "severity": 10,
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Searches for critical events with queue manager name
           
           **Step 6b - If no results, search for availability issues:**
           - operation: "get_events"
           - params: {{
               "problem": "unavailable",
               "severity": 10,
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Broadens to any critical unavailability events
           
           **Step 6c - If still no results, check all critical events:**
           - operation: "get_events"
           - params: {{
               "severity": 10,
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Then filter for events with:
             * entityLabel containing "{queue_manager}"
             * problem mentioning "down", "offline", "unavailable", or "connection"
           
           - Benefit: See if Instana detected the outage
           - Note: Queue manager down events are usually critical (severity 10)

        7. **Check recent releases** (manage_releases):
           - operation: "get_all_releases"
           - Look for deployments affecting {queue_manager}
           - Benefit: Determine if deployment caused the issue

        8. **Check application incidents** (manage_events):
           - operation: "get_events"
           - params: {{
               "entity_type": "application",
               "problem": "connection",
               "time_range": "{time_range or '1h'}"
             }}
           - Benefit: Identify downstream application impact

        Resolution: Start queue manager, check system resources, verify network
        """

    @auto_register_prompt
    @staticmethod
    def debug_ibmmq_large_messages(
        queue_name: str,
        queue_manager: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Debug IBM MQ message too large (MQRC 2030) - Message exceeds MAXMSGL"""
        return f"""
        Debug IBM MQ large message issue:
        - Queue name: {queue_name}
        - Queue manager: {queue_manager or '(will query all)'}
        - Time range: {time_range or '1h'}
        - Error code: MQRC 2030 (MQRC_MSG_TOO_BIG_FOR_Q_MGR)

        Infrastructure Analysis Steps:
        1. Check MQI failures at queue manager level
           - Entity: "ibm mq queue manager"
           - Metrics: ibmmq.queue_manager.mqi_failures
           - Filter by queue manager: {queue_manager or 'all'}
        
        2. Verify queue depth remains flat (messages rejected)
           - Entity: "ibm mq queue"
           - Metrics: ibmmq.queue.depth
           - Filter by queue name: {queue_name}
        
        3. Confirm message flow shows zero messages in
           - Metrics: ibmmq.queue.messages_in
        
        4. Compare attempted message size with MAXMSGL (default 4MB)
           - Check queue manager configuration

        Cross-Tool Integration:
        5. **Check for related Instana events** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 5a - Specific search (try first):**
           - operation: "get_events"
           - params: {{
               "problem": "message",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Searches for message-related events
           
           **Step 5b - If no results, search for MQI failures:**
           - operation: "get_events"
           - params: {{
               "problem": "failure",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Looks for general MQI failure events
           
           **Step 5c - If still no results, check application traces instead:**
           - MQRC 2030 errors rarely generate infrastructure events
           - Focus on application traces (Step 6) to find the issue
           
           - Note: Message size errors typically appear in application traces, not infrastructure events

        6. **Analyze application traces** (manage_applications):
           - resource_type: "analyze", operation: "get_all_traces"
           - Filter by services producing to {queue_name}
           - Look for error traces with MQRC 2030
           - Benefit: Identifies which application is sending large messages

        7. **Check recent releases** (manage_releases):
           - operation: "get_all_releases"
           - Look for deployments that may have changed message format
           - Benefit: Correlates issue with code changes

        Resolution: Increase MAXMSGL, reduce message size, or implement segmentation
        """

    @auto_register_prompt
    @staticmethod
    def debug_ibmmq_auth_failure(
        queue_name: str,
        queue_manager: Optional[str] = None,
        user: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Debug IBM MQ authorization failure (MQRC 2035) - Access denied"""
        return f"""
        Debug IBM MQ authorization failure:
        - Queue name: {queue_name}
        - Queue manager: {queue_manager or '(will query all)'}
        - User: {user or '(will identify from metrics)'}
        - Time range: {time_range or '1h'}
        - Error code: MQRC 2035 (MQRC_NOT_AUTHORIZED)

        Infrastructure Analysis Steps:
        1. Check queue usage failures using entity "ibm mq queue usage"
           - Metrics: ibmmq.queue.usage.failures
           - Filter by queue name: {queue_name}
        
        2. Verify MQI failures at queue manager level
           - Entity: "ibm mq queue manager"
           - Metrics: ibmmq.queue_manager.mqi_failures
        
        3. Identify which hosts are failing
           - Group by host.name
           - Benefit: Pinpoints source of unauthorized access attempts
        
        4. Confirm queue exists and user permissions
           - Check queue configuration

        Cross-Tool Integration:
        5. **Check for related Instana events** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 5a - Specific search (try first):**
           - operation: "get_events"
           - params: {{
               "problem": "authorization",
               "severity": 10,
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Searches for authorization/permission events
           
           **Step 5b - If no results, search for access denied:**
           - operation: "get_events"
           - params: {{
               "problem": "denied",
               "severity": 10,
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Broadens to any "denied" or "forbidden" events
           
           **Step 5c - If still no results, check application traces:**
           - MQRC 2035 errors often appear in application traces rather than infrastructure events
           - Focus on Step 6 (application traces) to identify the source
           
           - Note: Authorization failures may not generate infrastructure events

        6. **Analyze application traces** (manage_applications):
           - resource_type: "analyze", operation: "get_all_traces"
           - Filter by services accessing {queue_name}
           - Look for error traces with MQRC 2035
           - Benefit: Identifies which application/service has permission issues

        7. **Check recent releases** (manage_releases):
           - operation: "get_all_releases"
           - Look for deployments that may have changed service accounts
           - Benefit: Correlates permission issues with deployments

        8. **Check host-level details** using entity "host":
           - Filter by hosts showing failures
           - Benefit: Identifies if specific hosts have misconfigured credentials

        Resolution: Grant PUT/GET permissions using SET AUTHREC command
        """

    @auto_register_prompt
    @staticmethod
    def debug_ibmmq_empty_queue(
        queue_name: str,
        queue_manager: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Debug IBM MQ empty queue (MQRC 2033) - No messages available"""
        return f"""
        Debug IBM MQ empty queue issue:
        - Queue name: {queue_name}
        - Queue manager: {queue_manager or '(will query all)'}
        - Time range: {time_range or '1h'}
        - Error code: MQRC 2033 (MQRC_NO_MSG_AVAILABLE)

        Infrastructure Analysis Steps:
        1. Verify queue depth is zero using entity "ibm mq queue"
           - Metrics: ibmmq.queue.depth
           - Filter by queue name: {queue_name}
        
        2. Analyze if consumption rate exceeds production rate
           - Metrics: ibmmq.queue.messages_in, ibmmq.queue.messages_out
           - Compare rates over time
        
        3. Check if producers are connected
           - Group by host.name to identify producer hosts
        
        4. Review message age patterns
           - Metrics: ibmmq.queue.oldest_message_age

        Cross-Tool Integration:
        5. **Check for related Instana events** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 5a - Specific search (try first):**
           - operation: "get_events"
           - params: {{
               "entity_name": "{queue_name}",
               "problem": "empty",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Searches for empty queue events
           
           **Step 5b - If no results, search for low message events:**
           - operation: "get_events"
           - params: {{
               "problem": "low",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Looks for "low message" or "no messages" events
           
           **Step 5c - If still no results:**
           - MQRC 2033 is often expected behavior (consumer waiting for messages)
           - Focus on application traces (Step 6) to verify producer health
           
           - Note: Empty queue is often normal; events are rare unless configured

        6. **Analyze application traces** (manage_applications):
           - resource_type: "analyze", operation: "get_all_traces"
           - Filter by services producing to {queue_name}
           - Check if producers are experiencing errors
           - Benefit: Identifies if producer applications are failing

        7. **Check recent releases** (manage_releases):
           - operation: "get_all_releases"
           - Look for deployments affecting producer services
           - Benefit: Determines if deployment stopped message production

        8. **Check upstream dependencies**:
           - Use manage_applications to check services that feed {queue_name}
           - Look for high error rates or latency
           - Benefit: Identifies root cause in upstream systems

        Resolution: Often expected behavior; verify producers are running if unexpected
        """

    @auto_register_prompt
    @staticmethod
    def debug_ibmmq_channel_issues(
        channel_name: Optional[str] = None,
        queue_manager: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Debug IBM MQ channel connectivity issues - Messages not flowing"""
        return f"""
        Debug IBM MQ channel issues:
        - Channel name: {channel_name or '(will query all channels)'}
        - Queue manager: {queue_manager or '(will query all)'}
        - Time range: {time_range or '1h'}

        Infrastructure Analysis Steps:
        1. Check channel status using entity "ibm mq channel"
           - Metrics: ibmmq.channel.status
           - Filter by channel name: {channel_name or 'all'}
        
        2. Verify channel activity (bytes/messages sent and received)
           - Metrics: ibmmq.channel.bytes_sent, ibmmq.channel.bytes_received
           - Metrics: ibmmq.channel.messages_sent, ibmmq.channel.messages_received
        
        3. Check connection percentage
           - Metrics: ibmmq.channel.connection_percentage
        
        4. Analyze channel utilization and capacity
           - Metrics: ibmmq.channel.utilization
        
        5. Review buffer statistics
           - Metrics: ibmmq.channel.buffers_sent, ibmmq.channel.buffers_received

        6. Check network connectivity at host level
           - Entity: "host"
           - Metrics: network errors, packet loss
           - Filter by hosts running {queue_manager or 'queue managers'}

        Cross-Tool Integration:
        7. **Check for related Instana events** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 7a - Specific search (try first):**
           - operation: "get_events"
           - params: {{
               "problem": "channel",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Searches for channel-related events
           
           **Step 7b - If no results, search for connection issues:**
           - operation: "get_events"
           - params: {{
               "problem": "connection",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Broadens to any connection-related events
           
           **Step 7c - If still no results, check network events:**
           - operation: "get_events"
           - params: {{
               "problem": "network",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Looks for network connectivity issues
           
           - Note: Channel issues may manifest as network or connectivity events

        8. **Check remote queue manager status**:
           - Entity: "ibm mq queue manager"
           - Filter by remote queue manager
           - Benefit: Identifies if remote side is down

        9. **Analyze application impact** (manage_applications):
           - Check services using this channel
           - Look for increased error rates or timeouts
           - Benefit: Quantifies business impact

        10. **Check recent releases** (manage_releases):
            - operation: "get_all_releases"
            - Look for network or MQ configuration changes
            - Benefit: Correlates channel issues with changes

        Resolution: Start channel, check network, verify channel definitions match
        """

    @auto_register_prompt
    @staticmethod
    def debug_ibmmq_mft_transfer_failures(
        agent_name: Optional[str] = None,
        queue_manager: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Debug IBM MQ MFT file transfer failures"""
        return f"""
        Debug IBM MQ MFT transfer failures:
        - Agent name: {agent_name or '(will query all agents)'}
        - Queue manager: {queue_manager or '(will query all)'}
        - Time range: {time_range or '1h'}

        Infrastructure Analysis Steps:
        1. Check MFT agent status using entity "ibm mq mft agent"
           - Metrics: ibmmq.mft.agent.status
           - Filter by agent name: {agent_name or 'all'}
        
        2. Analyze transfer statistics using entity "ibm mq mft coordinator"
           - Metrics: ibmmq.mft.coordinator.transfers_active
           - Metrics: ibmmq.mft.coordinator.transfers_failed
        
        3. Check for retrying and timed-out transfers
           - Metrics: ibmmq.mft.agent.transfers_retrying
           - Metrics: ibmmq.mft.agent.transfers_timed_out
        
        4. Verify agent activity and processing
           - Metrics: ibmmq.mft.agent.transfers_in_progress
        
        5. Review coordinator health
           - Entity: "ibm mq mft coordinator"
           - Check all coordinator metrics

        6. Check disk space on agent hosts
           - Entity: "host"
           - Metrics: disk.used_percent
           - Filter by hosts running MFT agents

        Cross-Tool Integration:
        7. **Check for related Instana events** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 7a - Specific search (try first):**
           - operation: "get_events"
           - params: {{
               "problem": "transfer",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Searches for MFT transfer-related events
           
           **Step 7b - If no results, search for agent issues:**
           - operation: "get_events"
           - params: {{
               "problem": "agent",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Looks for MFT agent events
           
           **Step 7c - If still no results, check all MFT-related events:**
           - operation: "get_events"
           - params: {{
               "problem": "mft",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Broadens to any MFT-related events
           
           - Note: MFT issues may also appear as queue or channel events

        8. **Check queue manager health**:
           - Entity: "ibm mq queue manager"
           - Filter by {queue_manager or 'all'}
           - Benefit: Ensures underlying MQ infrastructure is healthy

        9. **Check network connectivity**:
           - Entity: "host"
           - Check network metrics between source and destination
           - Benefit: Identifies network issues affecting transfers

        10. **Check recent releases** (manage_releases):
            - operation: "get_all_releases"
            - Look for MFT configuration or agent updates
            - Benefit: Correlates failures with changes

        11. **Analyze application logs** (if available):
            - Check for file permission errors
            - Check for path configuration issues
            - Benefit: Identifies application-level problems

        Resolution: Start agent, verify paths, check connectivity and disk space
        """

    @auto_register_prompt
    @staticmethod
    def monitor_ibmmq_health(
        queue_manager: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Monitor overall IBM MQ infrastructure health"""
        return f"""
        Monitor IBM MQ infrastructure health:
        - Queue manager: {queue_manager or '(all queue managers)'}
        - Time range: {time_range or '1h'}

        Infrastructure Analysis Steps:
        1. Check queue manager health (status, connections, channels, failures)
           - Entity: "ibm mq queue manager"
           - Metrics: status, connection_count, channel_count, mqi_failures
        
        2. Monitor queue utilization across all queues
           - Entity: "ibm mq queue"
           - Metrics: depth, max_depth, usage percentage
        
        3. Check channel performance and connectivity
           - Entity: "ibm mq channel"
           - Metrics: status, messages sent/received, connection percentage
        
        4. Monitor MFT transfer success rates
           - Entity: "ibm mq mft agent"
           - Metrics: transfers active, failed, retrying
        
        5. Review message age and processing times
           - Entity: "ibm mq queue"
           - Metrics: oldest_message_age

        Cross-Tool Integration:
        6. **Check for active incidents** (manage_events) - PROGRESSIVE SEARCH STRATEGY:
           
           IMPORTANT: IBM MQ events use entityType="INFRASTRUCTURE", NOT "ibmmq"
           
           **Step 6a - Get all open incidents (recommended for health monitoring):**
           - operation: "get_events"
           - params: {{
               "state": "open",
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Then filter results for IBM MQ-related events by checking:
             * entityLabel contains queue manager names (e.g., "QM*", "*@host")
             * entityLabel contains queue names (e.g., "SYSTEM.*", "AMQ.*")
             * problem field contains MQ-related keywords
           
           **Step 6b - If too many results, filter by severity:**
           - operation: "get_events"
           - params: {{
               "state": "open",
               "severity": 10,
               "time_range": "{time_range or '1h'}",
               "event_type_filters": ["INCIDENT", "ISSUE"]
             }}
           - Focuses on critical issues only
           
           - Benefit: Identifies current issues requiring attention
           - Note: For health monitoring, start broad and filter results manually

        7. **Review recent changes** (manage_releases):
           - operation: "get_all_releases"
           - params: {{"time_range": "{time_range or '24h'}"}}
           - Benefit: Correlates health changes with deployments

        8. **Check application health** (manage_applications):
           - resource_type: "metrics"
           - Check services using IBM MQ
           - Look for error rates and latency spikes
           - Benefit: Ensures end-to-end health

        Key Health Indicators:
        - Queue Manager: Running status, active connections
        - Queues: Utilization < 80%, messages flowing
        - Channels: Connected, data transferring
        - MFT: Transfers succeeding, agents active
        """

    @classmethod
    def get_prompts(cls):
        """Get all prompts defined in this class"""
        return [
            ('infra_available_metrics', cls.infra_available_metrics),
            ('infra_get_entities', cls.infra_get_entities),
            ('infra_available_plugins', cls.infra_available_plugins),
            ('debug_ibmmq_queue_full', cls.debug_ibmmq_queue_full),
            ('debug_ibmmq_invalid_queue', cls.debug_ibmmq_invalid_queue),
            ('debug_ibmmq_qmgr_down', cls.debug_ibmmq_qmgr_down),
            ('debug_ibmmq_large_messages', cls.debug_ibmmq_large_messages),
            ('debug_ibmmq_auth_failure', cls.debug_ibmmq_auth_failure),
            ('debug_ibmmq_empty_queue', cls.debug_ibmmq_empty_queue),
            ('debug_ibmmq_channel_issues', cls.debug_ibmmq_channel_issues),
            ('debug_ibmmq_mft_transfer_failures', cls.debug_ibmmq_mft_transfer_failures),
            ('monitor_ibmmq_health', cls.monitor_ibmmq_health),
        ]
