Configuration 
The OpenDR endpoint monitoring system utilizes two primary configuration files to manage system behavior and database connections: 

- agentconfig.ini governs sensor operation
- dbconfig.ini governs database mode

The agentconfig.ini file serves as the central configuration point for all monitoring activities. It is organized into three main sections:

The General section controls system-wide parameters:
- OperatingSystem: Set the operating system mode (Windows, Linux, or MacOS)
- LogProfile: Set the logging scripts to be executed by assigning one of three pre-baked profiles (basic, advanced or complete) or 'custom' which will allow you to run your preference based on the Scripts parameter of the OS mode
- RunDatabaseOperations: Controls whether database operations are enabled (default False)
- LoggingInterval: Determines the frequency of log file rotation (minute, hour, or day)
- DatabaseInterval: Sets the interval for database operations (default 30 seconds)
- CleanupInterval: Specifies the cleanup interval for processed log files (default 30 minutes)

The Windows section configures Windows-specific monitoring:
- Scripts: Lists all Windows monitoring scripts to be executed by the custom log profile
- EndpointInterval: Sets the endpoint info logging interval (default 43200 seconds)
- NetworkInterval: Controls network logging frequency (default 0.1 seconds)
- ProcessInterval: Sets process logging frequency (default 0.1 seconds)
- SoftwareInterval: Defines software inventory logging interval (default 43200 seconds)
- UserInterval: Sets user info logging frequency (default 1 second)
- ServiceInterval: Controls service logging interval (default 60 seconds)
- HotfixInterval: Sets hotfix logging frequency (default 43200 seconds)
- DefenderInterval: Sets defender info logging frequency (default 60 seconds)
- AutorunInterval: Sets autorun logging frequency (default 43200 seconds)
- DriverInterval: Sets windows driver logging frequency (default 43200 seconds)
- TaskInterval: Sets windows task logging frequency (default 43200 seconds)

The Linux section configures Linux-specific monitoring:
- Scripts: Lists all Linux monitoring scripts to be executed by the custom log profile
- EndpointInterval: Sets the endpoint info logging interval (default 43200 seconds)
- NetworkInterval: Controls network logging frequency (default 0.1 seconds)
- ProcessInterval: Sets process logging frequency (default 0.1 seconds)
- SoftwareInterval: Defines software inventory logging interval (default 43200 seconds)
- ServiceInterval: Controls service logging interval (default 43200 seconds)
- CronLogInterval: Controls cron job logging interval (default 43200 seconds)
- KernelInterval: Controls linux kernel logging interval (default 43200 seconds)
- UserInterval: Sets user info logging frequency (default 1 second)

The MacOS section configures MacOS-specific monitoring:
- Scripts: Lists all MacOS monitoring scripts to be executed by the custom log profile
- EndpointInterval: Sets the endpoint info logging interval (default 43200 seconds)
- NetworkInterval: Controls network logging frequency (default 0.1 seconds)
- ProcessInterval: Sets process logging frequency (default 0.1 seconds)
- UserInterval: Sets user info logging frequency (default 1 second)

The dbconfig.ini file manages database connection settings:

- HostName: Specifies the database host (currently empty)
- PortNumber: Sets the database port (default 4000)
- DatabaseName: Defines the database name (default opendr)
- RootDatabaseUserName: Specifies the root username (default postgres)
- RootDatabasePassword: Stores the root database password (currently empty)
- AgentUserName: Defines the agent username (default agent)
- AgentPassword: Stores the agent user password (currently empty)
- AppUserName: Specifies the application username (default app)
- AppUserPassword: Stores the application user password (currently empty)
- SSLRootCert: Configures the path to the database TLS certificate (currently empty)

This configuration system provides a flexible and centralized way to manage monitoring activities and database connections across different operating systems. The modular design allows administrators to enable or disable specific monitoring capabilities and adjust monitoring intervals to meet specific requirements.
