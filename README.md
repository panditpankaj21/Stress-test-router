# Stress-Test Router

**Stress-Test Router** is a tool to evaluate router performance by simulating multiple virtual clients using **Linux network namespaces** and **macvlan** technology. It runs an asynchronous workload on a **Raspberry Pi** while continuously monitoring system health metrics.

[![Behave](https://img.shields.io/badge/Behave-BDD%20Framework-green)](https://behave.readthedocs.io/en/stable/)
[![Linux Kernel](https://img.shields.io/badge/Linux-Kernel%20Docs-black)](https://kernel.org/doc/html/latest/)
[![Network Namespace](https://img.shields.io/badge/Network%20Namespace-Isolation%20Tech-blue)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen)](https://github.com/panditpankaj21/Stress-test-router/actions)
[![Documentation](https://img.shields.io/badge/Docs-Available-blue)](https://github.com/panditpankaj21/Stress-test-router/tree/main/docs)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-yellow)](https://www.python.org/downloads/release/python-3100/)
[![Raspberry Pi](https://img.shields.io/badge/Platform-Raspberry%20Pi-red)](https://www.raspberrypi.com/software/)
[![License](https://img.shields.io/github/license/panditpankaj21/Stress-test-router)](https://github.com/panditpankaj21/Stress-test-router/blob/main/LICENSE)


---

## Overview

Simulates numerous virtual clients to stress-test routers and networks. It facilitates deep insights by simulating client traffic and monitoring:

- DHCP behavior  
- IP assignment stability  
- Download speeds  
- Ping latency  
- Raspberry Pi system stats: CPU usage, memory usage, temperature, and load during tests  

### Use Cases

- Router testing labs  
- IoT and home network experiments  
- Raspberry Pi network performance benchmarking  
- Automated network stress testing  

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

Configure the test parameters in `config.yaml`:

| Parameter          | Description                            |
|--------------------|------------------------------------|
| `interface`        | Network interface (e.g., eth0, wlan0) |
| `router_ip`        | Router's default gateway IP address  |
| `ping_duration`    | Duration in seconds for ping tests    |
| `download_timeout` | Maximum download test time (seconds)  |
| `client_count`     | Number of virtual clients (namespaces) |

### Example Configuration

interface: "eth0"
router_ip: "192.168.1.1"
ping_duration: 30
download_timeout: 60
client_count: 20

---

## Running Tests

**Root privileges are required to create network namespaces and macvlan interfaces.**

- Run all tests:

```bash
sudo behave
```

- Run a specific feature, for example ping:

```bash
sudo behave features/ping.feature
```

- Run tests by tag (e.g., download tests):

```bash
sudo behave --tags "@download"
```

---

## Contributing

Contributions are highly appreciated! Please follow these steps:

1. Fork the repository  
2. Create a feature branch (`git checkout -b feature-name`)  
3. Commit your changes with clear messages  
4. Push to your branch and open a Pull Request  

> All PRs require passing CI checks before merging.

---

## License

This project is licensed under the [MIT License](https://github.com/panditpankaj21/Stress-test-router/blob/main/LICENSE).
