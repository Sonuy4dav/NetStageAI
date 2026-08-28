"""Deterministic checks for the Cisco cases in the read-only dataset."""

import re
from dataclasses import dataclass
from typing import Callable

from .models import RuleCheckResult, RuleFinding
from .security import validate_cli_output


Matcher = Callable[[str], bool]


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    message: str
    matcher: Matcher
    fix_steps: list[str]
    osi_layer: str
    confidence: float
    severity: str


def _contains(*phrases: str) -> Matcher:
    lowered = tuple(phrase.lower() for phrase in phrases)
    return lambda output: all(phrase in output.lower() for phrase in lowered)


def _interface_admin_down(output: str) -> bool:
    return re.search(
        r"^\S+ is administratively down,? line protocol is down$",
        output,
        re.IGNORECASE | re.MULTILINE,
    ) is not None


RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition("INTERFACE_ADMIN_DOWN", "The interface is administratively down.", _interface_admin_down, ["interface <affected-interface>", "no shutdown"], "Layer 3", 0.98, "HIGH"),
    RuleDefinition("DHCP_POOL_EXHAUSTED", "The DHCP pool has no available addresses.", _contains("leased 10", "zero available"), ["ip dhcp excluded-address <unused-range>", "ip dhcp pool <pool-name>", "network <network> <mask>"], "Layer 7", 0.95, "HIGH"),
    RuleDefinition("DNS_LOOKUP_DISABLED", "DNS lookup is disabled or the configured name server is inactive.", _contains("no ip domain-lookup", "ip name-server"), ["ip domain lookup", "ip name-server <dns-server>"], "Layer 7", 0.94, "MEDIUM"),
    RuleDefinition("OSPF_HELLO_MISMATCH", "OSPF neighbors use different hello intervals.", _contains("ip ospf hello-interval 10", "ip ospf hello-interval 20"), ["interface <ospf-interface>", "ip ospf hello-interval <matching-value>"], "Layer 3", 0.97, "HIGH"),
    RuleDefinition("ACL_BLOCKS_HTTP", "An extended ACL denies HTTP traffic.", _contains("deny tcp", "eq 80"), ["permit tcp <source> <destination> eq 80", "apply the corrected ACL"], "Layer 4", 0.93, "MEDIUM"),
    RuleDefinition("NAT_OVERLOAD_MISSING", "NAT overload is missing from the translation rule.", _contains("ip nat inside source list", "missing overload"), ["ip nat inside source list <access-list> interface <outside-interface> overload"], "Layer 3", 0.96, "HIGH"),
    RuleDefinition("GUEST_ACL_TOO_PERMISSIVE", "The guest ACL permits unrestricted traffic.", _contains("guest_acl", "permit ip", "any"), ["deny ip 192.168.50.0 0.0.0.255 <internal-networks>", "permit only approved guest services"], "Layer 3/4", 0.90, "HIGH"),
    RuleDefinition("VLAN_MISSING_FROM_TRUNK", "The required VLAN is missing from the trunk allowed list.", _contains("trunk allowed vlan", "vlan 20 missing"), ["switchport trunk allowed vlan add 20"], "Layer 2", 0.96, "MEDIUM"),
    RuleDefinition("DEFAULT_GATEWAY_MISMATCH", "The host default gateway does not match the expected gateway.", _contains("default gateway 192.168.1.254"), ["configure the host default gateway as 192.168.1.1"], "Layer 3", 0.94, "HIGH"),
    RuleDefinition("MANAGEMENT_SVI_SHUTDOWN", "The management SVI is shut down.", _contains("interface vlan1", "shutdown"), ["interface Vlan1", "no shutdown"], "Layer 2", 0.97, "LOW"),
    RuleDefinition("INTERSWITCH_LINK_ACCESS_MODE", "The inter-switch link is configured as an access port instead of a trunk.", _contains("switchport mode access", "sw1 fa0/24", "sw2 fa0/24"), ["interface FastEthernet0/24", "switchport mode trunk"], "Layer 2", 0.96, "HIGH"),
    RuleDefinition("OSPF_PASSIVE_ACTIVE_LINK", "An active OSPF link is configured as passive.", _contains("passive-interface serial0/1/0", "router ospf"), ["router ospf 1", "no passive-interface Serial0/1/0"], "Layer 3", 0.95, "HIGH"),
    RuleDefinition("ACCESS_VLAN_MISMATCH", "The switch access port is assigned to the wrong VLAN.", _contains("switchport access vlan 14"), ["interface FastEthernet0/10", "switchport access vlan 40"], "Layer 2", 0.96, "MEDIUM"),
    RuleDefinition("DHCP_RELAY_MISSING", "The DHCP relay interface has no IP helper address.", _contains("missing ip helper-address", "interface gigabitethernet0/0"), ["interface GigabitEthernet0/0", "ip helper-address <dhcp-server>"], "Layer 7", 0.96, "HIGH"),
    RuleDefinition("STATIC_ROUTE_BAD_NEXT_HOP", "The static route uses an unreachable next-hop address.", _contains("next-hop ip 10.0.0.5 unreachable", "ip route"), ["replace the route with a reachable next-hop address"], "Layer 3", 0.94, "HIGH"),
    RuleDefinition("FTP_CONTROL_PORT_MISSING", "The ACL does not permit FTP control port 21.", _contains("eq 20", "missing port 21"), ["permit tcp <source> <server> eq 21"], "Layer 4", 0.95, "MEDIUM"),
    RuleDefinition("NAT_INSIDE_DIRECTION_MISSING", "The internal interface is missing the NAT inside direction.", _contains("ip nat inside source static", "missing ip nat inside"), ["interface <inside-interface>", "ip nat inside"], "Layer 3", 0.96, "HIGH"),
    RuleDefinition("RADIUS_SECRET_MISMATCH", "The RADIUS shared secret does not match.", _contains("radius-server host", "incorrect_secret_key"), ["configure the matching RADIUS shared secret on the client and server"], "Layer 7", 0.93, "HIGH"),
    RuleDefinition("NATIVE_VLAN_MISMATCH", "Trunk peers use different native VLANs.", _contains("native vlan 10", "native vlan 99"), ["configure the same native VLAN on both trunk ports"], "Layer 2", 0.97, "LOW"),
    RuleDefinition("DEFAULT_GATEWAY_OUTSIDE_SUBNET", "The default gateway is outside the host subnet.", _contains("outside subnet boundary", "10.1.1.50"), ["configure a gateway within the 10.1.1.0/28 subnet"], "Layer 3", 0.96, "HIGH"),
    RuleDefinition("OSPF_REDISTRIBUTION_SUBNETS_MISSING", "OSPF redistribution is missing the subnets keyword.", _contains("redistribute eigrp 100", "missing subnets"), ["router ospf 1", "redistribute eigrp 100 subnets"], "Layer 3", 0.95, "MEDIUM"),
    RuleDefinition("ACL_BLOCKS_HTTPS", "The outbound ACL does not permit HTTPS traffic.", _contains("permit tcp any any eq 80", "missing port 443"), ["permit tcp any any eq 443"], "Layer 4", 0.95, "MEDIUM"),
    RuleDefinition("DUPLICATE_IP_ADDRESS", "A duplicate IP address was detected.", _contains("duplicate address", "%ip-4-dup_addr"), ["assign a unique IP address to the conflicting host"], "Layer 3", 0.99, "HIGH"),
    RuleDefinition("VTP_DOMAIN_MISMATCH", "VTP peers use different domain names.", _contains("vtp domain corp", "case sensitive mismatch"), ["configure the same VTP domain on both switches"], "Layer 2", 0.96, "MEDIUM"),
    RuleDefinition("DAI_UPLINK_NOT_TRUSTED", "The uplink is not configured as trusted for Dynamic ARP Inspection.", _contains("ip arp inspection trust missing", "uplink"), ["interface GigabitEthernet0/1", "ip arp inspection trust"], "Layer 2", 0.95, "HIGH"),
    RuleDefinition("PORT_SECURITY_VIOLATION", "Port security detected a security violation.", _contains("psecure_violation", "security violation"), ["interface FastEthernet0/10", "shutdown", "no shutdown"], "Layer 2", 0.98, "MEDIUM"),
    RuleDefinition("HSRP_TIMER_MISMATCH", "HSRP peers use different hello timers.", _contains("standby 1 priority 110 hello 3", "standby 1 priority 100 hello 10"), ["configure the same HSRP hello timer on both peers"], "Layer 3", 0.96, "MEDIUM"),
    RuleDefinition("SUBINTERFACE_ENCAPSULATION_MISSING", "The router sub-interface is missing 802.1Q encapsulation.", _contains("missing encapsulation dot1q 20", "interface gigabitethernet0/0.20"), ["interface GigabitEthernet0/0.20", "encapsulation dot1Q 20"], "Layer 2/3", 0.97, "HIGH"),
    RuleDefinition("IPV6_RA_SUPPRESSED", "IPv6 Router Advertisements are suppressed.", _contains("ipv6 nd suppress-ra"), ["interface GigabitEthernet0/0", "no ipv6 nd suppress-ra"], "Layer 3", 0.97, "MEDIUM"),
    RuleDefinition("CDP_DISABLED", "CDP is disabled globally.", _contains("no cdp run"), ["cdp run"], "Layer 2", 0.98, "LOW"),
)


def evaluate_show_output(show_output: str) -> RuleCheckResult:
    """Evaluate output and return status plus all matching findings."""
    if not isinstance(show_output, str) or not show_output.strip():
        return RuleCheckResult("NO_KNOWN_ERROR")
    validate_cli_output(show_output)

    findings = []
    for rule in RULES:
        if not rule.matcher(show_output):
            continue
        fix_steps = rule.fix_steps
        if rule.rule_id == "INTERFACE_ADMIN_DOWN":
            match = re.search(r"^(\S+) is administratively down", show_output, re.IGNORECASE | re.MULTILINE)
            if match:
                fix_steps = [f"interface {match.group(1)}", "no shutdown"]
        findings.append(
            RuleFinding(
                rule_id=rule.rule_id,
                message=rule.message,
                evidence=[show_output.strip()],
                fix_steps=fix_steps,
                osi_layer=rule.osi_layer,
                confidence=rule.confidence,
                severity=rule.severity,
            )
        )
    return RuleCheckResult("ERRORS_DETECTED" if findings else "NO_KNOWN_ERROR", findings)


def check_show_output(show_output: str) -> list[RuleFinding]:
    """Backward-compatible helper returning only matching findings."""
    return evaluate_show_output(show_output).findings
