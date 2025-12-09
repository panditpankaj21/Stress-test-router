Feature: High‑Load Parallel File Download Stress Test Validates router and network 
        stability under heavy outbound traffic by simulating multiple macvlan 
        clients downloading a 100GB file in parallel.

  Background:
    Given the base network interface is available on the system
    And a 20MB ZIP file URL is configured as the download source

  Scenario Outline: Validate parallel high-volume file downloads for multiple virtual clients
    Given I create "5" virtual clients using macvlan
    Then no two clients should receive the same IP address
    And all assigned IPs should be reachable
    When all clients start downloading the 20MB ZIP file simultaneously

