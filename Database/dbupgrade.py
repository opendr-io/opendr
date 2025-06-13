import psycopg
import configparser
import pathlib
import json

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

def run_postgres_upgrade(queries):
    with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                    user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword')) as connection:
        with connection.cursor() as cursor:
            for query in queries:
                print(query)
                cursor.execute(query)
            connection.commit()

def update_postgres_users():
    with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                    user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword')) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {config.get('Database', 'AgentUserName', fallback='agent')}")
            cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {config.get('Database', 'AppUserName', fallback='app')}")
            cursor.execute(f"GRANT INSERT ON ALL TABLES IN SCHEMA public TO {config.get('Database', 'AgentUserName', fallback='agent')}")
            cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {config.get('Database', 'AppUserName', fallback='app')}")
            connection.commit()

def run():
    with open('upgrades.json', 'r') as file:
        d = json.load(file)

    patches = config.get('Upgrade', 'Patches', fallback='').split(', ')
    for patch in patches:
        if patch not in d:
            continue
        run_postgres_upgrade(d[patch])
    update_postgres_users()

run()