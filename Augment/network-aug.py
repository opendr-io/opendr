import time
from datetime import datetime, timedelta
import psycopg
import configparser
import pathlib
import socket
import concurrent.futures
from ipwhois import IPWhois
from ipwhois.exceptions import IPDefinedError

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

def get_dns_name(ip):
    """Perform a non-blocking reverse DNS lookup."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(socket.gethostbyaddr, ip)
        try:
            return future.result(timeout=2)[0]  # Timeout after 2 seconds
        except (socket.herror, socket.gaierror, concurrent.futures.TimeoutError):
            return 'none'  # Populate 'none' if DNS lookup fails

def get_as_name(ip):
    """Perform an AS (Autonomous System) lookup if DNS resolution fails."""
    try:
        obj = IPWhois(ip)
        result = obj.lookup_rdap(depth=1)
        return result.get("asn_description", "Unknown ASN")
    except IPDefinedError:
        return "Private IP"
    except Exception:
        return "Unknown ASN"

def get_resolved_name(ip):
    """Attempt to resolve DNS first, then fallback to AS lookup."""
    dns_name = get_dns_name(ip)
    as_name = 'skipped-dns' if dns_name != 'none' else get_as_name(ip)
    return dns_name, as_name 

def fetch_unique_ips():
    with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                        user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
        with connection.cursor() as cursor:
            ips = cursor.execute(f"SELECT DISTINCT(sourceip) FROM systemevents WHERE timestmp > '{(datetime.now() - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')}'").fetchall()
        connection.close()
    return [ip[0] for ip in ips]

def enrich_network(ip, dns_name, as_name):
    with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                        user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE systemevents SET dnsname = '{dns_name}', asname = '{as_name}' WHERE sourceip = '{ip}' AND timestmp > '{(datetime.now() - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')}'")
        connection.commit()

def run():
    interval = 43200.0
    print('network enrichment running')
    while True:
        ips = fetch_unique_ips()
        for ip in ips:
            dns_name, as_name = get_resolved_name(ip)
            enrich_network(ip, dns_name, as_name)
        time.sleep(interval)

run()