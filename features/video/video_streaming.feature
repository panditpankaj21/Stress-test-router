
Feature: video streaming

  Background: System Check
    Given the base network interface is available on the system
    # And the video streaming configuration is loaded

  Scenario: video streaming
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients start streaming a video simultaneously
    Then each client should successfully stream for the given duration