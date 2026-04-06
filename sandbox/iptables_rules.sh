#!/usr/bin/env bash
# Network restriction for the Sentinel sandbox container.
# Only allows outbound connections to api.fda.gov and DNS.
# Run as root before dropping to sandboxuser.

set -euo pipefail

ALLOWED_HOST="api.fda.gov"

# Flush existing rules
iptables -F OUTPUT 2>/dev/null || true

# Allow loopback
iptables -A OUTPUT -o lo -j ACCEPT

# Allow DNS (needed to resolve api.fda.gov)
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Resolve the IP(s) for the allowed host and permit them
for ip in $(getent ahosts "$ALLOWED_HOST" 2>/dev/null | awk '{print $1}' | sort -u); do
    iptables -A OUTPUT -d "$ip" -p tcp --dport 443 -j ACCEPT
    iptables -A OUTPUT -d "$ip" -p tcp --dport 80 -j ACCEPT
done

# Allow established/related connections
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Drop everything else
iptables -A OUTPUT -j DROP

echo "iptables rules applied: only $ALLOWED_HOST is reachable."
