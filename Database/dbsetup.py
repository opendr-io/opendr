import psycopg
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

def setup_postgres_database() -> None:
  print('Initiating Database Connection')
  with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), 
                        password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
    print('Connection Made!')
    with connection.cursor() as cursor:
      print('Creating PostgreSQL Database')
      cursor.execute(f"CREATE DATABASE {config.get('Database', 'DatabaseName', fallback='opendr')}")
      print('Database Created!')
    connection.commit()

def setup_postgres_tables() -> None:
  with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                      user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword')) as connection:
    with connection.cursor() as cursor:
      cursor.execute("""
        CREATE TABLE applications (
          id serial PRIMARY KEY, 
          timestamp text, 
          hostname text, 
          event text, 
          ec2_instance_id text, 
          program text, 
          description text, 
          name text, 
          status text, 
          state text, 
          username text, 
          identifier text, 
          image text,
          vendor text,
          version text,
          guid text
        )""")
      cursor.execute("""
          CREATE TABLE endpointinfo (
            id serial PRIMARY KEY, 
            timestmp text, 
            hostname text,  
            ec2instanceid text, 
            privateips text, 
            publicip text, 
            event text, 
            username text,
            onterminal text, 
            fromhostname text, 
            logintime text, 
            sid text
          )""")
      cursor.execute("""
          CREATE TABLE systemevents (
            id serial PRIMARY KEY, 
            timestamp text, 
            category text, 
            processid integer, 
            process text, 
            hostname text, 
            parentprocessid text,
            parentimage text, 
            username text, 
            dnsname text, 
            dnsdate text, 
            sourceip text, 
            sourceport text, 
            destinationip text, 
            destinationport text, 
            asname text, 
            status text, 
            image text, 
            commandline text, 
            sid text
          )""")
      cursor.execute("""
          CREATE TABLE systemalerts (
            id serial PRIMARY KEY, 
            timestmp text, 
            event text, 
            username text, 
            title text, 
            severity text,
            category text, 
            executable text, 
            filepath text, 
            eventid integer, 
            threatid integer, 
            origin text, 
            type text, 
            source text, 
            description text, 
            reference text, 
            sid text
          )""")
      connection.commit()
      print('Tables Created!')

def setup_postgres_users() -> None:
  with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                      user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword')) as connection:
    with connection.cursor() as cursor:
      cursor.execute(f"CREATE USER {config.get('Database', 'AgentUserName', fallback='agent')} WITH PASSWORD '{config.get('Database', 'AgentPassword')}'")
      cursor.execute(f"CREATE USER {config.get('Database', 'AppUserName', fallback='app')} WITH PASSWORD '{config.get('Database', 'AppUserPassword')}'")
      cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {config.get('Database', 'AgentUserName', fallback='agent')}")
      cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {config.get('Database', 'AppUserName', fallback='app')}")
      cursor.execute(f"GRANT INSERT ON ALL TABLES IN SCHEMA public TO {config.get('Database', 'AgentUserName', fallback='agent')}")
      cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {config.get('Database', 'AppUserName', fallback='app')}")
      connection.commit()
      print('Users Created!')

setup_postgres_database()
setup_postgres_tables()
setup_postgres_users()