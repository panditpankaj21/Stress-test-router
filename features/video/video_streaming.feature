
Feature: Concurrent Video Streaming Stress Test
  As a Network Test Engineer
  I want to simulate multiple macvlan clients streaming High Definition video
  So that I can validate the router's ability to handle sustained multimedia traffic without buffering

  Background: System Check
    Given the base network interface is available on the system
    # And the video streaming configuration is loaded

  Scenario: Stream video on 5 clients simultaneously
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients start streaming a video simultaneously
    Then each client should successfully stream for the given duration