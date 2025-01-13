import datetime
import socket
import subprocess
import sys
import threading
import time

import requests
from flask import Flask

app = Flask(__name__)

TELEGRAM_ALERT_BASE_URL = ""
chat_id = ""

check_commands_url = []

metrics_output_cached = ['Updating ... Try again after a few seconds']


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def init():
    writeln("Init ...\n")

    global TELEGRAM_ALERT_BASE_URL, chat_id

    # if len(sys.argv) > 1:
    #     need_restart_node = int(sys.argv[1]) == 1

    cmd_url = "unknown"
    if len(sys.argv) > 1:
        TELEGRAM_ALERT_BASE_URL = "https://api.telegram.org/" + sys.argv[1] + "/sendMessage"
    if len(sys.argv) > 2:
        chat_id = sys.argv[2]
    if len(sys.argv) > 3:
        cmd_url = sys.argv[3]
        check_commands_url.append(cmd_url)

    println(f'sys_params: {sys.argv[0]} TELEGRAM_ALERT_BASE_URL: {TELEGRAM_ALERT_BASE_URL} chat_id: {chat_id} cmd_url: {cmd_url}')

    run_updater_background()

def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()  # Проверка на ошибки HTTP
    return response.text

def parse_data(raw_data):
    lines = raw_data.strip().split("\n")
    return [line.split(";") for line in lines]


def check_node(command, ip_addr):
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    writeln("check_node: " + command)
    return result.returncode == 0


def writeln(msg):
    sys.stdout.write(msg + "\n")


def println(msg):
    sys.stdout.write(str(datetime.datetime.now()) + ": " + msg + "\n")


def metrics_cache_update():
    metrics_output = []
    hostname = socket.gethostname()
    IPAddr = socket.gethostbyname(hostname)
    whoami = hostname + "/" + IPAddr
    ip_addr = get_ip_address()
    ipinf = whoami + " " + ip_addr
    metrics_output.append(f'{ipinf}')
    now = datetime.datetime.now()
    metrics_output.append(f'{now}')
    la = get_la()
    metrics_output.append(f'{la}')

    for commandUrl in check_commands_url:
        println(f'command_url: {commandUrl}')
        raw_data = fetch_data(commandUrl)
        nodes_data = parse_data(raw_data)
        for node_name, command in nodes_data:
            println(f'node_name: {node_name} command:{command}')
            if node_name.startswith("#"): continue
            status = check_node(command, ip_addr)
            status_metric = "active" if status else "INACTIVE"
            metrics_output.append(f'{node_name}: {status_metric}')

    global metrics_output_cached
    metrics_output_cached = metrics_output


def run_updater():
    while True:
        job_updater()
        time.sleep(60 * 59)


def run_updater_background():
    writeln("Run background tasks ...\n")
    updater_thread = threading.Thread(target=run_updater)
    updater_thread.start()
    notifier_thread = threading.Thread(target=run_notifier)
    notifier_thread.start()


def job_updater():
    metrics_cache_update()


def run_notifier():
    while True:
        job_notifier()
        time.sleep(10)


def get_sys_info():
    return get_ip_address()


def job_notifier():
    writeln("Send telegram notifications ...\n")
    metrics_job = [get_sys_info()]
    index = 0
    batch_size = 75
    for metric_el in metrics_output_cached:
        # if "INACTIVE" in metric_el and not "[DEPRECATED]" in metric_el and not "BlockMesh" in metric_el:
        if 1 or "INACTIVE" in metric_el:
            metrics_job.append(metric_el)
        index += 1
        if index % batch_size == 0:
            requests.get(url=TELEGRAM_ALERT_BASE_URL, params={'chat_id': chat_id, 'text': "\n".join(metrics_job)})
            metrics_job = []

    if index > 0 and len(metrics_job) > 0 and not len(metrics_job) % batch_size == 0:
        requests.get(url=TELEGRAM_ALERT_BASE_URL, params={'chat_id': chat_id, 'text': "\n".join(metrics_job)})

    send_la()


def send_la():
    result_as_text = get_la()
    writeln(result_as_text)
    requests.get(url=TELEGRAM_ALERT_BASE_URL, params={'chat_id': chat_id, 'text': result_as_text})


def get_la():
    sys_v = subprocess.run("lsb_release -a", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys_inf = short_sys_info(sys_v.stdout.decode("utf-8"))
    ip_addr = get_sys_info()
    sys_top_origin = (subprocess.run("top -bn 1 | head -6", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    sys_top = short_top(sys_top_origin.stdout.decode("utf-8"))
    result_as_text = ip_addr + "\n" + sys_inf + "\n" + sys_top
    # writeln(result_as_text)
    return result_as_text


def rm_empty_el(arr_str):
    res_arr_str = []
    for el in arr_str:
        if not el == "":
            res_arr_str.append(el)
    return res_arr_str


def short_top(top):
    tops = top.split("\n")
    la = tops[0].replace("load average:", "la")[tops[0].index("load average"):].replace(",", "")
    cpus = rm_empty_el(tops[2].replace(",", " ").replace(" :", ":").replace("  ", " ").split(" "))
    cpu = ("cpu " +
           str(int(float(cpus[1]))) + cpus[2] + " " +
           str(int(float(cpus[3]))) + cpus[4] + " " +
           str(int(float(cpus[5]))) + cpus[6] + " " +
           str(int(float(cpus[7]))) + cpus[8])

    mem_arr = rm_empty_el(tops[3].replace(",", " ").replace(" :", "").replace("  ", " ").split(" "))
    mem = (mem_arr[1] + " " +
           str(int(float(mem_arr[2]) / 1000)) + "t " +
           str(int(float(mem_arr[4]) / 1000)) + "f " +
           str(int(float(mem_arr[6]) / 1000)) + "u " +
           str(int(float(mem_arr[8]) / 1000)) + "bc")
    return la + "\n" + cpu + "\n" + mem


def short_sys_info(sys_info):
    si = sys_info.split("\n")[1]
    return si[si.index("Ubuntu"):]


def test():
    writeln("Test mode: ")
    si = short_sys_info("Distributor ID: Ubuntu\nDescription: Ubuntu 22.04.5 LTS\nRelease: 22.04\nCodename: jammy")
    writeln(si)
    top_info = "top - 00:03:11 up 39 days, 13:55,  7 users,  load average: 5.29, 4.23, 3.84\nTasks: 3669 total,   2 running, 352 sleeping,   0 stopped, 3315 zombie\n%Cpu(s): 23.6 us,  6.8 sy,  0.0 ni, 54.0 id,  0.0 wa,  0.0 hi,  1.3 si, 14.3 st\nMiB Mem :  24028.4 total,   8793.8 free,  13857.2 used,   3299.5 buff/cache\nMiB Swap:      0.0 total,      0.0 free,      0.0 used.  10171.2 avail Mem"
    # writeln(top_info)
    writeln(short_top(top_info))


if __name__ == "__main__":
    # test()
    init()
