Feature: parallel download

  Background: System Check
    Given the base network interface is available on the system
    And the download target URL is configured

  Scenario: parallel download
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients start downloading the configured file simultaneously

