**PostgreSQL Setup**

1.  Go to the following link to download Postgres and select the one
    based on the operating system you are running and download the 17.4🡪
    [Postgres
    Download](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)

    <img width="387" alt="image" src="https://github.com/user-attachments/assets/9d6166dc-50e6-4dc5-a80a-2b48024bb9f8" />


2.  Once you have downloaded the file double click on the executable to
    start the installation process. When the installation window pops
    up, keep selecting next until you reach the following window.

    <img width="334" alt="image" src="https://github.com/user-attachments/assets/49ef5f70-525a-4cfa-a3d6-008c32a8d5f8" />


3.  Once you arrive here change the installation directory to the D
    drive as shown in the image below and click next

    <img width="340" alt="image" src="https://github.com/user-attachments/assets/d4edb066-027a-435b-8f51-232ba4858118" />


4.  In the following window make sure that all the items are select as
    shown below and click Next

    <img width="323" alt="image" src="https://github.com/user-attachments/assets/9226c156-0e4b-4af5-859f-f2df600adf0d" />


5.  In the following page make sure that the data directory in also in
    the D drive as shown below and click Next

    <img width="286" alt="image" src="https://github.com/user-attachments/assets/1477ada4-7e71-41e5-9730-1fa0b2131fe4" />


6.  In the following page you will be prompted to enter a root password
    for Postgres. Enter a password of your choosing and click Next

    <img width="328" alt="image" src="https://github.com/user-attachments/assets/cdf018bf-b20b-4b3a-a6b9-4a95ce8d47aa" />


7.  In the following page you will be prompted for a port number. Leave
    the default and click Next

    <img width="313" alt="image" src="https://github.com/user-attachments/assets/8b8a1264-de7e-4843-80c6-c9bb07664327" />


8.  The next window will ask for the locale. Keep the default selection
    and click Next

    <img width="312" alt="image" src="https://github.com/user-attachments/assets/1742259d-acad-4af8-ae61-a21295f12a2f" />


10.  Keep clicking Next and you will see the installation happening as
    shown below. This may take a few minutes

    <img width="328" alt="image" src="https://github.com/user-attachments/assets/5a2b9e76-8b9f-4212-9dd5-da6c9ea3d64e" />


11. Once the installation is done, you will reach the following page.
    You can keep the checkbox selected or deselect it if you feel you
    don't need any additional tools. Once you've made your decision
    click Finish.

    <img width="278" alt="image" src="https://github.com/user-attachments/assets/dc86f92f-4531-4ab9-bf0e-c7bc4ed0f2e9" />



**Setup Keys for SSL**

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


**Postgres TLS Setup**

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


**Database Setup**

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


**Beekeeper Studio Installation**

1.  Go to the following link to install Beekeeper Studio: [Beekeeper
    Studio Installation](https://www.beekeeperstudio.io/get)

2.  Once installed open Beekeeper Studio and select Postgres under
    "Connection Type" in the dropdown menu

    <img width="297" alt="image" src="https://github.com/user-attachments/assets/8ca1c58c-fe15-4647-ac11-c174e1f471bf" />


3.  Once you have selected that enter the IP address and port number
    along with your credentials and default database you are attempting
    to connect to as shown below.

    <img width="341" alt="image" src="https://github.com/user-attachments/assets/b65aa850-b482-48e4-baf1-d1bad0ea6910" />


4.  To connect to the database using TLS toggle and expand "Enable TLS"
    as shown below

    <img width="412" alt="image" src="https://github.com/user-attachments/assets/cb08cfec-818c-438e-a747-7f6e8c8c8f9a" />


5.  Once expanded enter your certificate file along with your
    database credentials to connect to the database. Uncheck "Reject
    Unauthorized" if using self-signed certificates as shown below

    ![image](https://github.com/user-attachments/assets/e59e1554-a55f-4f8a-aebd-a06be95dd5dd)

