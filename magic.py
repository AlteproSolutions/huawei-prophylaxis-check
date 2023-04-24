from ciscoconfparse import CiscoConfParse
from openpyxl import Workbook
import re
from scrapli import Scrapli

def check_config(parse):
    keywords = [
        "dhcp snooping enable",
        "info-center loghost 10.255.255.50 channel 4 local-time",
        "snmp-agent target-host trap address udp-domain 10.255.10.20",
        "local-user admin",
        "local-user admin service-type ssh",
        "ftp server enable",
    ]

    results = []
    for keyword in keywords:
        if parse.find_objects(keyword):
            results.append(True)
        else:
            results.append(False)
    return results

def extract_hostname(parse):
    hostname_obj = parse.find_objects(r"sysname (\S+)")

    hostname = hostname_obj[0].re_match(r"sysname (\S+)") if hostname_obj else ""

    return hostname

def get_stp_info(device):
    response = device.send_command("display stp active")
    output = response.result
    print(output)
    bpdu_protection = "BPDU-Protection     :Enabled" in output
    #stp_type = re.search(r"STP Type\s+:\s+(\S+)", output)

    return bpdu_protection, stp_type.group(1) if stp_type else ""

def check_no_bpdu_error_down(device):
    response = device.send_command("display error-down recovery")
    output = response.result
    print(output)
    return "Info: No error-down interface exists." in output

def check_ntp_status_ok(device):
    response = device.send_command("display ntp status | include clock status")
    output = response.result
    print(output)
    return "clock status: synchronized" in output

def check_http_status_disabled(device):
    response = device.send_command("display http server")
    output = response.result
    print(output)
    return "HTTP Server Status              : disabled" and "HTTP Secure-server Status       : disabled" in output



def create_excel(switch_data):
    wb = Workbook()
    ws = wb.active

    ws.append(["Hostname"] + [f"Command {i+1}" for i in range(6)] + ["BPDU Protection", "STP Type"])

    for data in switch_data:
        ws.append(data)

    wb.save("switch_config_results.xlsx")

def connect(device_info):
    device = Scrapli(**device_info)
    device.open()
    return device

if __name__ == "__main__":
    devices = []  # List of device connection information
    switch_data = []

    for device_info in devices:
        device = connect(device_info)
        config_text = device.send_command("display current-configuration").result
        parse = CiscoConfParse(config_text.splitlines())

        hostname = extract_hostname(parse)
        results = check_config(parse)
        bpdu_protection, stp_type = get_stp_info(device)

        switch_data.append([hostname] + results + [bpdu_protection, stp_type])

    create_excel(switch_data)