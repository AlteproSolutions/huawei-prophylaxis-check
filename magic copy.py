import os
import sys
import asyncio
from dotenv import load_dotenv
from ciscoconfparse import CiscoConfParse
from openpyxl import Workbook
from scrapli import AsyncScrapli
from rich import inspect

def create_inventory(hosts, username, password):
    inventory = []

    for host in hosts:
        inventory.append({
            "host": host,
            "auth_username": username,
            "auth_password": password,
            "auth_strict_key": False,
            "platform": "huawei_vrp",
            "transport": "ssh2"
        })
    return inventory

def find_hostname(config):
    for line in config.splitlines():
        if line.startswith("sysname"):
            hostname = line.split()[1]
            return hostname
    return None

def check_config(confparse, lines_to_check):
    result = {}

    for line in lines_to_check:
        if confparse.find_objects(line, exactmatch=True):
            result[line] = True
        else:
            result[line] = False

    return result

def create_excel(switch_data):
    wb = Workbook()
    ws = wb.active

    ws.append(["Hostname"] + [f"Command {i+1}" for i in range(6)] + ["BPDU Protection", "STP Type"])

    for data in switch_data:
        ws.append(data)

    wb.save("switch_config_results.xlsx")

get_device_config_and_save(device_connection):
    # Create output folder
    if not os.path.exists(f'{absolute_path}/output'):
        os.mkdir(f'{absolute_path}/output')

    # Get config and hostname
    response = await device_connection.send_command("display current configuration")
    config = response.result
    hostname = find_hostname(config)

    # Save Config
    device_path = f"{absolute_path}/output/{hostname}_" + f'({ip})'
    with open(f'{device_path}/config.txt', mode="w") as device_config_file:
        device_config_file.write(config)

    return config

async def perform_checks(device_connection, lines_to_check, absolute_path):
    checks = {}

    # Check STP info
    response = await device_connection.send_command("display stp active")
    output = response.result
    checks["get_stp_info"] = "BPDU-Protection     :Enabled" in output

    # Check no BPDU error-down
    response = await device_connection.send_command("display error-down recovery")
    output = response.result
    checks["check_no_bpdu_error_down"] = "Info: No error-down interface exists." in output

    # Check NTP status
    response = await device_connection.send_command("display ntp status | include clock status")
    output = response.result
    checks["check_ntp_status_ok"] = "clock status: synchronized" in output

    # Check HTTP status
    response = await device_connection.send_command("display http server")
    output = response.result
    checks["check_http_status_disabled"] = "HTTP Server Status              : disabled" and "HTTP Secure-server Status       : disabled" in output

    # Configuration checks
    config = await get_device_config_and_save(device_connection, device_connection.host, absolute_path)
    parsed_config = CiscoConfParse(config.splitlines())

    for line in lines_to_check:
        if parsed_config.find_objects(line, exactmatch=True):
            checks[line] = True
        else:
            checks[line] = False

    return checks

async def process_device(device):
    async with AsyncScrapli(**device) as device_connection:
        hostname = find_hostname(await get_device_config_and_save(device_connection, device["host"]))
        ip = device["host"]
        checks = await perform_checks(device_connection, lines_to_check, absolute_path)

        results = [hostname, ip] + [checks[line] for line in lines_to_check] + list(checks.values())
        return results
    

async def main():
# Load Environment Variables
    absolute_path = os.path.dirname(os.path.realpath(__file__))
    load_dotenv(absolute_path + "/.env")
    username = os.environ.get("USER")
    password = os.environ.get("PASSWORD")

    if (username or password) is None:
        print('U need to create .env file in root directory of the script and add USER = "YOURUSER" and PASSWORD = "YOURPASSWORD"')
        sys.exit(1)

    # Read hosts
    with open(f'{absolute_path}/hosts.txt', mode="r") as hostsFile:
        hosts = hostsFile.readlines()

    # Read commands
    with open(f'{absolute_path}/commands.txt', mode="r") as f:
        commands = f.read().splitlines()

    # Read lines to check
    with open(f'{absolute_path}/lines_to_check.txt', mode="r") as f:
        lines_to_check = f.read().splitlines()

    print("Commands: ", commands)
    print("device_connections : ", list(map(lambda x:x.strip(),hosts)))

    inventory = create_inventory(hosts, username, password)
    results = await asyncio.gather(*(process_device(device) for device in inventory))

    inspect(results)

    for result in results:
        print(result)
    #create_excel(results)




if __name__ == "__main__":
    asyncio.run(main())