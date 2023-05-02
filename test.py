import os
import concurrent.futures
from scrapli import Scrapli
from scrapli.driver.network import NetworkDriver
from scrapli.exceptions import ScrapliException

def backup_config(switch, username, password, output_dir):
    device = {
        "host": switch,
        "auth_username": username,
        "auth_password": password,
        "auth_strict_key": False,
        "platform": "huawei_vrp",
        "transport": "ssh2",
    }

    try:
        conn = Scrapli(**device)
        conn.open()
        response = conn.send_command("display current-configuration")
        output = response.result

        filename = f"{switch}_config_backup.txt"
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w") as f:
            f.write(output)

        print(f"Config saved for {switch}")

    except ScrapliException as e:
        print(f"Error connecting to {switch}: {str(e)}")

    finally:
        conn.close()

def backup_switches(switches, username, password, output_dir):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(backup_config, switch, username, password, output_dir) for switch in switches]
        concurrent.futures.wait(futures)

# Example usage
if __name__ == "__main__":
    switches = ["172.25.2.1", "172.25.2.6"]
    username = "admin"
    password = "UD6:8+MKUb46L{t7"
    output_dir = "configs"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    backup_switches(switches, username, password, output_dir)





    #LIVE CHECKS and CONFIG CHECKS
def perform_checks(device_connection, config):
    checks = {}

    # Check STP info
    response = device_connection.send_command("display stp active")
    output = response.result
    checks["get_stp_info"] = "BPDU-Protection     :Enabled" in output

    # Check no BPDU error-down
    response = device_connection.send_command("display error-down recovery")
    output = response.result
    checks["check_no_bpdu_error_down"] = "Info: No error-down interface exists." in output

    # Check NTP status
    response = device_connection.send_command("display ntp status | include clock status")
    output = response.result
    checks["check_ntp_status_ok"] = "clock status: synchronized" in output

    # Check HTTP status
    response = device_connection.send_command("display http server")
    output = response.result
    checks["check_http_status_disabled"] = "HTTP Server Status              : disabled" and "HTTP Secure-server Status       : disabled" in output



    # Configuration checks
    parsed_config = CiscoConfParse(config)
    for line in lines_to_check:
        if parsed_config.find_objects(line, exactmatch=True):
            checks[line] = True
        else:
            checks[line] = False

    return checks
