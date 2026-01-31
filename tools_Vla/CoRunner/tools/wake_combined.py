#!/usr/bin/env python3
"""Send Wake-on-LAN packets both to LAN broadcast and to a remote router (internet).

Behavior:
- Reads `tools_Vla/Wake/wake_lan.sh` to find MAC address.
- Reads `tools_Vla/Wake/wake_inet.sh` to find inet IP, port and MAC.
- Sends one magic packet to local broadcast and one to the inet IP:port.
- Prints diagnostic output for logging.
"""
import re
import socket
from pathlib import Path

p = Path(__file__).resolve()
ROOT = None
for parent in p.parents:
    if (parent / '.git').exists() or (parent / '.python-version').exists():
        ROOT = parent
        break
if ROOT is None:
    # fallback to 3 levels up (tools_Vla/CoRunner/tools -> workspace root)
    ROOT = p.parents[3]

WAKE_LAN = ROOT / 'tools_Vla' / 'Wake' / 'wake_lan.sh'
WAKE_INET = ROOT / 'tools_Vla' / 'Wake' / 'wake_inet.sh'


def extract_mac(line: str):
    m = re.search(r"([0-9A-Fa-f]{2}(?::|-)){5}[0-9A-Fa-f]{2}", line)
    return m.group(0).upper() if m else None


def extract_inet(line: str):
    # find -i IP -p PORT MAC or IP:PORT or similar
    ip = None
    port = None
    mac = extract_mac(line)
    m_ip = re.search(r"-i\s+([0-9\.]+)", line)
    if m_ip:
        ip = m_ip.group(1)
    m_port = re.search(r"-p\s+(\d+)", line)
    if m_port:
        port = int(m_port.group(1))
    return ip, port, mac


def make_magic(mac: str) -> bytes:
    hw = mac.replace(":", "").replace("-", "")
    if len(hw) != 12:
        raise ValueError("Bad MAC length")
    data = bytes.fromhex("FF" * 6 + hw * 16)
    return data


def send_broadcast(mac: str, port: int = 9):
    data = make_magic(mac)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(data, ("255.255.255.255", port))
    s.close()


def send_udp(ip: str, port: int, mac: str):
    data = make_magic(mac)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(data, (ip, int(port)))
    s.close()


def main():
    print("Reading wake scripts...")
    lan_mac = None
    inet_ip = None
    inet_port = None
    inet_mac = None

    if WAKE_LAN.exists():
        line = WAKE_LAN.read_text().strip()
        lan_mac = extract_mac(line)
        print("Found LAN MAC:", lan_mac)

    if WAKE_INET.exists():
        line = WAKE_INET.read_text().strip()
        inet_ip, inet_port, inet_mac = extract_inet(line)
        print("Found INET:", inet_ip, inet_port, inet_mac)

    if not lan_mac and not inet_mac:
        print("No MAC addresses found in wake scripts; nothing to do.")
        return 2

    rc = 0
    if lan_mac:
        try:
            print(f"Sending LAN broadcast magic packet to {lan_mac}")
            send_broadcast(lan_mac)
        except Exception as e:
            print("LAN send failed:", e)
            rc = 1

    if inet_ip and inet_port and inet_mac:
        try:
            print(f"Sending INET magic packet to {inet_ip}:{inet_port} for {inet_mac}")
            send_udp(inet_ip, inet_port, inet_mac)
        except Exception as e:
            print("INET send failed:", e)
            rc = 1
    elif inet_ip and inet_port and not inet_mac and lan_mac:
        try:
            print(f"Sending INET magic packet to {inet_ip}:{inet_port} using LAN MAC {lan_mac}")
            send_udp(inet_ip, inet_port, lan_mac)
        except Exception as e:
            print("INET send failed:", e)
            rc = 1

    print("Done, return code:", rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
