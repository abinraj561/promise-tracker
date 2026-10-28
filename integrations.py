"""
Promise Tracker - External Integrations Module
Handles bidirectional integration with:
1. Meta WhatsApp Business Cloud API & Twilio (Inbound Webhooks & Outbound Messaging)
2. Microsoft Teams (Incoming Webhooks with Adaptive Cards & Outgoing Bot Commands)
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, List

from database import get_db_connection
import nlp_extractor

# --- Integration Configuration Storage ---

def get_integration_settings() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM integrations_config")
    rows = cursor.fetchall()
    conn.close()
    
    config = {r["key"]: r["value"] for r in rows}
    return {
        # WhatsApp Cloud API
        "whatsapp_enabled": config.get("whatsapp_enabled", "true") == "true",
        "whatsapp_phone_number_id": config.get("whatsapp_phone_number_id", ""),
        "whatsapp_access_token": config.get("whatsapp_access_token", ""),
        "whatsapp_verify_token": config.get("whatsapp_verify_token", "promise_tracker_secret_token_2026"),
        "whatsapp_business_account_id": config.get("whatsapp_business_account_id", ""),
        "whatsapp_auto_ack": config.get("whatsapp_auto_ack", "true") == "true",
        
        # Microsoft Teams
        "teams_enabled": config.get("teams_enabled", "true") == "true",
        "teams_webhook_url": config.get("teams_webhook_url", ""),
        "teams_auto_morning_digest": config.get("teams_auto_morning_digest", "true") == "true",
        "teams_auto_overdue_alert": config.get("teams_auto_overdue_alert", "true") == "true",
        "teams_channel_name": config.get("teams_channel_name", "General / Operations"),
    }

def update_integration_settings(settings: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    for key, val in settings.items():
        val_str = "true" if val is True else ("false" if val is False else str(val))
        cursor.execute("""
        INSERT INTO integrations_config (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, val_str))
    conn.commit()
    conn.close()

# --- 1. WhatsApp Cloud API Engine ---

class WhatsAppManager:
    @staticmethod
    def verify_webhook(mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Optional[str]:
        settings = get_integration_settings()
        expected_token = settings.get("whatsapp_verify_token", "promise_tracker_secret_token_2026")
        if mode == "subscribe" and token == expected_token:
            return challenge
        return None

    @staticmethod
    def process_incoming_meta_webhook(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses Meta WhatsApp Business Cloud API webhook payload:
        entry[].changes[].value.messages[]
        """
        extracted_promises = []
        try:
            entries = payload.get("entry", [])
            for entry in entries:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    contacts = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts", [])}
                    messages = value.get("messages", [])
                    
                    for msg in messages:
                        if msg.get("type") == "text":
                            from_number = msg.get("from")
                            sender_name = contacts.get(from_number) or f"Customer ({from_number[-4:]})"
                            text_body = msg.get("text", {}).get("body", "")
                            
                            # Extract promises using our AI engine
                            promises = nlp_extractor.extract_promises_from_text(text_body, customer_override=sender_name)
                            for p in promises:
                                p["customer_phone"] = from_number
                                p["channel"] = "whatsapp"
                                extracted_promises.append(p)
                                
        except Exception as e:
            print(f"Error parsing Meta WhatsApp webhook: {e}")

        return extracted_promises

    @staticmethod
    def send_message(to_number: str, message_text: str) -> Dict[str, Any]:
        """
        Sends an outbound WhatsApp message via Meta Cloud API or simulates if no token.
        """
        settings = get_integration_settings()
        phone_number_id = settings.get("whatsapp_phone_number_id")
        access_token = settings.get("whatsapp_access_token")

        clean_number = "".join(filter(str.isdigit, to_number))
        
        # If credentials provided, call official Meta Graph API
        if phone_number_id and access_token and len(clean_number) >= 10:
            url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            body = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": clean_number,
                "type": "text",
                "text": {"preview_url": False, "body": message_text}
            }
            try:
                req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    return {"status": "sent", "mode": "meta_cloud_api", "response": res_data}
            except Exception as e:
                return {"status": "error", "mode": "meta_cloud_api", "error": str(e)}

        # Simulated response if testing locally
        return {
            "status": "simulated_success",
            "mode": "local_simulator",
            "recipient": clean_number or to_number,
            "message": message_text,
            "timestamp": datetime.now().isoformat()
        }

# --- 2. Microsoft Teams Adaptive Card Engine ---

class TeamsManager:
    @staticmethod
    def send_to_channel(webhook_url: str, card_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends an Adaptive Card payload to Microsoft Teams Incoming Webhook / Power Automate.
        """
        if not webhook_url:
            return {"status": "skipped", "message": "No Teams Webhook URL configured"}

        headers = {"Content-Type": "application/json"}
        try:
            req = urllib.request.Request(webhook_url, data=json.dumps(card_payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                res_code = response.getcode()
                return {"status": "success", "http_code": res_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def build_morning_briefing_card(summary: Dict[str, Any], due_today_promises: List[Dict[str, Any]], overdue_promises: List[Dict[str, Any]], app_url: str = "http://127.0.0.1:8844") -> Dict[str, Any]:
        """
        Builds a Microsoft Teams Adaptive Card (v1.4) for the 8:00 AM Daily Morning Briefing.
        """
        today_str = datetime.now().strftime("%A, %d %B %Y")
        overdue_count = len(overdue_promises)
        due_today_count = len(due_today_promises)

        card_body = [
            {
                "type": "Container",
                "style": "emphasis",
                "items": [
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "width": "auto",
                                "items": [{"type": "TextBlock", "text": "🔥", "size": "ExtraLarge"}]
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {"type": "TextBlock", "text": "Promise Tracker — Daily Morning Dispatch", "weight": "Bolder", "size": "Large"},
                                    {"type": "TextBlock", "text": f"📅 {today_str} • Reliability Score: {summary.get('reliability_rate', 98.4)}%", "isSubtle": True, "spacing": "None"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "🔴 Overdue Commitments:", "value": f"{overdue_count} critical item{'s' if overdue_count != 1 else ''}"},
                    {"title": "⚠️ Due Today:", "value": f"{due_today_count} customer promise{'s' if due_today_count != 1 else ''}"},
                    {"title": "⏳ Active Pipeline:", "value": f"{summary.get('total_active', 0)} promises"}
                ]
            }
        ]

        # Overdue Section
        if overdue_promises:
            card_body.append({
                "type": "TextBlock",
                "text": "🔴 **CRITICAL OVERDUE COMMITMENTS**",
                "weight": "Bolder",
                "color": "Attention",
                "spacing": "Medium"
            })
            for p in overdue_promises[:5]:
                card_body.append({
                    "type": "Container",
                    "style": "warning",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"**[{p['promise_code']}] {p['customer_name']}** — {p['title']}",
                            "weight": "Bolder"
                        },
                        {
                            "type": "TextBlock",
                            "text": f"📦 Deliverable: {p['deliverable']}\n👤 Responsible: **@{p['responsible_person']}** ({p['responsible_role']})\n⏰ Was due: {p['due_date_text']}",
                            "wrap": True,
                            "isSubtle": True,
                            "spacing": "None"
                        }
                    ]
                })

        # Due Today Section
        if due_today_promises:
            card_body.append({
                "type": "TextBlock",
                "text": "⚠️ **DUE TODAY — TEAM FOCUS**",
                "weight": "Bolder",
                "color": "Warning",
                "spacing": "Medium"
            })
            for p in due_today_promises[:6]:
                card_body.append({
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"**[{p['promise_code']}] {p['customer_name']}** • {p['title']}",
                            "weight": "Bolder"
                        },
                        {
                            "type": "TextBlock",
                            "text": f"📦 {p['deliverable']}\n🎯 Assigned: **@{p['responsible_person']}** • ⏰ {p['due_date_text']}",
                            "wrap": True,
                            "isSubtle": True,
                            "spacing": "None"
                        }
                    ]
                })
        else:
            card_body.append({
                "type": "TextBlock",
                "text": "✨ *No promises due today. All commitments up to date!*",
                "color": "Good"
            })

        card_body.append({
            "type": "TextBlock",
            "text": "💡 *“What did we tell customers we would do?” — Deliver 100% on time today.*",
            "isSubtle": True,
            "spacing": "Medium"
        })

        adaptive_card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": card_body,
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "🚀 Open Promise Board",
                                "url": app_url
                            }
                        ]
                    }
                }
            ]
        }
        return adaptive_card

    @staticmethod
    def build_overdue_alert_card(promise: Dict[str, Any], app_url: str = "http://127.0.0.1:8844") -> Dict[str, Any]:
        """
        Builds a high-priority Microsoft Teams alert when a customer promise is breached.
        """
        adaptive_card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "Container",
                                "style": "attention",
                                "items": [
                                    {"type": "TextBlock", "text": "🚨 CRITICAL: CUSTOMER PROMISE OVERDUE", "weight": "Bolder", "color": "Attention", "size": "Large"},
                                    {"type": "TextBlock", "text": f"Promise [{promise.get('promise_code')}] for **{promise.get('customer_name')}** has passed its deadline without verified fulfillment.", "wrap": True}
                                ]
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Customer:", "value": promise.get("customer_name", "N/A")},
                                    {"title": "Promise:", "value": promise.get("title", "N/A")},
                                    {"title": "Deliverable:", "value": promise.get("deliverable", "N/A")},
                                    {"title": "Responsible:", "value": f"@{promise.get('responsible_person', 'N/A')} ({promise.get('responsible_role', '')})"},
                                    {"title": "Promised Due Date:", "value": promise.get("due_date_text", "N/A")}
                                ]
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "⚡ View & Resolve on Board",
                                "url": app_url
                            }
                        ]
                    }
                }
            ]
        }
        return adaptive_card

    @staticmethod
    def process_teams_bot_command(command_text: str) -> Dict[str, Any]:
        """
        Handles incoming Microsoft Teams bot / outgoing webhook commands.
        e.g. '@PromiseTracker due', '@PromiseTracker extract <chat text>'
        """
        text_clean = command_text.strip()
        # Strip mention if present e.g. <at>PromiseTracker</at>
        text_clean = re_mention = text_clean.replace("<at>PromiseTracker</at>", "").strip()

        if "due" in text_clean.lower() or "status" in text_clean.lower():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM promises WHERE status IN ('due_today', 'overdue') ORDER BY due_date ASC")
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            
            lines = [f"**Found {len(rows)} urgent promises:**\n"]
            for r in rows:
                status_icon = "🔴" if r["status"] == "overdue" else "⚠️"
                lines.append(f"{status_icon} **[{r['promise_code']}] {r['customer_name']}** — {r['deliverable']} (Due: {r['due_date_text']} | Assigned: @{r['responsible_person']})")
            
            return {"type": "message", "text": "\n\n".join(lines)}

        elif "extract" in text_clean.lower() or "promise" in text_clean.lower():
            extracted = nlp_extractor.extract_promises_from_text(text_clean)
            if not extracted:
                return {"type": "message", "text": "🤖 Could not detect any commitments in that text. Try including customer name and due dates (e.g. 'Shihab requested table delivery by Friday')."}
            
            lines = [f"✨ **AI Extracted {len(extracted)} Promise(s):**\n"]
            for i, p in enumerate(extracted, 1):
                lines.append(f"{i}. **Customer:** {p['customer_name']}\n• **Deliverable:** {p['deliverable']}\n• **Due Date:** {p['due_date_text']}\n• **Assigned To:** @{p['responsible_person']} ({p['responsible_role']})")
            
            return {"type": "message", "text": "\n\n".join(lines)}

        return {
            "type": "message",
            "text": "👋 **Promise Tracker Bot Commands:**\n\n• `@PromiseTracker due` — View overdue and due today promises\n• `@PromiseTracker extract <text>` — Auto-extract customer commitments from chat snippet\n• `@PromiseTracker summary` — View overall reliability trust score"
        }
