import time
import importlib

try:
    import mysql.connector
except ImportError:
    print("\033[91mmysql.connector is not installed. Run 'pip install mysql-connector-python' \033[0m")


class MySQLConnection:
    def __init__(self, host='localhost', user='Hybrid_IDPS', password='css2', database='hybrid_idps'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.connect()

    def connect(self):
        self.connection = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )
        # if self.connection.is_connected():
        #     print(f'Connected to MySQL database as id {self.connection.connection_id}')
        # else:
        #     print('Failed to connect to MySQL database')

    def execute_query(self, sql_query):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(sql_query)
        results = cursor.fetchall()
        cursor.close()
        return results
        
    def disconnect(self):
        self.connection.close()
        # print('MySQL database connection closed.')
        
    def add_data_to_outer_layer(self, ip_address, geolocation, event_type, threat_level, dateTime, source_port, destination_port, protocol, payload):
        # need to implement dateTime. Its probs different standards from node.js to python to sql. make all utc iso whatever
        sql_query = "INSERT INTO outerLayer (ip_address, geolocation, event_type, threat_level, source_port, destination_port, protocol, payload) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor = self.connection.cursor()
        data = (ip_address, geolocation, event_type, threat_level, source_port, destination_port, protocol, payload)
        cursor.execute(sql_query, data)
        self.connection.commit()
        cursor.close()
        print('Data added to outerLayer successfully.')
        return True

    def add_data_to_outer_layer_bulk(self, data):
        try:
            sql_query = "INSERT INTO outerLayer (ip_address, geolocation, event_type, threat_level, timestamp) VALUES (%s, %s, %s, %s, %s)"
            cursor = self.connection.cursor()
            cursor.executemany(sql_query, data)
            self.connection.commit()
            cursor.close()
            print('Bulk data added to outerLayer successfully.')
            return True
        except Exception as e:
            print(f"Error adding bulk data to outerLayer: {e}")
            return False

class InnerLayer():
    def __init__(self) -> None:
        self.database = MySQLConnection()
        self.devices = {}
        self.threatTable = {
            "bruteForce": 0.2,
            "login":      0.9,
        }
        self.central_analyzer()

    def central_analyzer(self):
        interval = 1
        start_time = time.time()

        while True:
            if time.time() - start_time >= interval:
                self.database.connect()
                self.add_devices()
                ###### Analyzer Functions ######
                
                self.analyze_brute_force()
                
                self.analyze_log_in()
                
                ###### Analyzer Functions ######
                self.display_Events_and_calc_threat_level()
                start_time = time.time()
                self.database.disconnect()

    def analyze_brute_force(self):
        event_type = 'successfulLogin'
        threatName = "login"
        results = self.database.execute_query(f"SELECT * from hybrid_idps.innerLayer WHERE event_type = '{event_type}' ORDER BY timestamp DESC")
        results = self.extract_ips(results)
        for ip, all_events in results.items():
            for event in all_events:
                logName = f"{threatName}-{event['timestamp']}"
                # self.add_threat(ip, logName, all_events[:1])
                self.add_threat(ip, logName, threatName)
                count = 0

    def analyze_log_in(self):
        event_type = 'invalidCredentials'
        threatName = "bruteForce"
        
        results = self.database.execute_query(f"SELECT * from hybrid_idps.innerLayer WHERE event_type = '{event_type}' ORDER BY timestamp DESC")
        results = self.extract_ips(results)
        for ip, all_events in results.items():
            count = 0
            for event in all_events:
                count += 1
                if count > 10:
                    logName = f"{threatName}-{event['timestamp']}"
                    # self.add_threat(ip, logName, all_events[:1])
                    self.add_threat(ip, logName, threatName)
                    count = 0

    def display_Events_and_calc_threat_level(self):
        for ip, deviceData in self.devices.items():
            print("\n")
            print(f"IP: {ip}")
            logs = deviceData["logs"]
            threatLevel = 0
            for threatName, threadType in logs.items():
                print(f"        {threatName}")
                threatLevel += self.threatTable[threadType]
            if threatLevel > 1: threatLevel = 1
            self.set_threat_level(ip, threatLevel)
            color_code = "\033[92m"  # Green
            if threatLevel > 0.5:
                color_code = "\033[91m"  # Red
            elif 0 < threatLevel < 0.5:
                color_code = "\033[93m"  # Yellow
            reset_color = "\033[0m"
            print(f"    {color_code}[Threat Level]:   {threatLevel} {reset_color}")
            
    def extract_ips(self, results):
        ip_dict = {}
        for entry in results:
            ip = entry['ip_address']
            if ip not in ip_dict:
                ip_dict[ip] = []
            ip_dict[ip].append(entry)
        return ip_dict

    def add_devices(self):
        results = self.database.execute_query(f"SELECT DISTINCT ip_address from hybrid_idps.innerLayer")
        ip_addresses = [ip['ip_address'] for ip in results]
        for ip in ip_addresses:
            self.devices[ip] = {'threatLevel': 0, 'logs': {}}
                
    def add_threat(self, ip_address, logName,  log):
        if ip_address in self.devices:
            device = self.devices[ip_address]
            device['logs'][logName] = log
        else:
            print(f"Device with IP address {ip_address} does not exist.")
            
    def set_threat_level(self, ip_address, newThreatLevel):
        if ip_address in self.devices:
            device = self.devices[ip_address]['threatLevel'] = newThreatLevel
        else:
            print(f"Device with IP address {ip_address} does not exist.")

if __name__ == "__main__":
    x = InnerLayer()

        
            