from typing import Optional

from src.prompts import auto_register_prompt


class SyntheticSettingsPrompts:
    """Class containing synthetic settings related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_synthetic_test(test_id: Optional[str] = None, test_name: Optional[str] = None) -> str:
        """Retrieve a synthetic test's full record by ID or by name (name resolution supported)"""
        return f"""
        Get a synthetic test record by ID or name:
        - test_id: {test_id or 'None (supply test_name instead for name resolution)'}
        - test_name: {test_name or 'None (supply test_id instead for direct lookup)'}

        Supply either test_id (direct lookup) or test_name (case-insensitive label match).
        """

    @auto_register_prompt
    @staticmethod
    def get_synthetic_tests(
        application_id: Optional[str] = None,
        location_id: Optional[str] = None,
        credential_name: Optional[str] = None,
        sort: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter: Optional[str] = None,
    ) -> str:
        """List synthetic tests, optionally filtered by application, location, or credential, with pagination"""
        return f"""
        List synthetic tests with optional filters and pagination:
        - application_id: {application_id or 'None (no application filter)'}
        - location_id: {location_id or 'None (no location filter)'}
        - credential_name: {credential_name or 'None (no credential filter)'}
        - sort: {sort or "None (e.g. '+label' for ASC, '-label' for DESC)"}
        - offset: {offset or 'None (no page skip)'}
        - limit: {limit or 'None (return all)'}
        - filter: {filter or 'None (no attribute filter)'}

        All parameters are optional — omitting all returns every test.
        """

    @auto_register_prompt
    @staticmethod
    def get_locations(
        location_type: Optional[str] = None,
        status: Optional[str] = None,
        sort: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter: Optional[str] = None,
    ) -> str:
        """List all synthetic monitoring locations (PoPs) with full metadata including locationType, geoPoint, and datacenter flag"""
        return f"""
        List synthetic monitoring locations with optional filters:
        - location_type: {location_type or 'None (return all — use "Managed" for datacenters only, "Private" for self-hosted only)'}
        - status: {status or 'None (return all — use "Online" for active locations only)'}
        - sort: {sort or "None (e.g. '+label' for ASC, '-label' for DESC)"}
        - offset: {offset or 'None (no page skip)'}
        - limit: {limit or 'None (return all)'}
        - filter: {filter or 'None (no attribute filter)'}

        All parameters are optional — omitting all returns every location.

        DATACENTER IDENTIFICATION:
        - Locations with locationType="Managed" ARE datacenters (IBM Cloud / AWS / Azure hosted PoPs).
        - Locations with locationType="Private" are self-hosted PoPs — NOT datacenters.
        - NEVER use get_location_summary_list to identify datacenters — it does NOT return locationType.

        KEY FIELDS in each returned location record:
        - id: locationId used in all TAG_FILTER expressions for playback queries
        - label: stable internal name (e.g. "instana-release-aws-ap-south-1-Mumbai")
                 — matches locationLabel in datacenter config APIs
        - displayLabel: human-readable short name (e.g. "ap-south-1(Mumbai)")
                        — matches datacenter.label
        - customProperties.datacenterFlag: stable DC code (e.g. "aws-ap-south-1-Mumbai")
        - geoPoint: {{cityName, countryName, latitude, longitude}}
        - status: "Online" or "Offline"
        - totalTests: number of synthetic tests linked to this location

        WORKFLOW — to resolve a user-supplied datacenter name (e.g. "DAL12") to a locationId:
        1. Call get_locations (or get_all_datacenters) with no filters to get all Managed locations
        2. Match user input against displayLabel, label, or customProperties.datacenterFlag
        3. Extract the matching id
        4. Use that id in TAG_FILTER expressions for subsequent playback queries
        """

    @auto_register_prompt
    @staticmethod
    def get_location_by_id(
        location_id: Optional[str] = None,
        location_name: Optional[str] = None,
    ) -> str:
        """Retrieve a single synthetic monitoring location's full record by its ID or by name (name resolution supported)"""
        return f"""
        Get a single synthetic location record by ID or name:
        - location_id: {location_id or 'None (supply location_name instead for name resolution)'}
        - location_name: {location_name or 'None (supply location_id instead for direct lookup)'}

        Supply either location_id (direct lookup) or location_name (name resolution).

        NAME RESOLUTION — location_name is matched case-insensitively against:
        - label       (stable internal name, e.g. "instana-release-aws-ap-south-1-Mumbai")
                      — equivalent to datacenter.locationLabel
        - displayLabel (short human name, e.g. "ap-south-1(Mumbai)")
                       — equivalent to datacenter.label

        On no match, the error response includes available_location_names with id, label,
        and displayLabel for every known location to aid correction.

        Steps when location_name is provided:
        1. Fetch all locations internally
        2. Match location_name against label and displayLabel (case-insensitive)
        3. Resolve to the matching location_id
        4. Fetch and return the full location record for that id
        """

    @auto_register_prompt
    @staticmethod
    def get_all_datacenters(status: Optional[str] = None) -> str:
        """List all datacenter-backed synthetic monitoring locations (locationType=Managed only), with total online count"""
        return f"""
        Get all datacenter locations (locationType="Managed"):
        - status: {status or 'None (return all datacenters — use "Online" for active only)'}

        Returns: items (Managed location records), count (total matching), total_online (always
        the count of Online datacenters regardless of status filter), filters_applied.

        Each item contains the same rich schema as get_locations — id, label, displayLabel,
        geoPoint, customProperties.datacenterFlag, status, totalTests.

        Use get_all_datacenters (not get_location_summary_list) whenever you need:
        - The definitive list of datacenters (locationType discrimination is required)
        - The fleet denominator for health score calculations (total_online field)
        - Datacenter name → locationId resolution before playback queries

        IMPORTANT: get_location_summary_list does NOT return locationType and includes Private
        PoPs — it MUST NOT be used to enumerate datacenters or compute fleet health scores.
        """

    @auto_register_prompt
    @staticmethod
    def get_fleet_health_score(datacenter_count: Optional[int] = None) -> str:
        """Compute a single fleet health score: percentage of Online Managed datacenters where ALL synthetic tests are passing"""
        return f"""
        Compute the PowerVS / Instana fleet synthetic health score.
        - Expected datacenter count: {datacenter_count or 'None (discover dynamically from get_all_datacenters)'}

        DEFINITION:
        Fleet health score = (number of Online Managed datacenters where ALL tests have successRate = 1.0)
                     / (total number of Online Managed datacenters)  x 100

        A datacenter "passes" if and only if EVERY test assigned to it has successRate = 1.0.
        A datacenter "fails" if ANY test has successRate < 1.0 (even 0.99 counts as failing).

        FORBIDDEN CALCULATIONS — do NOT use any of the following approaches:
        - FORBIDDEN: weighted average of successRate across all test runs
          (e.g. sum(totalTestRuns * successRate) / sum(totalTestRuns) — this is WRONG)
        - FORBIDDEN: averaging successRates across tests without binary pass/fail per datacenter
        - FORBIDDEN: using get_location_summary_list as the datacenter enumeration source
          (it does NOT return locationType and includes Private PoPs)
        - FORBIDDEN: counting Private PoP locations as datacenters

        REQUIRED STEPS — follow this exact sequence:
        1. Call resource_type="settings", operation="get_all_datacenters", params={{"status": "Online"}}
           → Collect: all Online Managed locations → extract their ids and displayLabels
           → The total_online field from this response is the fleet denominator

        2. Call resource_type="test_playback", operation="get_test_summary_list"
           with payload: {{
             "metrics": [{{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}}],
             "timeFrame": {{"windowSize": 3600000}},
             "pagination": {{"page": 1, "pageSize": 200}}
           }}
           → Each result item contains locationStatusList: a list of per-location entries
             Each entry has: locationId, totalTestRuns, successRuns, successRate, locationDisplayLabel, locationType

        3. For EACH Online Managed datacenter from Step 1:
           a. Collect all locationStatusList entries whose locationId matches this datacenter's id
              AND locationType = "Managed"
           b. A datacenter PASSES if all its matching entries have successRate = 1.0
              (or if it has no test entries at all — treat as unknown, not failing)
           c. A datacenter FAILS if any entry has successRate < 1.0

        4. Compute:
           passing_datacenters = count of datacenters that PASS (binary, not averaged)
           fleet_health_score  = passing_datacenters / total_online x 100

        5. Report:
           - Fleet health score as a percentage (e.g. "73% — 22 of 30 datacenters fully passing")
           - List of failing datacenters with their displayLabel and lowest successRate
           - List of passing datacenters
           - Any datacenters with no test data (unknown status)
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_synthetic_test', cls.get_synthetic_test),
            ('get_synthetic_tests', cls.get_synthetic_tests),
            ('get_locations', cls.get_locations),
            ('get_location_by_id', cls.get_location_by_id),
            ('get_all_datacenters', cls.get_all_datacenters),
            ('get_fleet_health_score', cls.get_fleet_health_score),
        ]
