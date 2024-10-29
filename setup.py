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
        "pymodbus>=2.5.3",
        "paho-mqtt>=1.6.1",
        "pyyaml>=6.0"
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
