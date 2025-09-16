![logo](/img/opendr.jpg?raw=true "text")  
# OpenDR
A FOSS Endpoint Detection and Response (EDR) alternative implemented in Python using psutil and some Windows modules. Quick start:

0. Install Python 3.9 - 3.13
1. install the dependencies in the requirements file using pip install -r requirements (pref in a venv)
2. In the agentconfig.ini file, set the ```OperatingSystem=``` parameter to Windows, Linux or MacOS 
3. run sensor.py to start logging locally

If you are instrumenting an endpoint fleet, and need to ship logs to a database, see the database mode setup guide here. At present we started with Postgres but we can support other databases if you wish: https://github.com/cyberdyne-ventures/opendr/blob/main/setup.md

Common Components: these components use psutil which makes them portable across all three operating systems. This is what enabled us to ship sensors for Linux, Windows and the MacOS so quickly.

- The process component logs process events
- The network component logs network events
- The user component logs users that are present on the endpoint
- The endpoint info component logs essential endpoint identification information including hostname, IP addresses (both private and public), EC2 instance ID (for cloud environments), and unique identifiers such as the endpoint SID (Windows) or endpoint UUID (Linux and MacOS)
- The alert component can generate alerts on anything in our logs. Alert rules are defined in alertrules.csv.
- The Jupyter notebooks in the Jupyter folder can ingest OpenDR data for threat hunting. One notebook performs some simple anomaly detection and one is an experimental AI-assisted hunting notebook. That one needs a Groq API key which has a free tier, or you can use another model.

These components have different implementation details, across operating systems, but collect the same data types. These run twice per day, by default, but can be scheduled to run at any interval. Our thinking was that the cost / benefit ratio of logging all of this data once per hour, across a fleet, is not that high, esp where we don't need to repeat all that data at scale in order to detect new software and services. This means that we can be more efficient by generating a fraction of the data that some other tools produce.

- The services component inventories running services under Linux and Windows. We don't log stopped services by default but we can make that an option if you want us to
- The software component inventories installed Windows software and Linux packages
- The driver component inventories installed kernel drivers under Windows, with signer information, and kernel modules, under Linux.
- Scheduled tasks are inventoried under Windows and crontab entries under Linux.
- New services are logged under Windows and we're adding this to Linux. This will generate a log event whenever a new service starts for anomaly detection and / or threat hunting. 

Windows Components

- The Windows Defender components collects WD malware alerts. Want us to collect another alert source? Tell us what you want! 
- The hotfix log inventories installed hotfixes twice per day or it can run more often as you like. We use this data to identify CVEs for the Causality intrusion prediction project https://github.com/cyberdyne-ventures/predictions/tree/main
- Toasters: the alert component can optionally generate Toaster-style notifications to the user under Windows. 

Coming soon:

- SSH keys
- New drivers
- DNS and AS name enrichment
- USB drive activity
- File monitoring
- Agentic threat hunting and detection
- Your feature request here: tell us what you want!

About data privacy;

By default, OpenDR logs locally to the file system. Please run it on a D: drive under Windows to avoid consuming space on the C: drive; it can generate 10-25 MB of logs per day. *By default, no data leaves the host* unless you decide to use the database option. OpenDR has no cloud service of any kind at present. The endpoint module logs hostname, IP address, SID and instance ID information for correlation and hunting purposes. This module is optional and can be disabled if you don't want these things logged.



