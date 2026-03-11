# Router Performance and Stability Test

A test framework that simultae mulitiple clients and test the router performance and stability under high traffic.

[![Behave](https://img.shields.io/badge/Behave-BDD%20Framework-green)](https://behave.readthedocs.io/en/stable/)
[![Linux Kernel](https://img.shields.io/badge/Linux-Kernel%20Docs-black)](https://kernel.org/doc/html/latest/)
[![Network Namespace](https://img.shields.io/badge/Network%20Namespace-Isolation%20Tech-blue)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen)](https://github.com/panditpankaj21/Stress-test-router/actions)
[![Documentation](https://img.shields.io/badge/Docs-Available-blue)](https://panditpankaj21.github.io/Stress-test-router/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-yellow)](https://www.python.org/downloads/release/python-3100/)
[![License](https://img.shields.io/github/license/panditpankaj21/Stress-test-router)](https://github.com/panditpankaj21/Stress-test-router/blob/main/LICENSE)

---

## Overview

This tool gives freedom to create mulitple clients that connected to router and test your router under diffrent-different traffic generation such as:

1. Create multiple clients
2. Ping to router to check connectivity towards router
3. Ping to google.com/8.8.8.8, to check external connectivity via both IPV4 and IPV6
4. Prallel dowloading 10MB zip file
5. Video streaming, all client start streaming at the same time
6. Hybrid test, in this every client perfoming different differnt task for 30 sec. Simulating real-world secnario.
7. LAN-to-WLAN, one wifi client and others virtual client

### Use Cases

- Test Router performance and stability under high traffic
- Parallel execution of tests

---

## Quick Setup

Clone the repository and install required dependencies:

```bash
git clone https://github.com/panditpankaj21/Stress-test-router.git
```

```bash
cd Stress-test-router
```

```bash
pip install -r requirements.txt
```

---

## Configuration

1. `config.yaml` change the variable with yours:

   ```
   ROUTER_IPV4: "192.168.1.1"
   INTERFACE: "enp0s31f6"
   PING_DURATION: 30
   DOWNLOAD_TIMEOUT: 30   
   video_duration: 30   
   ```
2. create `.env` and update it with variable:

   ```
   ROUTER_MAC=""
   HOST=""
   USERNAME=""
   PASSWORD="pi_ssh_password"
   EMAIL=""
   DOMAIN=""
   PASSWD="router_ssh_password"
   SSH_TIMEOUT=
   WIFI_SSID=
   WIFI_PASSWORD=
   ```


---

## Running Tests

- Run all tests:

```bash
sudo behave
```

- Run a specific feature, for example ping:

```bash
sudo behave features/connectivity/goole_ping.feature
```

---

## Contributing

Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature-name`)
3. Commit your changes with clear messages
4. Push to your branch and open a Pull Request

> All PRs require passing CI checks before merging.

---

## License

This project is licensed under the [MIT License](https://github.com/panditpankaj21/Stress-test-router/blob/main/LICENSE).
