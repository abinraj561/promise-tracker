"""
Promise Tracker - Database Engine & Models
Stores and manages promises, customers, team members, and audit history in SQLite.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "promises.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Promises Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS promises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        promise_code TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone TEXT,
        channel TEXT DEFAULT 'whatsapp',
        direction TEXT DEFAULT 'business_to_customer', -- 'business_to_customer' or 'customer_to_business'
        category TEXT DEFAULT 'general',
        title TEXT NOT NULL,
        deliverable TEXT NOT NULL,
        due_date TEXT NOT NULL, -- ISO formatted string (YYYY-MM-DD HH:MM)
        due_date_text TEXT, -- e.g. "Friday evening", "Tomorrow 3 PM"
        payment_amount REAL DEFAULT 0.0,
        currency TEXT DEFAULT '₹',
        responsible_person TEXT NOT NULL,
        responsible_role TEXT,
        status TEXT DEFAULT 'pending', -- 'pending', 'due_today', 'overdue', 'completed', 'renegotiated', 'cancelled'
        priority TEXT DEFAULT 'medium', -- 'critical', 'high', 'medium', 'low'
        original_message TEXT,
        proof_note TEXT,
        proof_attachment TEXT,
        renegotiated_reason TEXT,
        renegotiated_count INTEGER DEFAULT 0,
        original_due_date TEXT,
        created_at TEXT NOT NULL,
        completed_at TEXT
    );
    """)
    
    # Audit Logs / Renegotiation History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS promise_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        promise_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        actor TEXT DEFAULT 'System',
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (promise_id) REFERENCES promises(id) ON DELETE CASCADE
    );
    """)

    # Team Members
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL,
        avatar_color TEXT DEFAULT '#10B981',
        phone TEXT
    );
    """)

    # Integrations Configuration (WhatsApp & Microsoft Teams)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS integrations_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def seed_sample_data_if_empty():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM promises")
    count = cursor.fetchone()["count"]
    
    if count == 0:
        now = datetime.now()
        today_evening = (now.replace(hour=18, minute=0, second=0, microsecond=0)).strftime("%Y-%m-%d %H:%M")
        today_afternoon = (now.replace(hour=14, minute=30, second=0, microsecond=0)).strftime("%Y-%m-%d %H:%M")
        yesterday_evening = (now - timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        tomorrow_evening = (now + timedelta(days=1)).replace(hour=19, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        in_3_days = (now + timedelta(days=3)).replace(hour=11, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        completed_date = (now - timedelta(days=2)).replace(hour=16, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")

        team = [
            ("Sameer", "Logistics & Delivery", "#10B981", "+91 98765 43210"),
            ("Rahul", "UI/UX Designer", "#6366F1", "+91 98765 43211"),
            ("Priya", "Finance & Accounts", "#F59E0B", "+91 98765 43212"),
            ("Arjun", "Senior Technician", "#EC4899", "+91 98765 43213"),
            ("Kavita", "Studio Manager", "#8B5CF6", "+91 98765 43214"),
            ("Vikram", "Site Engineer", "#3B82F6", "+91 98765 43215"),
        ]
        cursor.executemany("INSERT OR IGNORE INTO team_members (name, role, avatar_color, phone) VALUES (?, ?, ?, ?)", team)

        sample_promises = [
            (
                "PRM-1041",
                "Shihab",
                "+91 98451 22334",
                "whatsapp",
                "business_to_customer",
                "furniture",
                "Solid Teak Dining Table Delivery",
                "6-Seater Teak Dining Table with protective packing & assembly",
                today_evening,
                "Today evening by 6:00 PM",
                0.0,
                "₹",
                "Sameer",
                "Logistics & Delivery",
                "due_today",
                "high",
                "Shihab: Can you deliver the table by Friday?\nOwner: Yes, Friday evening definitely.",
                None,
                None,
                None,
                0,
                today_evening,
                (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
                None
            ),
            (
                "PRM-1042",
                "Rahul Verma",
                "+91 98112 33445",
                "whatsapp",
                "customer_to_business",
                "agency",
                "Advance Payment for App Redesign",
                "₹20,000 Bank Transfer / UPI confirmation",
                today_afternoon,
                "Today 2:30 PM",
                20000.0,
                "₹",
                "Priya",
                "Finance & Accounts",
                "due_today",
                "critical",
                "Rahul: Okay bro, I'll pay ₹20k tomorrow and you send the design by Monday.",
                None,
                None,
                None,
                0,
                today_afternoon,
                (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                None
            ),
            (
                "PRM-1043",
                "Rahul Verma",
                "+91 98112 33445",
                "whatsapp",
                "business_to_customer",
                "agency",
                "Figma Design Mockups v1 Submission",
                "Complete Figma workspace link with onboarding & home screens",
                in_3_days,
                "Monday morning 11:00 AM",
                0.0,
                "₹",
                "Rahul",
                "UI/UX Designer",
                "pending",
                "high",
                "Rahul: Okay bro, I'll pay ₹20k tomorrow and you send the design by Monday.\nAgency: Done bro, Figma links will be shared Monday.",
                None,
                None,
                None,
                0,
                in_3_days,
                (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                None
            ),
            (
                "PRM-1038",
                "Ananya Sharma",
                "+91 99234 55667",
                "whatsapp",
                "business_to_customer",
                "interior",
                "3D Living Room Virtual Render",
                "High-resolution 4K render with walnut finishes",
                yesterday_evening,
                "Yesterday 5:00 PM",
                0.0,
                "₹",
                "Rahul",
                "UI/UX Designer",
                "overdue",
                "critical",
                "Ananya: Need the 3D renders before our architect meeting on Thursday.\nDesigner: We'll share them Thursday 5 PM sharp.",
                None,
                None,
                None,
                0,
                yesterday_evening,
                (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
                None
            ),
            (
                "PRM-1035",
                "Deepak Nair",
                "+91 97456 77889",
                "whatsapp",
                "business_to_customer",
                "repair",
                "iPhone 15 Pro OLED & Battery Replacement",
                "Repaired device with 6-month warranty card",
                completed_date,
                "Two days ago 4:00 PM",
                4500.0,
                "₹",
                "Arjun",
                "Senior Technician",
                "completed",
                "medium",
                "Deepak: Is it possible to collect my phone before 5 PM Wednesday?\nArjun: Yes sir, ready by 4 PM.",
                "Delivered on time. Customer signed invoice #9812. Tested in front of client.",
                None,
                None,
                0,
                completed_date,
                (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),
                completed_date
            ),
            (
                "PRM-1044",
                "Dr. Meenakshi Sundaram",
                "+91 98800 11223",
                "call_memo",
                "business_to_customer",
                "clinic",
                "Comprehensive Blood Panel & Lipid Profile Report",
                "PDF report sent via WhatsApp & doctor consultation slot confirmed",
                tomorrow_evening,
                "Tomorrow 7:00 PM",
                0.0,
                "₹",
                "Kavita",
                "Studio Manager",
                "pending",
                "medium",
                "Phone note: Dr. Meenakshi requested report before her evening clinic.",
                None,
                None,
                None,
                0,
                tomorrow_evening,
                now.strftime("%Y-%m-%d %H:%M"),
                None
            )
        ]

        for p in sample_promises:
            cursor.execute("""
            INSERT INTO promises (
                promise_code, customer_name, customer_phone, channel, direction, category,
                title, deliverable, due_date, due_date_text, payment_amount, currency,
                responsible_person, responsible_role, status, priority, original_message,
                proof_note, proof_attachment, renegotiated_reason, renegotiated_count,
                original_due_date, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, p)
            promise_id = cursor.lastrowid
            cursor.execute("""
            INSERT INTO promise_audit_logs (promise_id, action, actor, details, created_at)
            VALUES (?, 'Created', 'System Seed', 'Promise automatically indexed from conversation', ?)
            """, (promise_id, p[22]))

        conn.commit()
    conn.close()

# Initialize DB on load
init_db()
seed_sample_data_if_empty()
