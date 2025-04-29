import psycopg
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

def setup_postgres_tables():
  applications_table = 'applications(timestmp, hostname, sid, ec2instanceid, program, servicename, displayname, status, start, username, pid, executable)'
  system_events_table = 'systemevents(timestmp, hostname, event, pid, process, sid, username, executable, commandline, dnsname, dnsdate, sourceip, sourceport, destip, destport, asname, status, onterminal, fromhostname, logintime)'
  print('Initiating Database Connection')
  with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), 
                      password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
    print('Connection Made!')
    with connection.cursor() as cursor:
      print('Creating PostgreSQL Database')
      cursor.execute(f"CREATE DATABASE {config.get('Database', 'DatabaseName', fallback='opendr')}")
      print('Database Created!')
    connection.commit()

  with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                      user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword')) as connection:
    with connection.cursor() as cursor:
      print('Creating PostgreSQL Tables and Users')
      cursor.execute("""CREATE TABLE endpointinfo (id serial PRIMARY KEY, timestmp text, hostname text, ec2instanceid text, privateips text, publicip text, event text, username text,
        onterminal text, fromhostname text, logintime text, sid text)""")
      cursor.execute("""CREATE TABLE systemevents (id serial PRIMARY KEY, timestmp text, event text, pid text, name text, hostname text, ppid text,
        parent text, username text, dnsname text, dnsdate text, sourceip text, sourceport text, destip text, destport text, asname text, status text, 
        onterminal text, fromhostname text, logintime text, sid text)""")
      print('Tables Created!')
      cursor.execute(f"CREATE USER {config.get('Database', 'AgentUserName', fallback='agent')} WITH PASSWORD '{config.get('Database', 'AgentPassword')}'")
      cursor.execute(f"CREATE USER {config.get('Database', 'AppUserName', fallback='app')} WITH PASSWORD '{config.get('Database', 'AppUserPassword')}'")
      cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {config.get('Database', 'AgentUserName', fallback='agent')}")
      cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {config.get('Database', 'AppUserName', fallback='app')}")
      cursor.execute(f"GRANT INSERT ON ALL TABLES IN SCHEMA public TO {config.get('Database', 'AgentUserName', fallback='agent')}")
      cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {config.get('Database', 'AppUserName', fallback='app')}")
      print('Users Created!')
    connection.commit()

setup_postgres_tables()