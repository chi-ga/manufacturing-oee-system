# Manufacturing OEE System

A system for tracking Overall Equipment Effectiveness (OEE) in manufacturing environments.

## Overview

This system helps monitor and analyze manufacturing equipment performance by tracking:

- **Availability** - Uptime vs. planned production time
- **Performance** - Actual throughput vs. maximum possible throughput
- **Quality** - Good products vs. total products produced

## Features

- Real-time OEE calculation and monitoring
- Equipment downtime tracking
- Production data collection and analysis
- Performance dashboards and reporting
- Alert system for OEE threshold violations

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
pip install -r requirements.txt
```

### Usage

```bash
python main.py
```

## Project Structure

```
manufacturing-oee-system/
├── README.md
├── requirements.txt
├── main.py
├── src/
│   ├── __init__.py
│   ├── oee_calculator.py
│   ├── data_collector.py
│   ├── equipment_monitor.py
│   └── reporting.py
├── tests/
│   └── ...
└── config/
    └── ...
```

## License

MIT