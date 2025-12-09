Feature: Network Stress Testing Using Virtual Clients
  To ensure that the router performs reliably under heavy load,
  As a network tester,
  I want to automatically create multiple virtual clients using macvlan
  And verify that each client receives a valid IP and can reach the router.

  Background:
    Given the router IP address is configured
    And the base network interface is available on the system

  Scenario: Stress test router with varying number of clients
    Given I create "5" virtual clients using macvlan
    Then no two clients should receive the same IP address
    And all assigned IPs should be reachable
    When all clients attempt to ping the router simultaneously "IPV4"
    Then each client should successfully reach the router


