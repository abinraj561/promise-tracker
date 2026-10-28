"""
Promise Tracker - FastAPI Application & REST API
Provides real-time promise tracking, automated NLP extraction, daily morning briefings,
audit logging, team accountability, and WhatsApp message dispatching.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import io
import csv

from database import get_db_connection, init_db, seed_sample_data_if_empty
import nlp_extractor
import integrations
from integrations import WhatsAppManager, TeamsManager, get_integration_settings, update_integration_settings

app = FastAPI(
    title="Promise Tracker API",
    description="Operational customer promise and commitment tracking platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure DB is initialized
init_db()

# --- Pydantic Request Models ---

class PromiseCreate(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = "+91 98765 00000"
    channel: Optional[str] = "whatsapp"
    direction: Optional[str] = "business_to_customer"
    category: Optional[str] = "general"
    title: str
    deliverable: str
    due_date: str # "YYYY-MM-DD HH:MM"
    due_date_text: Optional[str] = None
    payment_amount: Optional[float] = 0.0
    currency: Optional[str] = "₹"
    responsible_person: str
    responsible_role: Optional[str] = "Logistics & Delivery"
    priority: Optional[str] = "medium"
    original_message: Optional[str] = None

class PromiseUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    title: Optional[str] = None
    deliverable: Optional[str] = None
    due_date: Optional[str] = None
    due_date_text: Optional[str] = None
    payment_amount: Optional[float] = None
    responsible_person: Optional[str] = None
    responsible_role: Optional[str] = None
    priority: Optional[str] = None

class PromiseFulfill(BaseModel):
    proof_note: str
    proof_attachment: Optional[str] = None

class PromiseRenegotiate(BaseModel):
    new_due_date: str
    new_due_date_text: Optional[str] = None
    reason: str

class ExtractionRequest(BaseModel):
    text: str
    customer_name: Optional[str] = None
    api_key: Optional[str] = None

class TeamMemberCreate(BaseModel):
    name: str
    role: str
    avatar_color: Optional[str] = "#10B981"
    phone: Optional[str] = None

# --- Helper Functions ---

def generate_promise_code() -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) as max_id FROM promises")
    row = cursor.fetchone()
    conn.close()
    next_id = (row["max_id"] or 1000) + 1
    return f"PRM-{next_id}"

def update_dynamic_statuses():
    """Recalculates status for non-completed promises based on current system time."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, due_date, status FROM promises WHERE status NOT IN ('completed', 'cancelled')")
    rows = cursor.fetchall()
    
    now = datetime.now()
    today_date = now.date()

    for r in rows:
        p_id = r["id"]
        due_str = r["due_date"]
        try:
            due_dt = datetime.strptime(due_str, "%Y-%m-%d %H:%M")
            if due_dt < now:
                new_status = "overdue"
            elif due_dt.date() == today_date:
                new_status = "due_today"
            else:
                new_status = "pending"
                
            if new_status != r["status"] and r["status"] != "renegotiated":
                cursor.execute("UPDATE promises SET status = ? WHERE id = ?", (new_status, p_id))
        except ValueError:
            pass

    conn.commit()
    conn.close()

# --- API Endpoints ---

@app.get("/api/dashboard/summary")
def get_dashboard_summary():
    update_dynamic_statuses()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Counts
    cursor.execute("SELECT status, COUNT(*) as count FROM promises GROUP BY status")
    status_counts = {r["status"]: r["count"] for r in cursor.fetchall()}
    
    overdue_count = status_counts.get("overdue", 0)
    due_today_count = status_counts.get("due_today", 0)
    pending_count = status_counts.get("pending", 0)
    completed_count = status_counts.get("completed", 0)
    renegotiated_count = status_counts.get("renegotiated", 0)
    total_active = overdue_count + due_today_count + pending_count + renegotiated_count
    
    # Customer commitments vs Business commitments
    cursor.execute("SELECT direction, COUNT(*) as count FROM promises WHERE status != 'completed' GROUP BY direction")
    direction_counts = {r["direction"]: r["count"] for r in cursor.fetchall()}

    # Reliability Trust Score Calculation
    cursor.execute("SELECT COUNT(*) as total_resolved FROM promises WHERE status = 'completed'")
    total_resolved = cursor.fetchone()["total_resolved"]
    
    cursor.execute("SELECT COUNT(*) as on_time FROM promises WHERE status = 'completed' AND (completed_at <= due_date OR renegotiated_count = 0)")
    on_time_count = cursor.fetchone()["on_time"]
    
    reliability_rate = round((on_time_count / max(1, total_resolved)) * 100, 1) if total_resolved > 0 else 98.4

    # Top Team Workload
    cursor.execute("""
    SELECT responsible_person, responsible_role, COUNT(*) as active_count,
           SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) as overdue_count
    FROM promises
    WHERE status != 'completed'
    GROUP BY responsible_person
    ORDER BY active_count DESC
    """)
    team_workload = [dict(r) for r in cursor.fetchall()]

    # Critical Alerts
    alerts = []
    if due_today_count > 0:
        alerts.append({
            "type": "warning",
            "icon": "⚠️",
            "text": f"{due_today_count} customer promise{'s are' if due_today_count > 1 else ' is'} due today"
        })
    if overdue_count > 0:
        alerts.append({
            "type": "danger",
            "icon": "🔴",
            "text": f"{overdue_count} promise{'s are' if overdue_count > 1 else ' is'} overdue"
        })
    if not alerts:
        alerts.append({
            "type": "success",
            "icon": "✅",
            "text": "All customer commitments are on schedule!"
        })

    conn.close()
    return {
        "overdue": overdue_count,
        "due_today": due_today_count,
        "pending": pending_count,
        "completed": completed_count,
        "renegotiated": renegotiated_count,
        "total_active": total_active,
        "customer_commitments": direction_counts.get("customer_to_business", 0),
        "business_commitments": direction_counts.get("business_to_customer", 0),
        "reliability_rate": reliability_rate,
        "team_workload": team_workload,
        "alerts": alerts
    }

@app.get("/api/promises")
def get_promises(
    status: str = Query("all"),
    direction: str = Query("all"),
    category: str = Query("all"),
    responsible: str = Query("all"),
    search: Optional[str] = None
):
    update_dynamic_statuses()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM promises WHERE 1=1"
    params = []
    
    if status != "all":
        if status == "active":
            query += " AND status IN ('due_today', 'overdue', 'pending', 'renegotiated')"
        else:
            query += " AND status = ?"
            params.append(status)
            
    if direction != "all":
        query += " AND direction = ?"
        params.append(direction)
        
    if category != "all":
        query += " AND category = ?"
        params.append(category)

    if responsible != "all":
        query += " AND responsible_person = ?"
        params.append(responsible)

    if search:
        query += " AND (customer_name LIKE ? OR title LIKE ? OR deliverable LIKE ? OR promise_code LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    # Sort: Overdue first, then Due Today, then Pending by due_date ascending
    query += """
    ORDER BY 
        CASE 
            WHEN status = 'overdue' THEN 1
            WHEN status = 'due_today' THEN 2
            WHEN status = 'pending' THEN 3
            WHEN status = 'renegotiated' THEN 4
            ELSE 5
        END,
        due_date ASC
    """
    
    cursor.execute(query, params)
    promises = [dict(r) for r in cursor.fetchall()]
    
    # Attach audit log count & recent log
    for p in promises:
        cursor.execute("SELECT action, actor, details, created_at FROM promise_audit_logs WHERE promise_id = ? ORDER BY id DESC", (p["id"],))
        p["audit_logs"] = [dict(log) for log in cursor.fetchall()]

    conn.close()
    return {"promises": promises, "total": len(promises)}

@app.get("/api/promises/{promise_id}")
def get_promise(promise_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promises WHERE id = ?", (promise_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Promise not found")
        
    promise = dict(row)
    cursor.execute("SELECT * FROM promise_audit_logs WHERE promise_id = ? ORDER BY id DESC", (promise_id,))
    promise["audit_logs"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return promise

@app.post("/api/promises/extract")
def extract_promises(req: ExtractionRequest):
    """Parses text and returns candidate promises without saving."""
    extracted = nlp_extractor.extract_promises_from_text(
        text=req.text,
        customer_override=req.customer_name,
        gemini_api_key=req.api_key
    )
    return {"candidates": extracted, "count": len(extracted)}

@app.post("/api/promises")
def create_promise(p: PromiseCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    code = generate_promise_code()
    
    # Check if due_date is today or overdue
    try:
        due_dt = datetime.strptime(p.due_date, "%Y-%m-%d %H:%M")
        if due_dt < datetime.now():
            status = "overdue"
        elif due_dt.date() == datetime.now().date():
            status = "due_today"
        else:
            status = "pending"
    except ValueError:
        status = "pending"

    cursor.execute("""
    INSERT INTO promises (
        promise_code, customer_name, customer_phone, channel, direction, category,
        title, deliverable, due_date, due_date_text, payment_amount, currency,
        responsible_person, responsible_role, status, priority, original_message,
        original_due_date, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        code, p.customer_name, p.customer_phone, p.channel, p.direction, p.category,
        p.title, p.deliverable, p.due_date, p.due_date_text or p.due_date,
        p.payment_amount or 0.0, p.currency or "₹", p.responsible_person,
        p.responsible_role, status, p.priority or "medium", p.original_message,
        p.due_date, now_str
    ))
    
    promise_id = cursor.lastrowid
    cursor.execute("""
    INSERT INTO promise_audit_logs (promise_id, action, actor, details, created_at)
    VALUES (?, 'Created', 'User / Auto-Extractor', 'Promise logged into active tracker', ?)
    """, (promise_id, now_str))

    conn.commit()
    conn.close()
    return {"id": promise_id, "promise_code": code, "status": status, "message": "Promise successfully created!"}

@app.post("/api/promises/batch-save")
def batch_save_promises(promises: List[PromiseCreate]):
    created_ids = []
    for p in promises:
        res = create_promise(p)
        created_ids.append(res)
    return {"saved": created_ids, "count": len(created_ids)}

@app.put("/api/promises/{promise_id}")
def update_promise(promise_id: int, u: PromiseUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promises WHERE id = ?", (promise_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Promise not found")
        
    updates = []
    params = []
    for field, val in u.dict(exclude_unset=True).items():
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(val)
            
    if updates:
        params.append(promise_id)
        cursor.execute(f"UPDATE promises SET {', '.join(updates)} WHERE id = ?", params)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("""
        INSERT INTO promise_audit_logs (promise_id, action, actor, details, created_at)
        VALUES (?, 'Updated', 'Operations Admin', 'Promise parameters updated', ?)
        """, (promise_id, now_str))
        conn.commit()

    conn.close()
    return {"message": "Promise updated successfully"}

@app.post("/api/promises/{promise_id}/fulfill")
def fulfill_promise(promise_id: int, f: PromiseFulfill):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promises WHERE id = ?", (promise_id,))
    p = cursor.fetchone()
    if not p:
        conn.close()
        raise HTTPException(status_code=404, detail="Promise not found")
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("""
    UPDATE promises 
    SET status = 'completed', proof_note = ?, proof_attachment = ?, completed_at = ?
    WHERE id = ?
    """, (f.proof_note, f.proof_attachment, now_str, promise_id))

    cursor.execute("""
    INSERT INTO promise_audit_logs (promise_id, action, actor, details, created_at)
    VALUES (?, 'Fulfilled', 'Operator / Responsible Rep', ?, ?)
    """, (promise_id, f"Delivered & Verified: {f.proof_note}", now_str))

    conn.commit()
    conn.close()
    return {"message": "Promise marked as fulfilled!", "status": "completed"}

@app.post("/api/promises/{promise_id}/renegotiate")
def renegotiate_promise(promise_id: int, r: PromiseRenegotiate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promises WHERE id = ?", (promise_id,))
    p = cursor.fetchone()
    if not p:
        conn.close()
        raise HTTPException(status_code=404, detail="Promise not found")
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    old_due = p["due_date"]
    new_count = (p["renegotiated_count"] or 0) + 1

    cursor.execute("""
    UPDATE promises 
    SET due_date = ?, due_date_text = ?, renegotiated_reason = ?, 
        renegotiated_count = ?, status = 'renegotiated'
    WHERE id = ?
    """, (r.new_due_date, r.new_due_date_text or r.new_due_date, r.reason, new_count, promise_id))

    cursor.execute("""
    INSERT INTO promise_audit_logs (promise_id, action, actor, details, created_at)
    VALUES (?, 'Renegotiated', 'Operations Team', ?, ?)
    """, (promise_id, f"Deadline shifted from {old_due} to {r.new_due_date}. Reason: {r.reason}", now_str))

    conn.commit()
    conn.close()
    return {"message": "Promise deadline renegotiated successfully", "status": "renegotiated"}

@app.delete("/api/promises/{promise_id}")
def delete_promise(promise_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM promises WHERE id = ?", (promise_id,))
    cursor.execute("DELETE FROM promise_audit_logs WHERE promise_id = ?", (promise_id,))
    conn.commit()
    conn.close()
    return {"message": "Promise removed"}

@app.get("/api/team")
def get_team():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT tm.*, 
           COUNT(p.id) as total_promises,
           SUM(CASE WHEN p.status = 'due_today' THEN 1 ELSE 0 END) as due_today_count,
           SUM(CASE WHEN p.status = 'overdue' THEN 1 ELSE 0 END) as overdue_count,
           SUM(CASE WHEN p.status = 'completed' THEN 1 ELSE 0 END) as completed_count
    FROM team_members tm
    LEFT JOIN promises p ON tm.name = p.responsible_person
    GROUP BY tm.id
    ORDER BY total_promises DESC
    """)
    team = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"team": team}

@app.post("/api/team")
def add_team_member(m: TeamMemberCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO team_members (name, role, avatar_color, phone) VALUES (?, ?, ?, ?)",
                       (m.name, m.role, m.avatar_color, m.phone))
        conn.commit()
        member_id = cursor.lastrowid
        conn.close()
        return {"id": member_id, "name": m.name, "role": m.role}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Team member already exists")

@app.get("/api/notifications/whatsapp-digest")
def get_whatsapp_digest():
    """Generates ready-to-copy WhatsApp messages for daily morning team brief & customer updates."""
    update_dynamic_statuses()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM promises WHERE status = 'due_today' ORDER BY due_date ASC")
    due_today = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM promises WHERE status = 'overdue' ORDER BY due_date ASC")
    overdue = [dict(r) for r in cursor.fetchall()]
    
    conn.close()

    # Generate Team Digest
    today_str = datetime.now().strftime("%A, %d %B %Y")
    team_msg = f"🌅 *PROMISE TRACKER - DAILY MORNING BRIEFING*\n📅 {today_str}\n"
    team_msg += "─────────────────────────\n"
    
    if overdue:
        team_msg += f"🔴 *CRITICAL: {len(overdue)} OVERDUE PROMISES*\n"
        for p in overdue:
            team_msg += f"• [{p['promise_code']}] *{p['customer_name']}*: {p['deliverable']} (Due: {p['due_date_text']}) ➡️ @{p['responsible_person']}\n"
        team_msg += "\n"
        
    if due_today:
        team_msg += f"⚠️ *DUE TODAY: {len(due_today)} CUSTOMER COMMITMENTS*\n"
        for p in due_today:
            team_msg += f"• [{p['promise_code']}] *{p['customer_name']}*: {p['deliverable']} ({p['due_date_text']}) ➡️ @{p['responsible_person']}\n"
        team_msg += "\n"
    else:
        team_msg += "✨ No promises due today. Great job team!\n\n"

    team_msg += "🎯 *Let's deliver 100% of our commitments today!*"

    # Generate Customer Message Nudges
    customer_nudges = []
    for p in due_today:
        msg = f"Hi {p['customer_name']}, this is a friendly update regarding your *{p['title']}*. Our team ({p['responsible_person']}) is on track for *{p['due_date_text']}*. Please let us know if you need any adjustments!"
        customer_nudges.append({
            "promise_code": p["promise_code"],
            "customer_name": p["customer_name"],
            "customer_phone": p["customer_phone"],
            "message": msg
        })

    return {
        "team_digest": team_msg,
        "customer_nudges": customer_nudges,
        "due_today_count": len(due_today),
        "overdue_count": len(overdue)
    }

@app.get("/api/export/csv")
def export_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promises ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        for r in rows:
            writer.writerow(dict(r))
            
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customer_promises.csv"}
    )

@app.post("/api/webhook/simulate")
def simulate_whatsapp_webhook(payload: Dict[str, Any]):
    """Simulates an incoming WhatsApp message payload from WhatsApp Cloud API or Twilio."""
    raw_message = payload.get("message", "")
    from_number = payload.get("from", "+91 98765 11223")
    sender_name = payload.get("sender_name", "Valued Customer")
    
    extracted = nlp_extractor.extract_promises_from_text(raw_message, customer_override=sender_name)
    saved = []
    for item in extracted:
        p = PromiseCreate(
            customer_name=item["customer_name"],
            customer_phone=from_number,
            channel="whatsapp",
            direction=item["direction"],
            category=item["category"],
            title=item["title"],
            deliverable=item["deliverable"],
            due_date=item["due_date"],
            due_date_text=item["due_date_text"],
            payment_amount=item["payment_amount"],
            currency=item["currency"],
            responsible_person=item["responsible_person"],
            responsible_role=item["responsible_role"],
            priority=item["priority"],
            original_message=raw_message
        )
        saved.append(create_promise(p))

# --- Integration Hub Endpoints (WhatsApp & Microsoft Teams) ---

@app.get("/api/integrations/config")
def get_integrations_config():
    return get_integration_settings()

@app.post("/api/integrations/config")
def save_integrations_config(payload: Dict[str, Any]):
    update_integration_settings(payload)
    return {"status": "success", "message": "Integration settings updated successfully"}

# Meta WhatsApp Business Cloud API Webhook Handshake (GET)
@app.get("/api/integrations/whatsapp/webhook")
def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    challenge = WhatsAppManager.verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return HTMLResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")

# Meta WhatsApp Business Cloud API Incoming Message Webhook (POST)
@app.post("/api/integrations/whatsapp/webhook")
def receive_whatsapp_webhook(payload: Dict[str, Any]):
    extracted_promises = WhatsAppManager.process_incoming_meta_webhook(payload)
    saved = []
    
    for item in extracted_promises:
        p = PromiseCreate(
            customer_name=item["customer_name"],
            customer_phone=item.get("customer_phone", "+91 98765 00000"),
            channel="whatsapp",
            direction=item["direction"],
            category=item["category"],
            title=item["title"],
            deliverable=item["deliverable"],
            due_date=item["due_date"],
            due_date_text=item["due_date_text"],
            payment_amount=item["payment_amount"],
            currency=item["currency"],
            responsible_person=item["responsible_person"],
            responsible_role=item["responsible_role"],
            priority=item["priority"],
            original_message=item.get("original_message", "")
        )
        saved.append(create_promise(p))

    # Send auto-acknowledgement back to customer if configured
    settings = get_integration_settings()
    if settings.get("whatsapp_auto_ack") and saved and extracted_promises:
        first = extracted_promises[0]
        ack_msg = f"✅ Hi {first['customer_name']}, your promise for *{first['title']}* has been logged. Deliverable: {first['deliverable']} (Due: {first['due_date_text']}). Assigned to our team member @{first['responsible_person']}."
        WhatsAppManager.send_message(first.get("customer_phone", ""), ack_msg)

    # Post to Microsoft Teams if enabled
    if settings.get("teams_enabled") and settings.get("teams_webhook_url") and saved:
        teams_card = TeamsManager.build_overdue_alert_card({
            "promise_code": saved[0]["promise_code"],
            "customer_name": extracted_promises[0]["customer_name"],
            "title": extracted_promises[0]["title"],
            "deliverable": extracted_promises[0]["deliverable"],
            "responsible_person": extracted_promises[0]["responsible_person"],
            "responsible_role": extracted_promises[0]["responsible_role"],
            "due_date_text": extracted_promises[0]["due_date_text"]
        })
        TeamsManager.send_to_channel(settings.get("teams_webhook_url"), teams_card)

    return {"status": "processed", "promises_extracted": len(saved), "saved_promises": saved}

# Outbound WhatsApp Test Sender
@app.post("/api/integrations/whatsapp/send-test")
def send_whatsapp_test(payload: Dict[str, Any]):
    phone = payload.get("phone", "+91 98451 22334")
    message = payload.get("message", "🔥 Hello from Promise Tracker! Your table delivery is confirmed for Friday evening.")
    result = WhatsAppManager.send_message(phone, message)
    return result

# Microsoft Teams Test Alert Sender
@app.post("/api/integrations/teams/send-test")
def send_teams_test_alert(payload: Dict[str, Any]):
    settings = get_integration_settings()
    webhook_url = payload.get("webhook_url") or settings.get("teams_webhook_url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Please provide a Microsoft Teams Incoming Webhook URL")

    # Sample test card
    test_promise = {
        "promise_code": "PRM-1041",
        "customer_name": "Shihab (Test Customer)",
        "title": "Solid Teak Dining Table Delivery",
        "deliverable": "6-Seater Teak Dining Table with protective packing & assembly",
        "responsible_person": "Sameer",
        "responsible_role": "Logistics & Delivery",
        "due_date_text": "Friday by 18:00 (Today)"
    }
    card = TeamsManager.build_overdue_alert_card(test_promise)
    res = TeamsManager.send_to_channel(webhook_url, card)
    return res

# Microsoft Teams Morning Briefing Dispatcher
@app.post("/api/integrations/teams/dispatch-digest")
def dispatch_teams_morning_digest():
    settings = get_integration_settings()
    webhook_url = settings.get("teams_webhook_url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Microsoft Teams Webhook URL is not configured")

    update_dynamic_statuses()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promises WHERE status = 'due_today' ORDER BY due_date ASC")
    due_today = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM promises WHERE status = 'overdue' ORDER BY due_date ASC")
    overdue = [dict(r) for r in cursor.fetchall()]
    conn.close()

    summary = get_dashboard_summary()
    card = TeamsManager.build_morning_briefing_card(summary, due_today, overdue)
    res = TeamsManager.send_to_channel(webhook_url, card)
    return {
        "status": "dispatched",
        "due_today_count": len(due_today),
        "overdue_count": len(overdue),
        "teams_response": res
    }

# Microsoft Teams Outgoing Webhook / Bot Command Endpoint
@app.post("/api/integrations/teams/bot")
def handle_teams_bot_command(payload: Dict[str, Any]):
    text = payload.get("text", "")
    response = TeamsManager.process_teams_bot_command(text)
    return response

# Serve static frontend files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Promise Tracker API is running. Building frontend UI...</h1>")
