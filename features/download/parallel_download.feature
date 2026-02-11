Feature: Concurrent File Download Stress Test
  As a Network Test Engineer
  I want to simulate multiple macvlan clients downloading large files simultaneously
  So that I can validate the router's throughput stability and packet handling under load

  Background: System Check
    Given the base network interface is available on the system
    And the download target URL is configured

  Scenario: Validate parallel downloads for 5 concurrent virtual clients
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients start downloading the configured file simultaneously

