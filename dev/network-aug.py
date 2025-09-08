from datetime import datetime, timedelta
import psycopg
import configparser
import pathlib
import common.attributes as attr

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

class NetworkAug():
    def __init__(self):
        self.interval = attr.get_config_value('Augment', 'NetworkAugInterval', 43200.0, 'float')
        print("NetworkAug Initialization complete")

    def get_resolved_name(self, ip):
        """Attempt to resolve DNS first, then fallback to AS lookup."""
        dns_name = attr.get_dns_name(ip)
        as_name = 'skipped-dns' if dns_name != 'none' else attr.get_as_name(ip)
        return dns_name, as_name 

    def fetch_unique_ips(self):
        with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                            user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
            with connection.cursor() as cursor:
                ips = cursor.execute(f"SELECT DISTINCT(sourceip) FROM systemevents WHERE timestmp > '{(datetime.now() - timedelta(seconds=self.interval)).strftime('%Y-%m-%d %H:%M:%S')}'").fetchall()
            connection.close()
        return [ip[0] for ip in ips]

    def enrich_network(self, ip, dns_name, as_name) -> None:
        with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                            user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"UPDATE systemevents SET dnsname = '{dns_name}', asname = '{as_name}' WHERE sourceip = '{ip}' AND timestmp > '{(datetime.now() - timedelta(seconds=self.interval)).strftime('%Y-%m-%d %H:%M:%S')}'")
            connection.commit()

    def augment_events(self):
        print("Running Augment network")
        ips = self.fetch_unique_ips()
        for ip in ips:
            if not ip or ip == 'n/a':
                continue
            dns_name, as_name = self.get_resolved_name(ip)
            self.enrich_network(ip, dns_name, as_name)
