Feature: External Internet Reachability
  As a Network Test Engineer
  I want to verify that virtual clients can route traffic to the public internet
  So that I can confirm the NAT and Gateway configurations are working correctly

  Background: System Check
    Given the base network interface is available on the system

  Scenario: Verify IPv4 internet access for 5 concurrent virtual clients
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients attempt to ping Google DNS "IPV6"
    Then each client should successfully reach the internet
