Feature: WiFi Connection with Network Replacement

  Scenario: One Wifi and others via virtual Ethernet
    Given the base network interface is available on the system
    And WiFi radio is on
    When I connect to WiFi
    Then WiFi should be connected
    And the config file should only have one network block
    And I should have IPv4 address
    Given I initialize the Network Manager
    When I provision "5" virtual clients using macvlan
    Then no two clients should have the same IP address
    And all assigned IPs should be reachable
    When all clients attempt to ping WiFi Client "IPV4" 
    When I turn off WiFi radio
    Then WiFi radio should be off