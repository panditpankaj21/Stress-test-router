Feature: Router Stress Testing using Virtual Clients
  To evaluate router CPU and performance under heavy concurrent load
  As a network tester
  I want multiple macvlan-based clients to generate traffic simultaneously

  Background: System Check
    Given the base network interface is available on the system

  @mixed-stress
  Scenario: Run a basic mixed-traffic load test
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When I assign a random workload to each client for "30" seconds