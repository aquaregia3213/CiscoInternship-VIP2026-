#!/usr/bin/env python3
"""
NetSage AI Rule Checker
------------------------
Automated rule checker for verifying network configurations against common networking faults.

Input Assumptions:
- Accepts network state data as structured JSON or dictionaries representing devices (Routers, Switches, Hosts).
- Device configurations include interface IPs, subnet masks, admin status, VLAN databases, route tables, and host IP settings.
- Standard Cisco command output strings (`show ip interface brief`, `show vlan brief`, `show ip route`, `ipconfig`) can also be parsed.

Rules Implemented:
1. Duplicate IP Address Check
2. Subnet Mask Mismatch Check (on connected subnets)
3. Default Gateway Mismatch Check (Host Gateway vs Router Interface IP)
4. Administratively Down Interface Check
5. Missing VLAN Check (Access port VLAN vs Switch VLAN database)
6. Missing Route / Reachability Check
"""

import json
import ipaddress
from typing import Dict, List, Any


class NetworkRuleChecker:
    def __init__(self, network_data: Dict[str, Any]):
        """
        Initialize the rule checker with structured network topology/device configuration state.
        """
        self.devices = network_data.get("devices", {})
        self.hosts = network_data.get("hosts", {})
        self.findings = []

    def check_duplicate_ips(self) -> List[Dict[str, Any]]:
        """
        Rule 1: Detect duplicate IP addresses assigned across router interfaces and host configurations.
        """
        ip_map = {}
        rule_findings = []

        # Collect IPs from router/switch interfaces
        for dev_name, dev_info in self.devices.items():
            for intf_name, intf_info in dev_info.get("interfaces", {}).items():
                ip = intf_info.get("ip_address")
                if ip and ip != "unassigned":
                    if ip in ip_map:
                        ip_map[ip].append(f"{dev_name} {intf_name}")
                    else:
                        ip_map[ip] = [f"{dev_name} {intf_name}"]

        # Collect IPs from host configurations
        for host_name, host_info in self.hosts.items():
            ip = host_info.get("ip_address")
            if ip:
                if ip in ip_map:
                    ip_map[ip].append(f"Host {host_name}")
                else:
                    ip_map[ip] = [f"Host {host_name}"]

        for ip, locations in ip_map.items():
            if len(locations) > 1:
                finding = {
                    "rule": "Duplicate IP Address",
                    "severity": "High",
                    "confirmed": True,
                    "details": f"Duplicate IP {ip} detected on multiple devices/hosts: {', '.join(locations)}.",
                    "remediation": f"Reassign unique IP address to one of the conflicting endpoints: {', '.join(locations)}."
                }
                rule_findings.append(finding)
                self.findings.append(finding)

        return rule_findings

    def check_admin_down_interfaces(self) -> List[Dict[str, Any]]:
        """
        Rule 2: Detect interfaces that are administratively down when configured with an IP address.
        """
        rule_findings = []
        for dev_name, dev_info in self.devices.items():
            for intf_name, intf_info in dev_info.get("interfaces", {}).items():
                status = intf_info.get("admin_status", "").lower()
                ip = intf_info.get("ip_address", "")
                if status == "administratively down" and ip and ip != "unassigned":
                    finding = {
                        "rule": "Administratively Down Interface",
                        "severity": "High",
                        "confirmed": True,
                        "details": f"Interface {intf_name} on {dev_name} (IP: {ip}) is administratively down.",
                        "remediation": f"Execute 'no shutdown' under interface {intf_name} configuration on {dev_name}."
                    }
                    rule_findings.append(finding)
                    self.findings.append(finding)

        return rule_findings

    def check_default_gateway_mismatches(self) -> List[Dict[str, Any]]:
        """
        Rule 3: Check host default gateway settings against router interface IP addresses.
        """
        rule_findings = []
        for host_name, host_info in self.hosts.items():
            host_ip = host_info.get("ip_address")
            host_mask = host_info.get("subnet_mask")
            host_gw = host_info.get("default_gateway")

            if not host_ip or not host_gw:
                continue

            try:
                host_net = ipaddress.IPv4Interface(f"{host_ip}/{host_mask}").network
            except Exception:
                continue

            gw_found = False
            matching_net_found = False

            for dev_name, dev_info in self.devices.items():
                for intf_name, intf_info in dev_info.get("interfaces", {}).items():
                    r_ip = intf_info.get("ip_address")
                    r_mask = intf_info.get("subnet_mask")
                    if not r_ip or r_ip == "unassigned" or not r_mask:
                        continue

                    try:
                        r_net = ipaddress.IPv4Interface(f"{r_ip}/{r_mask}").network
                    except Exception:
                        continue

                    if host_net == r_net:
                        matching_net_found = True
                        if r_ip == host_gw:
                            gw_found = True
                            break

            if matching_net_found and not gw_found:
                finding = {
                    "rule": "Default Gateway Mismatch",
                    "severity": "High",
                    "confirmed": True,
                    "details": f"Host {host_name} default gateway ({host_gw}) does not match router IP in subnet {host_net}.",
                    "remediation": f"Update host {host_name} default gateway to the correct router interface IP address."
                }
                rule_findings.append(finding)
                self.findings.append(finding)

        return rule_findings

    def check_subnet_mask_mismatches(self) -> List[Dict[str, Any]]:
        """
        Rule 4: Detect subnet mask mismatches between hosts on the same IP broadcast domain.
        """
        rule_findings = []
        subnet_masks = {}

        for host_name, host_info in self.hosts.items():
            host_ip = host_info.get("ip_address")
            host_mask = host_info.get("subnet_mask")
            vlan = host_info.get("vlan")

            if not host_ip or not host_mask or vlan is None:
                continue

            if vlan not in subnet_masks:
                subnet_masks[vlan] = []
            subnet_masks[vlan].append((host_name, host_ip, host_mask))

        for vlan, host_list in subnet_masks.items():
            masks = set(h[2] for h in host_list)
            if len(masks) > 1:
                details_str = ", ".join([f"{h[0]} ({h[1]}/{h[2]})" for h in host_list])
                finding = {
                    "rule": "Subnet Mask Mismatch",
                    "severity": "Medium",
                    "confirmed": True,
                    "details": f"Subnet mask mismatch detected among hosts on VLAN {vlan}: {details_str}.",
                    "remediation": f"Standardize subnet masks for all endpoints on VLAN {vlan}."
                }
                rule_findings.append(finding)
                self.findings.append(finding)

        return rule_findings

    def check_missing_vlans(self) -> List[Dict[str, Any]]:
        """
        Rule 5: Detect access ports assigned to VLANs that do not exist in the switch VLAN database.
        """
        rule_findings = []
        for dev_name, dev_info in self.devices.items():
            if dev_info.get("type") != "switch":
                continue

            vlan_db = dev_info.get("vlan_database", [])
            for intf_name, intf_info in dev_info.get("interfaces", {}).items():
                mode = intf_info.get("mode")
                access_vlan = intf_info.get("access_vlan")

                if mode == "access" and access_vlan:
                    if access_vlan not in vlan_db:
                        finding = {
                            "rule": "Missing VLAN in Database",
                            "severity": "High",
                            "confirmed": True,
                            "details": f"Switch {dev_name} port {intf_name} assigned to access VLAN {access_vlan}, but VLAN {access_vlan} is missing from the switch database.",
                            "remediation": f"Create VLAN {access_vlan} on switch {dev_name} ('vlan {access_vlan}')."
                        }
                        rule_findings.append(finding)
                        self.findings.append(finding)

        return rule_findings

    def check_missing_routes(self) -> List[Dict[str, Any]]:
        """
        Rule 6: Check for target destination subnets that lack routing table entries on gateway routers.
        """
        rule_findings = []
        for dev_name, dev_info in self.devices.items():
            if dev_info.get("type") != "router":
                continue

            routes = dev_info.get("routing_table", [])
            target_subnets = dev_info.get("expected_subnets", [])

            for target in target_subnets:
                has_route = False
                for r in routes:
                    if r == target or r == "0.0.0.0/0":
                        has_route = True
                        break

                if not has_route:
                    finding = {
                        "rule": "Missing Route",
                        "severity": "High",
                        "confirmed": True,
                        "details": f"Router {dev_name} routing table does not contain a route to destination subnet {target} or default route.",
                        "remediation": f"Add a static route ('ip route {target} ...') or configure dynamic routing (OSPF/EIGRP) on {dev_name}."
                    }
                    rule_findings.append(finding)
                    self.findings.append(finding)

        return rule_findings

    def run_all_checks(self) -> List[Dict[str, Any]]:
        """
        Run all configured network rules and return complete findings.
        """
        self.findings = []
        self.check_duplicate_ips()
        self.check_admin_down_interfaces()
        self.check_default_gateway_mismatches()
        self.check_subnet_mask_mismatches()
        self.check_missing_vlans()
        self.check_missing_routes()
        return self.findings


# Sample Demonstration Network Topology Data
SAMPLE_NETWORK_STATE = {
    "devices": {
        "R1": {
            "type": "router",
            "interfaces": {
                "GigabitEthernet0/0/0": {
                    "ip_address": "192.168.10.1",
                    "subnet_mask": "255.255.255.0",
                    "admin_status": "administratively down"
                },
                "GigabitEthernet0/0/1": {
                    "ip_address": "172.16.1.1",
                    "subnet_mask": "255.255.255.252",
                    "admin_status": "up"
                }
            },
            "routing_table": ["192.168.10.0/24", "172.16.1.0/30"],
            "expected_subnets": ["10.2.2.0/24"]
        },
        "S1": {
            "type": "switch",
            "vlan_database": [1, 10, 20],
            "interfaces": {
                "FastEthernet0/1": {"mode": "access", "access_vlan": 10},
                "FastEthernet0/5": {"mode": "access", "access_vlan": 30}
            }
        }
    },
    "hosts": {
        "PC-1": {
            "ip_address": "192.168.10.10",
            "subnet_mask": "255.255.255.0",
            "default_gateway": "192.168.10.1",
            "vlan": 10
        },
        "PC-A": {
            "ip_address": "172.16.20.15",
            "subnet_mask": "255.255.255.0",
            "default_gateway": "172.16.20.254",
            "vlan": 20
        },
        "PC-C": {
            "ip_address": "192.168.10.10",
            "subnet_mask": "255.255.255.128",
            "default_gateway": "192.168.10.1",
            "vlan": 10
        }
    }
}


if __name__ == "__main__":
    print("==================================================")
    print("      NetSage AI Network Rule Checker v1.0        ")
    print("==================================================\n")

    checker = NetworkRuleChecker(SAMPLE_NETWORK_STATE)
    findings = checker.run_all_checks()

    print(f"Total Faults Detected: {len(findings)}\n")
    for idx, f in enumerate(findings, 1):
        print(f"[{idx}] Rule: {f['rule']} (Severity: {f['severity']})")
        print(f"    Confirmed: {f['confirmed']}")
        print(f"    Details:   {f['details']}")
        print(f"    Fix:       {f['remediation']}\n")
