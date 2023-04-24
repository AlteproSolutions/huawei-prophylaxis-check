from scrapli import Scrapli

device_info = {
   "host": "172.25.2.7",
   "auth_username": "admin",
   "auth_password": "UD6:8+MKUb46L{t7",
   "auth_strict_key": False,
   "platform": "huawei_vrp",
   "transport": "ssh2"
}
# List of device connection information
switch_data = []


def connect(device_info):
    device = Scrapli(**device_info)
    device.open()
    return device

device = connect(device_info)
response = device.send_command("display stp active")
output = response.result
print(output)
print("Info: No error-down interface exists." in output)