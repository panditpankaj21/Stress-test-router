Feature: hybrid test

  Background: System Check
    Given the base network interface is available on the system
    
  Scenario: hybrid test
    Given I initialize the Network Manager
    When I provision "50" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When I assign a random workload to each client for "7200" seconds