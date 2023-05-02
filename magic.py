from ciscoconfparse import CiscoConfParse
from openpyxl import Workbook
from scrapli import Scrapli
from rich import inspect
from rich import print as rprint
import os
import sys
import re
from dotenv import load_dotenv
from scrapli import AsyncScrapli
from scrapli.exceptions import ScrapliException
import concurrent.futures
import pandas as pd

def create_inventory(hosts, username, password):

    inventory = []

    for host in hosts:
        inventory.append({
            "host": host.strip(),
            "auth_username": username,
            "auth_password": password,
            "auth_strict_key": False,
            "platform": "huawei_vrp",
            "transport": "ssh2"
        })
    return inventory

def perform_live_checks(device_connection):
    live_checks = {}

    # Check STP info
    response = device_connection.send_command("display stp active")
    output = response.result
    live_checks["get_stp_info"] = "BPDU-Protection     :Enabled" in output

    # Check no BPDU error-down
    response = device_connection.send_command("display error-down recovery")
    output = response.result
    live_checks["check_no_bpdu_error_down"] = "Info: No error-down interface exists." in output

    # Check NTP status
    response = device_connection.send_command("display ntp status | include clock status")
    output = response.result
    live_checks["check_ntp_status_synchronized"] = "clock status: synchronized" in output

    # Check HTTP status
    response = device_connection.send_command("display http server")
    output = response.result
    live_checks["check_http_status_disabled"] = "HTTP Server Status              : disabled" and "HTTP Secure-server Status       : disabled" in output

    return live_checks


def connect(device):
    device_connection = Scrapli(**device).open()
    return device_connection


def get_hostname(config):
    for line in config.splitlines():
        if line.startswith("sysname"):
            hostname = line.split()[1]
            return hostname
    return None

def check_config(config, global_lines_to_check):

    result = {}
    confparse = CiscoConfParse(config.splitlines())
    for line in global_lines_to_check:
        if confparse.find_objects(line, exactmatch=True):
            result[line] = True
        else:
            result[line] = False

    return result


def check_interfaces_config(config, interfaces_lines_to_check):

    result = {}
    confparse = CiscoConfParse(config.splitlines())
    for line in global_lines_to_check:
        if confparse.find_objects(line, exactmatch=True):
            result[line] = True
        else:
            result[line] = False

    return result

def save_to_excel(data, output_file):
    # Create a new workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Outputs"

    # Set column headers
    headers = ['Zařízení', 'IP adresa']
    for device in data:
        for ip, info in device.items():
            for check_name in info['check_results']:
                if check_name not in headers:
                    headers.append(check_name)

    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num).value = header


    # Add data to the worksheet
    for row_num, device in enumerate(data, 2):
        for ip, info in device.items():
            ws.cell(row=row_num, column=1).value = info['hostname']
            ws.cell(row=row_num, column=2).value = ip
            for col_num, header in enumerate(headers[2:], 3):
                ws.cell(row=row_num, column=col_num).value = info['check_results'].get(header, None)

    # Uložení sešitu do souboru
    wb.save(output_file)


def connect_to_device(device):
    try:
        conn = Scrapli(**device)
        conn.open()
        return conn
    except Exception as e:
        pass

def get_config(connected_device):
    try:
        return connected_device.send_command("display current-configuration").result

    except Exception as e:
        pass    


def process_device(device, global_lines_to_check, commands_to_get_output):

    # Get config and info about device
    conn = connect_to_device(device)

    try: 
        device_config = get_config(conn)

        with open(f'{device_path}/config.txt', mode="w") as device_config_file:
            device_config_file.write(device_config)

        print(f"Config saved for {device}")

    except Exception as e:print(f"Failed when getting config from {device}")

    hostname = get_hostname(device_config)
    ip = device.get("host")
    device_path = f"{absolute_path}/output/{hostname}_" + f'({ip})'

    if not os.path.exists(device_path):
        os.mkdir(device_path)

    for command in commands_to_get_output:
        try:
            response = conn.send_command(command)

            with open(f'{device_path}/{command.strip().replace(" ", "_")}-{hostname}_({ip}).txt', mode="w") as commandfile:
                commandfile.write(response.result)

        except:
            print("Device " + hostname + f' ({ip}) - failed when getting ' + command)
            continue




    live_checks = perform_live_checks(conn)
    config_checks = check_config(device_config, global_lines_to_check)

    checks_results = {}
    checks_results.update(live_checks)
    checks_results.update(config_checks)


    device_data = {
        ip: {
            'hostname': hostname,
            'config': device_config,
            'check_results': checks_results,
        }
    }

    return device_data




if __name__ == "__main__":

    # Load Environment Variables
    absolute_path = os.path.dirname(os.path.realpath(__file__))
    load_dotenv(absolute_path + "/.env")
    username = os.environ.get("USER")
    password = os.environ.get("PASSWORD")
    
    if (username or password) is None:
        print('U need to create .env file in root directory of the script and add USER = "YOURUSER" and PASSWORD = "YOURPASSWORD"')
        sys.exit(1)

    #Create output folder
    if not os.path.exists(f'{absolute_path}/output'): os.mkdir(f'{absolute_path}/output')

    # Read hosts
    with open(f'{absolute_path}/config/hosts.txt', mode="r") as hostsFile:
        hosts = hostsFile.readlines()

    # Read commands
    with open(f'{absolute_path}/config/commands.txt', mode="r") as f:
        commands_to_get_ouput = f.read().splitlines()

    # Read lines to check
    with open(f'{absolute_path}/config/global_lines_to_check.txt', mode="r") as f:
        global_lines_to_check = f.read().splitlines()

    print("Commands: ", commands_to_get_ouput)
    print("device_connections : ", list(map(lambda x:x.strip(),hosts)))

    inventory = create_inventory(hosts, username, password)

    devices_data = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_device, device, global_lines_to_check, commands_to_get_ouput) for device in inventory]
        concurrent.futures.wait(futures)

        for future in concurrent.futures.as_completed(futures):
            devices_data.append(future.result())
            
    rprint(devices_data)
    inspect(devices_data)

    save_to_excel(devices_data, absolute_path + "/output/commands_check.xlsx")


    for object in devices_data:
        rprint(object)
        inspect(object)
