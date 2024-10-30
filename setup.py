from setuptools import setup, find_packages

setup(
    name="solaredge_mqtt_bridge",
    version="0.1.0",
    description="SolarEdge MQTT Bridge for reading data via Modbus and publishing to an MQTT broker.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Xerolux",
    author_email="git@xerolux.com",
    url="https://github.com/xerolux/solaredge_mqtt_bridge",
    packages=find_packages(),
    install_requires=[
        "pymodbus>=2.5.3",            # For Modbus communication
        "paho-mqtt>=1.6.1",           # For MQTT communication
        "pyyaml>=6.0",                # For YAML config handling
        "requests>=2.25.1",           # For API requests (e.g., weather data)
        "influxdb>=5.3.1",            # For InfluxDB communication
        "scikit-learn>=1.0.2",        # For ML models
        "joblib>=1.1.0",              # For saving/loading models
        "pandas>=1.3.3",              # For data manipulation
        "email-validator>=1.1.3",     # For validating email addresses
    ],
    entry_points={
        "console_scripts": [
            "solaredge_mqtt_bridge=solaredge_mqtt_bridge.main:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
