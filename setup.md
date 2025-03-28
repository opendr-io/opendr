PostgreSQL Setup Guide

1.  Go to the following link to download Postgres and select the one
    based on the operating system you are running and download the 17.4🡪
    [Postgres
    Download](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)

![](media/image1.png){width="5.373915135608049in"
height="2.719682852143482in"}

2.  Once you have downloaded the file double click on the executable to
    start the installation process. When the installation window pops
    up, keep selecting next until you reach the following window.

![](media/image2.png){width="4.630225284339457in"
height="3.7057206911636045in"}

3.  Once you arrive here change the installation directory to the D
    drive as shown in the image below and click next

![](media/image3.png){width="4.715956911636045in"
height="3.6949759405074367in"}

4.  In the following window make sure that all the items are select as
    shown below and click Next

![](media/image4.png){width="4.482294400699913in"
height="3.6939501312335956in"}

5.  In the following page make sure that the data directory in also in
    the D drive as shown below and click Next

![](media/image5.png){width="3.982678258967629in"
height="3.2431583552055994in"}

6.  In the following page you will be prompted to enter a root password
    for Postgres. Enter a password of your choosing and click Next

![](media/image6.png){width="4.558752187226597in"
height="3.6737740594925636in"}

7.  In the following page you will be prompted for a port number. Leave
    the default and click Next

![](media/image7.png){width="4.3456321084864395in"
height="3.5408858267716536in"}

8.  The next window will ask for the locale. Keep the default selection
    and click Next

![](media/image8.png){width="4.327707786526684in"
height="3.442169728783902in"}

9.  Keep clicking Next and you will see the installation happening as
    shown below. This may take a few minutes

![](media/image9.png){width="4.54955927384077in"
height="3.627350174978128in"}

10. Once the installation is done, you will reach the following page.
    You can keep the checkbox selected or deselect it if you feel you
    don't need any additional tools. Once you've made your decision
    click Finish.

![](media/image10.png){width="3.8561198600174977in"
height="3.1143110236220473in"}

Setup Keys for SSL

1.  Here are the commands to create the key and certificate to use with
    Postgres. This would require you to have OpenSSL installed on your
    machine. If you don't have OpenSSL installed on Windows here's the
    link to get started: [OpenSSL
    Installation](https://slproweb.com/products/Win32OpenSSL.html)

> \# Server private key
>
> openssl genrsa -out postgres-server.key 4096
>
> \# Certificate Signing Request (CSR)
>
> openssl req -new -key postgres-server.key -out postgres-server.csr
> -subj \"/CN=rqlite-server\"
>
> \# Sign with CA
>
> openssl x509 -req -in postgres-server.csr -CA postgres-ca.crt -CAkey
> postgres-ca.key -CAcreateserial -out postgres-server.crt -days 365
> -sha256

Postgres TLS Setup

1.  When configuring TLS for Postgres go to the postgresql.conf file.
    This would be in the directory Postgres was installed in. The
    snippet should be below line 105 in the file. Here find the
    following code and turn on ssl, ssl_prefer_server_ciphers and
    ssl_ciphers. After that assign your ssl key to ssl_key_file and ssl
    certificate to ssl_cert_file.

> \# - SSL -
>
> ssl = on
>
> #ssl_ca_file = \'\'
>
> ssl_cert_file = \'\[certfile\]\'
>
> #ssl_crl_file = \'\'
>
> #ssl_crl_dir = \'\'
>
> ssl_key_file = \'\[keyfile\]\'
>
> ssl_ciphers = \'HIGH:MEDIUM:+3DES:!aNULL\'  # allowed SSL ciphers
>
> ssl_prefer_server_ciphers = on
>
> #ssl_ecdh_curve = \'prime256v1\'
>
> #ssl_min_protocol_version = \'TLSv1.2\'
>
> #ssl_max_protocol_version = \'\'
>
> #ssl_dh_params_file = \'\'
>
> #ssl_passphrase_command = \'\'
>
> #ssl_passphrase_command_supports_reload = off

2.  Once you have completed the above step go to pg_hba.conf which
    should be in the same directory and make the following changes. This
    would allow endpoints to be able to communicate and send telemetry
    to the database.

> \# \-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--
>
> \# Authentication Records
>
> \# \-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--
>
> \#
>
> \# This file controls: which hosts are allowed to connect, how clients
>
> \# are authenticated, which PostgreSQL user names they can use, which
>
> \# databases they can access.  Records take one of these forms:
>
> \#
>
> \# local         DATABASE  USER  METHOD  \[OPTIONS\]
>
> \# host          DATABASE  USER  ADDRESS  METHOD  \[OPTIONS\]
>
> hostssl all all 0.0.0.0/0 md5
>
> \# hostnossl     DATABASE  USER  ADDRESS  METHOD  \[OPTIONS\]
>
> \# hostgssenc    DATABASE  USER  ADDRESS  METHOD  \[OPTIONS\]
>
> \# hostnogssenc  DATABASE  USER  ADDRESS  METHOD  \[OPTIONS\]

3.  If you would like to configure the IP address, port number, and
    maximum connections that can be made to the database, go to
    "Connection Settings" in the postgresql.conf file which should be
    below line 58 in the file. There make the changes to the following
    lines

> listen_addresses = \'\*\'
>
>           \# comma-separated list of addresses;
>
>           \# defaults to \'localhost\'; use \'\*\' for all
>
>           \# (change requires restart)
>
> port = 5432
>
> max_connections = 100

Database Setup

The purpose of running this setup is to initialize the database with the
appropriate tables and users with the correct permissions to be able to
insert data from the agent.

1.  First clone the repository for the application from GitHub

2.  Once that's done go to navigate to the dev directory and run the
    following command: 

python dbsetup.py

Running this script will create the tables and the users needed to
ingest data from the agent. Once this is complete you can start the
agent by running the following command:

python agent.py

Beekeeper Studio Installation

1.  Go to the following link to install Beekeeper Studio: [Beekeeper
    Studio Installation](https://www.beekeeperstudio.io/get)

2.  Once installed open Beekeeper Studio and select Postgres under
    "Connection Type" in the dropdown menu

![](media/image11.png){width="4.130237314085739in"
height="2.603903105861767in"}

3.  Once you have selected that enter the IP address and port number
    along with your credentials and default database you are attempting
    to connect to as shown below.

![](media/image12.png){width="4.737689195100613in"
height="2.986868985126859in"}

4.  To connect to the database using TLS toggle and expand "Enable TLS"
    as shown below

![](media/image13.png){width="5.718104768153981in"
height="3.6049715660542434in"}

5.  Once expanded enter your key and certificate file along with your
    database credentials to connect to the database. Uncheck "Reject
    Unauthorized" if using self-signed certificates as shown below

![](media/image14.png){width="5.651995844269466in"
height="3.5632917760279965in"}