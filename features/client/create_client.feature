Feature: client creation

  Background: System Check
    Given the router IP address is configured
    And the base network interface is available on the system

  Scenario: client creation
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients attempt to ping the router simultaneously using "IPV4"
    Then each client should successfully reach the router

