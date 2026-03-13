# PfChat investigation patterns

Use these patterns to turn raw pfSense API results into useful security answers.

## Broad health check

When the user asks for a general assessment:

1. Run `snapshot`.
2. Check `errors` first so you know which parts are missing.
3. Review devices for unknown or unnamed hosts.
4. Review logs for repeated blocked attempts from a single source.
5. Review connections for repeated destinations, unusual ports, or unexpected outbound traffic.
6. Review gateways/interfaces for packet loss, latency, or obvious errors.
7. Summarize in three blocks:
   - Findings
   - Evidence
   - Recommended next steps

## Unknown device triage

When a device looks unfamiliar:

- Extract IP, MAC, hostname, interface, and lease details.
- Compare hostname/MAC vendor clues if available.
- Check whether the device has active states.
- Say clearly whether it is unknown because of missing metadata or because behavior is actually unusual.

## Suspicious traffic triage

Look for:

- many blocked hits from one source IP
- one internal host talking to many external destinations quickly
- traffic to unusual external ports
- repeated hits to admin services from outside
- connections that do not match the user’s expected devices or apps

Do not overclaim malware or compromise from port numbers alone. Phrase it as suspicion, anomaly, or worth checking unless the evidence is strong.

## Rule review

When evaluating firewall rules:

- quote the relevant rule fields
- note interface, action, source, destination, protocol, and ports
- call out broad any/any exposure explicitly
- separate intended access from accidental over-permissiveness

## Reporting style

Prefer this structure:

- **Summary**
- **Notable findings**
- **Evidence**
- **Recommended actions**

Keep raw JSON out of the main answer unless the user asks for it.
