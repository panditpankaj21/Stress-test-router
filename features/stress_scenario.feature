Feature: Router Stress Testing using Virtual Clients
  To evaluate router CPU and performance under heavy concurrent load
  As a network tester
  I want multiple macvlan-based clients to generate traffic simultaneously\


  Background:
    Given the base network interface is available on the system


  Scenario: Run a basic mixed-traffic load test
    Given a stress scenario manager with duration "30" seconds and download URL "http://speedtest.tele2.net/20MB.zip"
    And I create "20" virtual clients using macvlan
    Then no two clients should receive the same IP address
    And all assigned IPs should be reachable
    When I start the stress test
    Then I should see results for each namespace