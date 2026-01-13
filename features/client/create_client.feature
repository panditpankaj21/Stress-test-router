Feature: Virtual Client Connectivity and Reachability
  As a Network Test Engineer
  I want to validate that the Router can handle multiple concurrent connections
  So that I can ensure stable IP allocation and packet forwarding for attached devices

  Background: System Check
    Given the router IP address is configured
    And the base network interface is available on the system

  Scenario Outline: Validate <protocol> connectivity with 5 concurrent virtual clients
    Given I initialize the Network Manager
    When I provision "2" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients attempt to ping the router simultaneously using "<protocol>"
    Then each client should successfully reach the router

    Examples:
      | protocol |
      | IPV4     |