import re
import ssl
import shutil
import psycopg

class StoreData:
  def __init__(self):
    self.host = ''
    self.port = ''
    self.db = ''
    self.user = ''
    self.password=""
    self.sslmode = ''
    self.sslrootcert = ''
    self.users_log_counter = 0
    self.failed_users_log_counter = 0
    self.endpoint_log_counter = 0
    self.failed_endpoint_log_counter = 0
    self.network_log_counter = 0
    self.failed_network_log_counter = 0
    self.process_log_counter = 0
    self.failed_proccess_log_counter = 0
    self.services_log_counter = 0
    self.failed_service_log_counter = 0
    self.applications_installed_log_counter = 0
    self.failed_applications_installed_log_counter = 0

  def store_process_events(self, filename):
    table = 'systemevents(timestmp, event, pid, name, hostname, ppid, parent, username, dnsname, dnsdate, sourceip, sourceport, destip, destport, asname, status, onterminal, fromhostname, logintime, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          pattern = r'(\w+):([^|]+)(?:[,|]|$)'
          matches = re.findall(pattern, line)
          data = {key.strip(): value.strip() for key, value in matches}
          final_params = [data.get('timestamp'), data.get('event'), data.get('pid'), data.get('name'), data.get('hostname'), data.get('ppid'), data.get('parent'), data.get('username')]
          final_params[9:9] = [''] * 11
          final_params.append(data.get('sid'))
          fillers = ("%s," * 20)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          try:
            connection.execute(sqlInsertStatement, final_params)
            connection.commit()
            self.process_log_counter += 1
            with open('successfulstorage/successful-processlog-insertion.log', 'a') as file:
              file.write(f"Successful Database Writes: {self.process_log_counter} \n")
          except Exception as e:
            self.failed_proccess_log_counter += 1
            with open('failedstorage/unsuccessful-processlog-insertion.log', 'a') as file:
              file.write(f"Unsuccessful Database Writes: {self.failed_proccess_log_counter} \n")
              file.write(f"File: {filename} \n Line Attemped On: {final_params} \n SQL Statement: {sqlInsertStatement} \n\n")

  def store_network_events(self, filename):
    table = 'systemevents(timestmp, event, pid, name, hostname, ppid, parent, username, dnsname, dnsdate, sourceip, sourceport, destip, destport, asname, status, onterminal, fromhostname, logintime, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          pattern = r'(\w+):([^|]+)(?:[,|]|$)'
          matches = re.findall(pattern, line)
          data = {key.strip(): value.strip() for key, value in matches}
          final_params = [data.get('timestamp'),  data.get('event'), data.get('pid'), data.get('process'), data.get('hostname'), '', '', '', '', '',
          data.get('sourceip'), data.get('sourceport'), data.get('destip'), data.get('destport'), '', data.get('status'), '', '', '', data.get('sid')]
          fillers = ("%s," * 20)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          try:
            connection.execute(sqlInsertStatement, final_params)
            connection.commit()
            self.network_log_counter += 1
            with open('successfulstorage/successful-networklog-insertion.log', 'a') as file:
              file.write(f"Successful Database Writes: {self.network_log_counter} \n")
          except Exception as e:
            self.failed_network_log_counter += 1
            with open('successfulstorage/successful-networklog-insertion.log', 'a') as file:
              file.write(f"Unsuccessful Database Writes: {self.failed_network_log_counter} \n")
              file.write(f"File: {filename} \n Line Attemped On: {final_params} \n SQL Statement: {sqlInsertStatement} \n\n")

  def store_installed_services(self, filename):
    table = 'applications(timestmp, hostname, pid, ec2instanceid, program, servicename, displayname, status, start, username, executable, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          pattern = r'(\w+):([^|]+)(?:[,|]|$)'
          matches = re.findall(pattern, line)
          data = {key.strip(): value.strip() for key, value in matches}
          final_params = [data.get('timestamp'),  data.get('hostname'), data.get('pid'), '', '', data.get('servicename'), data.get('displayname'), data.get('status'), data.get('start'), data.get('username'),  data.get('executable'), data.get('sid')]
          fillers = ("%s," * 12)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          try:
            connection.execute(sqlInsertStatement, final_params)
            connection.commit()
            self.services_log_counter += 1
            with open('successfulstorage/successful-serviceslog-insertion.log', 'a') as file:
              file.write(f"Successful Database Writes: {self.services_log_counter} \n")
          except Exception as e:
            self.failed_service_log_counter += 1
            with open('failedstorage/unsuccessful-serviceslog-insertion.log', 'a') as file:
              file.write(f"Unsuccessful Database Writes: {self.failed_service_log_counter} \n")
              file.write(f"File: {filename} \n Line Attemped On: {final_params} \n SQL Statement: {sqlInsertStatement} \n\n")
          
  def store_installed_applications(self, filename):
    table = 'applications(timestmp, hostname, pid, ec2instanceid, program, servicename, displayname, status, start, username, executable, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          pattern = r'(\w+):([^|]+)(?:[,|]|$)'
          matches = re.findall(pattern, line)
          data = {key.strip(): value.strip() for key, value in matches}
          final_params = [data.get('timestamp'), data.get('hostname'), '', data.get('instanceid'), data.get('program'), '', '', '', '', '', '', data.get('sid')]
          fillers = ("%s," * 12)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          try:
            connection.execute(sqlInsertStatement, final_params)
            connection.commit()
            self.applications_installed_log_counter += 1
            with open('successfulstorage/successful-applicationsinstalledlog-insertion.log', 'a') as file:
              file.write(f"Successful Database Writes: {self.applications_installed_log_counter} \n")
          except Exception as e:
            self.failed_service_log_counter += 1
            with open('failedstorage/unsuccessful-applicationsinstalledlog-insertion.log', 'a') as file:
              file.write(f"Unsuccessful Database Writes: {self.failed_service_log_counter} \n")
              file.write(f"File: {filename} \n Line Attemped On: {final_params} \n SQL Statement: {sqlInsertStatement} \n\n")

  def store_endpoint_info(self, filename):
    table = 'endpointinfo(timestmp, event, hostname, ec2instanceid, privateips, publicip, username, onterminal, fromhostname, logintime, sid)'
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          pattern = r'(\w+):([^|]+)(?:[,|]|$)'
          matches = re.findall(pattern, line)
          data = {key.strip(): value.strip() for key, value in matches}
          final_params = [data.get('timestamp'), '', data.get('hostname'), data.get('ec2_instance_id'), data.get('private_ips'), data.get('public_ip'), '', '', '', '', data.get('sid')]
          fillers = ("%s," * 11)[:-1]
          sqlInsertStatement = 'INSERT INTO ' + table + ' VALUES('+fillers+')'
          try:
            connection.execute(sqlInsertStatement, final_params)
            connection.commit()
            self.endpoint_log_counter += 1
            with open('successfulstorage/successful-endpointinfolog-insertion.log', 'a') as file:
              file.write(f"Successful Database Writes: {self.endpoint_log_counter} \n")
          except Exception as e:
            self.failed_endpoint_log_counter += 1
            with open('failedstorage/unsuccessful-endpointinfolog-insertion.log', 'a') as file:
              file.write(f"Unsuccessful Database Writes: {self.failed_endpoint_log_counter} \n")
              file.write(f"File: {filename} \n Line Attemped On: {final_params} \n SQL Statement: {sqlInsertStatement} \n\n")
  
  def store_user_info(self, filename):
    tables = ['endpointinfo(timestmp, event, hostname, ec2instanceid, privateips, publicip, username, onterminal, fromhostname, logintime, sid)',
    'systemevents(timestmp, event, pid, name, hostname, ppid, parent, username, dnsname, dnsdate, sourceip, sourceport, destip, destport, asname, status, onterminal, fromhostname, logintime, sid)']
    with psycopg.connect(host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password, sslmode=self.sslmode, sslrootcert=self.sslrootcert) as connection:
      with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
          if(not line):
            continue
          pattern = r'(\w+):([^|]+)(?:[,|]|$)'
          matches = re.findall(pattern, line)
          data = {key.strip(): value.strip() for key, value in matches}
          final_params = [[data.get('timestamp'), data.get('event'), data.get('hostname'), '', '', '', data.get('username'), data.get('on_terminal'), data.get('from_hostname'), data.get('at_login_time'), data.get('sid')], 
          [data.get('timestamp'), data.get('event'), '', '', data.get('hostname'), '', '', data.get('username'), '', '', '', '', '', '', '', '', data.get('on_terminal'), data.get('from_hostname'), data.get('at_login_time'), data.get('sid')]]
          fillers = [("%s," * 11)[:-1], ("%s," * 20)[:-1]]
          sqlInsertStatements = ['INSERT INTO ' + tables[0] + ' VALUES('+fillers[0]+')', 'INSERT INTO ' + tables[1] + ' VALUES('+fillers[1]+')']
          try:
            connection.execute(sqlInsertStatements[0], final_params[0])
            connection.execute(sqlInsertStatements[1], final_params[1])
            connection.commit()
            self.users_log_counter += 1
            with open('successfulstorage/successful-endpointinfolog-insertion.log', 'a') as file:
              file.write(f"Successful Database Writes: {self.users_log_counter} \n")
          except Exception as e:
            self.failed_users_log_counter += 1
            with open('failedstorage/unsuccessful-endpointinfolog-insertion.log', 'a') as file:
              file.write(f"Unsuccessful Database Writes: {self.failed_users_log_counter} \n")
              file.write(f"File: {filename} \n Line Attemped On: {final_params[0]} \n SQL Statement: {sqlInsertStatements[0]} \n\n")
              file.write(f"File: {filename} \n Line Attemped On: {final_params[1]} \n SQL Statement: {sqlInsertStatements[1]} \n\n")