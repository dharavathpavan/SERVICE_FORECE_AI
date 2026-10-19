# ServiceForce.ai - Telephony, Asterisk & VoLTE Gateway Setup Guide

This guide details connecting real enterprise telephony to ServiceForce.ai, including Bring-Your-Own-SIM (BYO SIM) voice gateways and Asterisk PBX SIP media bridges.

---

## 1. Supported Hardware & Connectivity

### Certified GSM / VoLTE Hardware Gateways
Standard USB cellular modems and standard consumer smartphones **do not** expose low-latency, full-duplex digital PCM audio streams required for real-time AI speech conversation with barge-in interruption. For reliable BYO SIM connectivity, use certified enterprise voice gateways:
- **Yeastar TG Series (TG100 / TG200 / TG400):** 1 to 4 SIM VoLTE gateway exposing standard RFC 3261 SIP endpoints.
- **Dinstar UC2000-VE / VF Series:** GSM/VoLTE gateway with hardware echo cancellation and SIP signaling.
- **Grandstream Wave / HT801 ATA:** For connecting landline FXO/FXS analog trunks.

---

## 2. Asterisk PBX Configuration

### `pjsip.conf` Configuration
Place the following endpoint configuration in `/etc/asterisk/pjsip.conf`:

```ini
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060

; Registration to VoLTE Gateway or Cloud SIP Trunk
[serviceforce-trunk]
type=endpoint
context=from-serviceforce
disallow=all
allow=ulaw,alaw,opus
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes
aors=serviceforce-trunk

[serviceforce-trunk]
type=aor
contact=sip:192.168.1.100:5060
```

### `extensions.conf` (Dialplan & Media Bridge)
Place the routing dialplan in `/etc/asterisk/extensions.conf`:

```ini
[from-serviceforce]
exten => _+X.,1,NoOp(ServiceForce Inbound AI Call: ${CALLERID(num)})
same => n,Answer()
same => n,Set(CHANNEL(hangup_handler_push)=serviceforce-cleanup,s,1)
same => n,AudioSocket(serviceforce-call-${UNIQUEID},127.0.0.1:9099)
same => n,Hangup()

[serviceforce-cleanup]
exten => s,1,NoOp(Cleaning up ServiceForce call session)
same => n,Return()
```

---

## 3. Linking a Phone Number in ServiceForce.ai

There are two ways to get a working line. Pick one before you start; both are driven from the app.

| Path | What you need | What you get |
| --- | --- | --- |
| **Mock line** | Nothing | Every screen, the dial keypad and campaigns work end to end, but no audio leaves the machine and the "AI" replays a scripted conversation. Useful for testing the flow. |
| **Real line** | A certified GSM/VoLTE gateway on your network running the SIP bridge from Section 2 | Real inbound and outbound calls answered by the AI agent. |

### Step 1 - Register the gateway (real lines only)

*App:* **Telephony → Gateways → Add gateway**, then press **Verify** on the row.

*REST:*

```bash
# 1. Register it. It starts unverified - a record is not a connection.
curl -X POST http://localhost:8000/api/v1/gateways \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"identifier": "yeastar-tg200", "sip_endpoint": "sip:192.168.1.100:5060"}'

# 2. Probe it for real. This is what flips it to online.
curl -X POST http://localhost:8000/api/v1/gateways/$GATEWAY_ID/verify \
  -H "Authorization: Bearer $TOKEN"

# 3. See which SIMs are actually registered.
curl http://localhost:8000/api/v1/gateways/$GATEWAY_ID/lines \
  -H "Authorization: Bearer $TOKEN"
```

Skip this step entirely for a mock line.

### Step 2 - Add the number

*App:* **Telephony → Phone lines → Add line**. Set the friendly name, the number your gateway presents (for example `+919876543210`), the connection type (`GSM / VoLTE gateway`, `SIP trunk` or `Mock`), and attach the gateway you just registered.

*REST:*

```bash
curl -X POST http://localhost:8000/api/v1/phone-connections \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
        "friendly_name": "Support line",
        "phone_number": "+919876543210",
        "connection_type": "gsm_gateway",
        "gateway_id": "'"$GATEWAY_ID"'",
        "inbound_enabled": true,
        "outbound_enabled": true
      }'
```

The number is created **unverified**, and the platform never pretends otherwise.

### Step 3 - Verify the line

*App:* press **Verify line** on the row. You will get either a real pass or an honest failure with the gateway's message.

*REST:*

```bash
curl -X POST http://localhost:8000/api/v1/phone-connections/$CONNECTION_ID/verify \
  -H "Authorization: Bearer $TOKEN"
```

A successful probe returns `{"verified": true, "status": "healthy", ...}`. A failed one returns `{"verified": false, "status": "unverified", "message": "..."}` with HTTP 200, because a failed probe is a result, not a crash. Outbound dialling on an unverified line is refused by policy with the reason `line_not_verified`.

### Step 4 - Assign an agent

*App:* edit the line and pick an agent, or set the agent's binding from **Agents**.

*REST:*

```bash
curl -X PATCH http://localhost:8000/api/v1/phone-connections/$CONNECTION_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"assigned_agent_id": "'"$AGENT_ID"'"}'
```

The agent's greeting, system prompt, voice, language and enabled tools are what the voice session uses on the call - nothing is hardcoded.

### Step 5 - Make a call

**Manually:** **Calls → Place call**, type the destination on the keypad (long-press `0` for `+`), pick the line and agent, confirm, and press **Place call**. Press **Open call** to watch the live transcript as the agent talks.

```bash
curl -X POST http://localhost:8000/api/v1/calls/outbound \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"to_number": "+919812345678", "connection_id": "'"$CONNECTION_ID"'",
       "agent_id": "'"$AGENT_ID"'", "reason": "manual_test", "confirmed": true}'
```

**By campaign:** **Outbound → Campaigns → New campaign**, attach the line and agent, add contacts, then press **Dry run** to see exactly how many calls are ready and which numbers policy would refuse (with reasons). Press **Start** to activate and dial the first batch; press **Run dialer** for each further batch.

```bash
curl -X POST http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/dry-run -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/start   -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/sweep   -H "Authorization: Bearer $TOKEN"
```

Each pass dials at most `concurrency_limit` contacts and reports `{dialed, blocked, failed}`. Contacts the policy refuses are recorded as a failed call carrying the reason (for example `contact_suppressed`), so nothing is dropped silently.

### What will not work, and why

- **A consumer phone, a USB dongle or an emulator cannot be linked as a line.** They do not expose the full-duplex PCM audio and barge-in control the AI needs, so the platform will not pretend they do.
- **Adding a number does not make it usable.** Until a probe succeeds it stays unverified and outbound calls on it are refused.
- **With `VOICE_PROVIDER=mock` no speech leaves the machine.** Set a real provider and a real gateway for actual audio; the dashboard, transcript and control flow are identical either way.

---

## 4. Real-Call Acceptance Test Checklist

Before placing the voice agent in production service with real callers:
- [ ] **Two-Way Audio Test:** Dial the assigned business number from a mobile phone. Verify that the agent's greeting is audible within 1.5 seconds of answering.
- [ ] **Speech Barge-In / Interruption Test:** While the agent is reciting a paragraph, speak clearly: *"Excuse me, Jordan."* Verify that the agent immediately ceases speaking within 300ms and listens.
- [ ] **Live Tool Retrieval Test:** Ask: *"Can you check the status of my order ORD-8921?"* Verify that the agent queries the live CRM tool and reads the correct carrier tracking ETA.
- [ ] **Human Escalation Test:** State: *"I need to speak with a human supervisor right away."* Verify that the call is transferred to the designated supervisor extension without disconnection.
- [ ] **Clean Hangup Test:** Terminate the call from the mobile phone. Verify that the call session closes gracefully and the detailed transcript, duration, and summary appear in `/app/calls`.

### Outbound checks

- [ ] **Keypad dial:** Place an outbound call from **Calls → Place call** on a verified line. The destination rings and the agent speaks its configured greeting.
- [ ] **Unverified line is refused:** Try the same call on an unverified line. The attempt is refused with `line_not_verified` and is visible in the call list - it is never reported as connected.
- [ ] **Campaign dry run:** Build a campaign, suppress one of its numbers in **Compliance**, then run **Dry run**. The refused number is listed with the reason `contact_suppressed` and is not dialled.
- [ ] **Campaign dial pass:** Press **Start** (or **Run dialer**) and confirm the reported `dialled / refused / failed` counts match the calls that appear in `/app/calls`.
- [ ] **Transcript is real:** Open a completed call. The transcript lines are the actual turns stored during the call, and the agent's lines reflect the agent's prompt and greeting - not a fixed script.
