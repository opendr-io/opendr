import re
import psycopg
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

class StoreData:
  def __init__(self):
    self.host = config.get('Database', 'HostName')
    self.port = config.get('Database', 'PortNumber', fallback='4000')
    self.db = config.get('Database', 'DatabaseName', fallback='opendr')
    self.user = config.get('Database', 'AgentUserName', fallback='agent')
    self.password = config.get('Database', 'AgentPassword')
    self.sslmode = 'verify-ca'
    self.sslrootcert = config.get('Database', 'SSLRootCert')
    self.users_log_counter = 0
    self.endpoint_log_counter = 0
    self.network_log_counter = 0
    self.process_log_counter = 0
    self.services_log_counter = 0
    self.applications_installed_log_counter = 0

  @staticmethod
  def find_pattern(line):
    pattern = r'(\w+):([^|]+)(?:[,|]|$)'
    matches = re.findall(pattern, line)
    data = {key.strip(): value.strip() for key, value in matches}
    return data

  def store_process_events(self, filename):
    table = 'systemevents(timestmp, event, pid, name, hostname, ppid, parent, username, dnsname, dnsdate, sourceip, sourceport, destip, destport, asname, status, exe, cmdline, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'),  data.get('event'), data.get('pid'), data.get('name'), data.get('hostname'), data.get('ppid'), data.get('parent'), data.get('username')]
          final_params[9:9] = [''] * 8
          final_params.extend([ data.get('exe'),  data.get('cmdline'), data.get('sid')])
          fillers = ("%s," * 19)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_network_events(self, filename):
    table = 'systemevents(timestmp, event, pid, name, hostname, ppid, parent, username, dnsname, dnsdate, sourceip, sourceport, destip, destport, asname, status, exe, cmdline, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'),  data.get('event'), data.get('pid'), data.get('name'), data.get('hostname'), '', '', data.get('username'), '', '',
          data.get('sourceip'), data.get('sourceport'), data.get('destip'), data.get('destport'), '', data.get('status'), '', '', data.get('sid')]
          fillers = ("%s," * 19)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_installed_services(self, filename):
    table = 'applications(timestmp, hostname, pid, ec2instanceid, program, servicename, displayname, status, start, username, executable, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'),  data.get('hostname'), data.get('pid'), '', '', data.get('servicename'), data.get('displayname'), data.get('status'), data.get('start'), data.get('username'),  data.get('executable'), data.get('sid')]
          fillers = ("%s," * 12)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_installed_applications(self, filename):
    table = 'applications(timestmp, hostname, pid, ec2instanceid, program, servicename, displayname, status, start, username, executable, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'),  data.get('hostname'), '', data.get('instanceid'), data.get('program'), '', '', '', '', '', '', data.get('sid')]
          fillers = ("%s," * 12)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_endpoint_info(self, filename):
    table = 'endpointinfo(timestmp, event, hostname, ec2instanceid, privateips, publicip, username, onterminal, fromhostname, logintime, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), '', data.get('hostname'), data.get('ec2_instance_id'), data.get('private_ips'), data.get('public_ip'), '', '', '', '', data.get('sid')]
          fillers = ("%s," * 11)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_user_info(self, filename):
    table = 'systemevents(timestmp, event, pid, name, hostname, ppid, parent, username, dnsname, dnsdate, sourceip, sourceport, destip, destport, asname, status, exe, cmdline, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), '', '', data.get('hostname'), '', '',
                          data.get('username'), '', '', data.get('sourceip'), '', '', '', '', '', '', '',data.get('sid')]
          fillers = ("%s," * 19)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_new_service(self, filename):
    table = 'applications(timestmp, hostname, pid, ec2instanceid, program, servicename, displayname, status, start, username, executable, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'),  data.get('hostname'), data.get('pid'), '', '', data.get('servicename'), data.get('displayname'), data.get('status'), data.get('start'), data.get('username'),  data.get('executable'), data.get('sid')]
          fillers = ("%s," * 12)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_hotfix_info(self, filename):
    table = 'applications(timestmp, hostname, pid, ec2instanceid, program, servicename, displayname, status, start, username, executable, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('hostname'), '', '', '', data.get('name'), '', data.get('description'), '', data.get('username'), '', data.get('sid')]
          fillers = ("%s," * 12)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_defender_info(self, filename):
    table = 'systemalerts(timestmp, event, username, title, severity, category, executable, filepath, eventid, threatid, origin, type, source, description, reference, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('username'), data.get('title'), data.get('severity'), data.get('category'), data.get('executable'),
                          data.get('filepath'), data.get('eventid'), data.get('threatid'), data.get('origin'), data.get('type'), data.get('source'), data.get('description'), data.get('references'), data.get('sid')]
          fillers = ("%s," * 16)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()
