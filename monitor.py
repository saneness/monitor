#!/usr/local/bin/python3

# -*- coding: utf-8 -*-

import time
import os
import json
import psutil
import requests
import subprocess
import sys

from config import *

def pre(text):
    return '`' + text + '`'

def send_message(text):
    data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": 'markdown'})
    cmd = f"curl -X POST 'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage' -H 'Content-Type: application/json' -d '{data}'"
    os.system(cmd)
    time.sleep(1)

def check_service(service):
    status = STATUS[str(subprocess.call(['systemctl', 'is-active', '--quiet', service]))]
    return status in STATUS_WARNING, status

def check_service_remote(service, host):
    status = STATUS[str(subprocess.call(['ssh', host, 'systemctl', 'is-active', '--quiet', service]))]
    return status in STATUS_WARNING, status

def check_docker(name):
    containers = json.loads(subprocess.check_output(['docker', 'ps', '--no-trunc', '--format', '{"name":"{{.Names}}", "status":"{{.Status}}"}']).decode("utf-8"))
    if isinstance(containers, dict):
        containers = [containers]
    for container in containers:
        if container['name'] == name and 'Up' in container['status']:
            return False, 'running'
    return True, 'stopped'

def check_temp():
    value = int(subprocess.check_output(['cat', '/sys/class/thermal/thermal_zone0/temp'])) / 1000.0
    return value > MAX_TEMP, f'{value:.1f}°C'

def check_memory():
    memory = psutil.virtual_memory()
    memory_used = memory.used / 1024 / 1024
    memory_total = memory.total / 1024 / 1024
    value = 100.0 * memory_used / memory_total
    return value > MAX_MEMORY, f'{value:.2f}% ({memory_used:.1f}MB of {memory_total:.1f}MB)'

def check_disk():
    disk = psutil.disk_usage('/')
    disk_used = disk.used / 1024 / 1024 / 1024
    disk_total = disk.total / 1024 / 1024 / 1024
    value = 100.0 * disk_used / disk_total
    return value > MAX_DISK, f'{value:.2f}% ({disk_used:.1f}GB of {disk_total:.1f}GB)'

def check_nginx():
    return check_service('nginx')

def check_tgsanebot():
    return check_service('tgsanebot')

def check_openvpn_uk():
    return check_service('openvpn')

def check_openvpn_nl():
    return check_service_remote(service='openvpn', host='vpnie')

def check_quakejs():
    return check_docker('quakejs')

def check_openai():
    result = subprocess.check_output(['/usr/local/bin/balance_check']).decode('utf8').strip()
    return result == 'unknown', result

def check_nadezhdin():
    result = subprocess.check_output(['/usr/local/bin/nadezhdin']).decode('utf8').strip()
    return result.isdigit(), result

def check_monzo_pot():
    result = subprocess.check_output(['cat', '/tmp/monzo_pots']).decode('utf8').strip()
    return False, result

monitoring = {
    check_temp:       f'temperature:',
    check_memory:     f'memory usage:',
    check_disk:       f'disk usage:',
    check_nginx:      f'nginx status:',
    check_tgsanebot:  f'tgsanebot status:',
    check_openvpn_uk: f'openvpn (uk) status:',
    check_quakejs:    f'quakejs status:',
#   check_nadezhdin:  f'nadezhdin status:',
#   check_openai:     f'openai status:',
    check_monzo_pot:  f'monzo pot:'
}

try:
    if len(sys.argv) == 2 and sys.argv[1] in ('-c', '-t', '-h'):
        for check in monitoring:
            warning, value = check()
            if len(sys.argv) > 1:
                match sys.argv[1]:
                    case '-c':
                        print(' '.join(['[WARNING]' if warning else '[OK]', monitoring[check], f'{value}']))
                    case '-t':
                        if warning:
                            if not os.path.exists(f"/tmp/.monitoring_{check.__name__}"):
                                send_message(pre(' '.join(['[WARNING]', monitoring[check], f'{value}'])))
                                open(f"/tmp/.monitoring_{check.__name__}", "w+").close()
                        else:
                            if os.path.exists(f"/tmp/.monitoring_{check.__name__}"):
                                send_message(pre(' '.join(['[OK]', monitoring[check], f'{value}'])))
                                os.remove(f"/tmp/.monitoring_{check.__name__}")
                    case '-h':
                        for word in LINKS:
                            if word in monitoring[check]:
                                monitoring[check] = monitoring[check].replace(word, LINKS[word])
                        if warning:
                            print('<span>' + '<font color="#FF0000">[WARNING]</font> ' + monitoring[check] + f' {value}' + '<span><br>')
                        else:
                            print('<span>' + '<font color="#32CD32">[OK]</font> ' + monitoring[check] + f' {value}' + '<span><br>')
                    case _:
                        print(f'Unknown option(s) \'{" ".join(sys.argv[1:])}\'')
    else:
        print('Please use -c for console, -t for telegram, -h for html. Can\'t use multiple options at once.')
except TypeError:
    send_message(pre(' '.join(['[ERROR] monitoring issue'])))
