from netmiko.ssh_autodetect import SSHDetect



def autodetect_device(host, username, password):
    device = {
    'device_type': 'autodetect',
    'ip': host,
    'username': username,
    'password': password,
}
    
    guesser = SSHDetect(**device)
    best_match = guesser.autodetect()
    print(best_match) # Name of the best device_type to use further
    print(guesser.potential_matches) # Dictionary of the whole matching result



    host = {
            "host": host.strip(),
            "auth_username": username,
            "auth_password": password,
            "auth_strict_key": False,
            "platform": "huawei_vrp",
            "transport": "ssh2"
    }