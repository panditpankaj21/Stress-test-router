Feature: google ping

  Background: System Check
    Given the base network interface is available on the system

  Scenario: google ping
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients attempt to ping Google DNS "IPV6"
    Then each client should successfully reach the internet
