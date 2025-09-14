import re
import psycopg
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

class StoreData:
  def __init__(self):
    self.host: str = config.get('Database', 'HostName')
    self.port: str = config.get('Database', 'PortNumber', fallback='4000')
    self.db: str = config.get('Database', 'DatabaseName', fallback='opendr')
    self.user: str = config.get('Database', 'AgentUserName', fallback='agent')
    self.password: str = config.get('Database', 'AgentPassword')
    self.sslmode: str = config.get('Database', 'SSLMode')
    self.sslrootcert: str = config.get('Database', 'SSLRootCert')

  @staticmethod
  def find_pattern(line):
    pattern = r'(\w+):([^|]+)(?:[,|]|$)'
    matches = re.findall(pattern, line)
    data = {key.strip(): value.strip() for key, value in matches}
    return data

  def store_process_events(self, filename: str) -> None:
    table = 'systemevents(timestamp, category, processid, process, hostname, parentprocessid, parentimage, username, dnsname, dnsdate, sourceip, sourceport, destinationip, destinationport, asname, status, image, commandline, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines: list[str] = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'),  data.get('category'), data.get('processid'), data.get('process'), 
                          data.get('hostname'), data.get('parentprocessid'), data.get('parentimage'), data.get('username')]
          final_params[9:9] = [''] * 8
          final_params.extend([ data.get('image'),  data.get('commandline'), data.get('sid') or data.get('uuid')])
          fillers = ("%s," * 19)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_network_events(self, filename: str) -> None:
    table = 'systemevents(timestamp, category, processid, process, hostname, parentprocessid, parentimage, username, dnsname, dnsdate, sourceip, sourceport, destinationip, destinationport, asname, status, image, commandline, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines: list[str] = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'),  data.get('category'), data.get('processid'), data.get('process'), data.get('hostname'), '', '', data.get('username'), '', '',
          data.get('sourceip'), data.get('sourceport'), data.get('destinationip'), data.get('destinationport'), '', data.get('status'), '', '', data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 19)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_installed_services(self, filename: str) -> None:
    table: str = 'applications(timestamp, event, hostname, identifier, ec2_instance_id, program, description, name, status, state, username, image, vendor, version, guid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines: list[str] = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('hostname'), data.get('pid'), '', '', data.get('servicename'), data.get('displayname'), data.get('status'), data.get('start'),
                          data.get('username'), data.get('executable'), '', '', data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 15)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_installed_applications(self, filename: str) -> None:
    table: str = 'applications(timestamp, event, hostname, identifier, ec2_instance_id, program, description, name, status, state, username, image, vendor, version, guid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines: list[str] = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('hostname'), '', data.get('instanceid'), data.get('program'),
                          '', '', '', '', '', '', '', '', data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 15)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_endpoint_info(self, filename: str) -> None:
    table: str = 'endpointinfo(timestmp, event, hostname, ec2instanceid, privateips, publicip, username, onterminal, fromhostname, logintime, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines: list[str] = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), '', data.get('hostname'), data.get('ec2_instance_id'), data.get('private_ips'), data.get('public_ip'), '', '', '', '', data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 11)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()
  
  def store_user_info(self, filename: str) -> None:
    table = 'systemevents(timestamp, category, processid, process, hostname, parentprocessid, parentimage, username, dnsname, dnsdate, sourceip, sourceport, destinationip, destinationport, asname, status, image, commandline, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines: list[str] = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('category'), 0, '', data.get('hostname'), '', '',
                          data.get('username'), '', '', data.get('sourceip'), '', '', '', '', '', '', '', data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 19)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_hotfix_info(self, filename: str) -> None:
    table = 'applications(timestamp, event, hostname, identifier, ec2_instance_id, program, description, name, status, state, username, image, vendor, version, guid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('hostname'), '', '', '', data.get('description'), data.get('name'), '',
                          '', data.get('username'), '', '', '', data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 15)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_defender_info(self, filename: str) -> None:
    table = 'systemalerts(timestmp, event, username, title, severity, category, executable, filepath, eventid, threatid, origin, type, source, description, reference, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('username'), data.get('title'), data.get('severity'), data.get('category'), data.get('executable'),
                          data.get('filepath'), data.get('eventid'), data.get('threatid'), data.get('origin'), data.get('type'), data.get('source'), data.get('description'), data.get('references'), data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 16)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_driver_info(self, filename: str) -> None:
    table = 'applications(timestamp, event, hostname, identifier, ec2_instance_id, program, description, name, status, state, username, image, vendor, version, guid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('hostname'), '', data.get('ec2_instance_id'), '', data.get('desc'), 
                          data.get('friendly_name'), data.get('is_signed'), '', data.get('username'), data.get('pdo'), data.get('signer'), 
                          data.get('driver_version'), data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 15)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_autorun_info(self, filename: str) -> None:
    table = 'applications(timestamp, event, hostname, identifier, ec2_instance_id, program, description, name, status, state, username, image, vendor, version, guid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('hostname'), '', data.get('ec2_instance_id'), 
                          '', data.get('entry'), data.get('source'), '', '', '', data.get('path'), '', 
                          '', data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 15)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_scheduled_task_info(self, filename: str) -> None:
    table = 'applications(timestamp, event, hostname, identifier, ec2_instance_id, program, description, name, status, state, username, image, vendor, version, guid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('hostname'), '', data.get('ec2_instance_id'), 
                          '', data.get('task_to_run'), data.get('task_name'), data.get('status'), data.get('schedule'), data.get('author'), '', '', 
                          '', data.get('sid') or data.get('uuid')]
          fillers = ("%s," * 15)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()

  def store_debug_events(self, filename: str) -> None:
    table = 'systemlog(timestamp, event, hostname, source, platform, message, value)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          data = self.find_pattern(line)
          final_params = [data.get('timestamp'), data.get('event'), data.get('hostname'),
                          data.get('source'), data.get('platform'), data.get('message'), data.get('value')]
          fillers = ("%s," * 7)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          connection.execute(sqlInsertStatement, final_params)
          connection.commit()
