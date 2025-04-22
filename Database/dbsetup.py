import psycopg
from pathlib import Path

def setup_postgres_tables():
  applications_table = 'applications(timestmp, hostname, sid, ec2instanceid, program, servicename, displayname, status, start, username, pid, executable)'
  system_events_table = 'systemevents(timestmp, hostname, event, pid, process, sid, username, executable, commandline, dnsname, dnsdate, sourceip, sourceport, destip, destport, asname, status, onterminal, fromhostname, logintime)'
  print('Initiating Database Connection')
  with psycopg.connect() as connection:
    print('Connection Made!')
    with connection.cursor() as cursor:
      print('Creating PostgreSQL Database')
      cursor.execute("CREATE DATABASE opendr")
      print('Database Created!')
    connection.commit()

  with psycopg.connect() as connection:
    with connection.cursor() as cursor:
      print('Creating PostgreSQL Tables and Users')
      print('Users Created!')
      cursor.execute("""CREATE TABLE applications (id serial PRIMARY KEY, timestmp text, hostname text, ec2instanceid text, program text, servicename text, displayname text, status text, start text, username text, pid TEXT, executable text, sid text)""")
      cursor.execute("""CREATE TABLE endpointinfo (id serial PRIMARY KEY, timestmp text, hostname text,  ec2instanceid text, privateips text, publicip text, event text, username text,
      onterminal text, fromhostname text, logintime text, sid text)""")
      cursor.execute("""CREATE TABLE systemevents (id serial PRIMARY KEY, timestmp text, event text, pid integer, name text, hostname text, ppid text,
      parent text, username text, dnsname text, dnsdate text, sourceip text, sourceport text, destip text, destport text, asname text, status text, sid text)""")
      print('Tables Created!')
      cursor.execute("CREATE USER agent WITH PASSWORD 'Agent!123'")
      cursor.execute("CREATE USER app WITH PASSWORD 'user!123'")
      cursor.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO agent;")
      cursor.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app")
      cursor.execute("GRANT INSERT ON ALL TABLES IN SCHEMA public TO agent")
      cursor.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO app")
    connection.commit()

setup_postgres_tables()