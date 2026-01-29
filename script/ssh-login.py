#!/usr/bin/env python3


import sys
import os
import pprint
import json
import time
import requests
import getopt

pp = pprint.PrettyPrinter(indent=4)
enable_traces = 0

customerid = ''
locationid = ''

domain = os.getenv("DOMAIN")
email = os.getenv("EMAIL")
passwd = os.getenv("PASSWD")

sshpassword = os.getenv("PASSWORD")
time_out = int(os.getenv("SSH_TIMEOUT", "3600"))

enable = 1


def print_logs(*args):
    if enable_traces == 1:
        print(args)


def gettoken():
    url = domain + '/api/Customers/login?include=user'
    payload = '{"email":"' + email + '","password":"' + passwd + '"}'
    headers = {'content-type': 'application/json'}
    # print(f"gettoken - payload {payload}")
    r = requests.post(url, data=payload, headers=headers, verify=True)
    r.raise_for_status()
    # pp.pprint(r.json())
    token = r.json()['id']
    print_logs("TOKEN = " + token)
    return token


def enable_ssh(token, state):
    epoch_time = int(time.time())

    (
        print(
            "Enabling ssh for the node "
            + nodeid
            + " on the domain - "
            + domain
            + " for next "
            + str(time_out)
            + " seconds"
        )
        if int(state)
        else print("Disabling ssh for the node" + nodeid + "on the domain - " + domain)
    )

    url = domain + '/api/Nodes/' + nodeid
    headers = {'Content-Type': 'application/json', 'Authorization': token}

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    cust_loc_id = r.json()
    customerid = cust_loc_id["customerId"]
    locationid = cust_loc_id["locationId"]

    payload_dict = {
        "kvConfigs": [
            {
                "module": "SSHM",
                "key": "sshAccessControl",
                "value": "true" if int(state) else "false",
            },
            {"module": "SSHM", "key": "sshEnableTime", "value": str(epoch_time)},
            {"module": "SSHM", "key": "sshAuthPasswd", "value": sshpassword},
            {"module": "SSHM", "key": "sshTotalSessTimeout", "value": str(time_out)},
        ]
    }
    # Mask password before logging payload_dict.
    payload_log = dict(payload_dict)
    payload_log['kvConfigs'] = []
    for item in payload_dict['kvConfigs']:
        masked_item = dict(item)
        if masked_item.get('key') == 'sshAuthPasswd':
            masked_item['value'] = '****'
        payload_log['kvConfigs'].append(masked_item)

    url = (
        domain
        + '/api/Customers/'
        + customerid
        + '/locations/'
        + locationid
        + '/nodes/'
        + nodeid
        + '/kvConfigs'
    )
    headers = {'Content-Type': 'application/json', 'Authorization': token}

    payload = json.dumps(payload_dict)
    r = requests.patch(url, data=payload, headers=headers, verify=True)
    r.raise_for_status()

    url = domain + '/api//Customers/' + customerid + '/nodes/' + nodeid
    headers = {'Content-Type': 'application/json', 'Authorization': token}
    print_logs("Node info ", url)

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    nod_info = r.json()
    # pp.pprint(nod_info)

    print("\nUse following ssh command to login:")
    try:
        wanip = nod_info["wanIp"]
        print(" ssh operator@" + wanip)
        # pp.pprint(r.json())

    except Exception as e:
        print("read error - wanIp:", e)

    try:
        lanip = nod_info["ip"]
        print(" ssh operator@" + lanip)
    except Exception as e:
        print("read error - lanip:", e)

    try:
        for name in nod_info["ipv6"]:
            splitstring = name.split("/", 1)
            print(" ssh operator@" + splitstring[0])
    except Exception as e:
        print(" read error - ipv6 addesses:", e)
    try:
        for name in nod_info["ipv6"]:
            splitstring = name.split("/", 1)
            print(" ssh operator@" + splitstring[0])
    except Exception as e:
        print(" read error - ipv6 addesses:", e)


def usage():
    print("Help - Script to perfrom ssh login:")
    print("Options:")
    print("-i <nodeid>")
    print("-e <1/0> - <1 - enable sh 0 - disable ssh>  <default enable>")
    print("-n <int/dev> <int for int NOC and dev for dev NOC> <default int>")

    print("Examples:")
    print("python3 ./sshlogin.py -i c8b422578f17 -n int -e 1")
    print("python3 ./sshlogin.py -i f4694238ddf7 -n dev -e 1")
    print("python3 ./sshlogin.py -i f4694238ddf7 -n int -e 0")
    print("\n")


if __name__ == "__main__":

    # Parse and interpret options.
    (opts, val) = getopt.getopt(
        sys.argv[1:], "i:n:e:h", ["nodeid=", "noc=", "enable=", "help"]
    )
    # print(opts,val)
    for opt, value in opts:
        if (opt == "-i") or (opt == "--nodeid"):
            nodeid = str(value)
        elif (opt == "-e") or (opt == "--enable"):
            enable = int(value)
        elif (opt == "-n") or (opt == "--noc"):
            if value == "dev":
                domain = 'https://piranha-dev3.tau.dev-charter.net'
        elif (opt == "-h") or (opt == "--help"):
            usage()
            exit()
        else:
            exit()

    token = gettoken()
    enable_ssh(token, enable)
