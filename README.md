![logo](/img/opendr.png?raw=true "text")  
# OpenDR
A FOSS Endpoint Detection and Response (EDR) alternative implemented in Python using psutil and some Windows modules. Setup:

0. Requires Python 3.9 - 3.12. 3.13 will be supported in the near future. 
1. install the dependencies in the requirements file using pip install -r requirements (pref in a venv)
2. run agent.py to start logging locally (please do this on a D: drive under Windows or something other than the C: drive)

Collects the following by default:

- process events with parent info
- network events with process info
- endpoint info including IP address and instance IDs
- endpoint SID (Windows)
- endpoint UUID (Linux)
- running services
- installed software

Coming soon:

- user information
- new services
- drivers and new drivers
- malware detections

About data privacy;

By default, OpenDR logs locally to the file system. Please run it on a D: drive under Windows to avoid consuming space on the C: drive; it can generate 10-25 MB of logs per day. *By default, no data leaves the host* unless you decide to use the database option. OpenDR has no cloud service of any kind at present. The endpoint module logs hostname, IP address, SID and instance ID information for correlation and hunting purposes. This module is optional and can be disabled if you don't want these things logged.

Database options: agents can optionally ship events to a Postgres database if you want centralized collection (this database can run wherever you wish.) Setup scripts and shippers are included and this will be covered in forthcoming docs.


