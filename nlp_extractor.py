"""
Promise Tracker - AI & Smart Heuristic Promise Extractor
Handles single messages, multi-turn WhatsApp dialogues, audio transcripts, and split commitments.
"""

import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

WEEKDAYS = {
    'monday': 0, 'mon': 0,
    'tuesday': 1, 'tue': 1,
    'wednesday': 2, 'wed': 2,
    'thursday': 3, 'thu': 3,
    'friday': 4, 'fri': 4,
    'saturday': 5, 'sat': 5,
    'sunday': 6, 'sun': 6
}

DEPARTMENT_MAP = [
    (re.compile(r'(pay|payment|advance|transfer|upi|invoic|amount|₹|rs\.?|\$|bill|deposit|fee|cash|cheque)', re.I), "Priya", "Finance & Accounts", "payment"),
    (re.compile(r'(deliver|table|sofa|chair|furniture|ship|dispatch|courier|transport|send by truck|cargo)', re.I), "Sameer", "Logistics & Delivery", "delivery"),
    (re.compile(r'(design|figma|render|3d|mockup|ui|ux|wireframe|logo|banner|creative|layout|prototype)', re.I), "Rahul", "UI/UX Designer", "design"),
    (re.compile(r'(repair|screen|battery|fix|service|inspect|hardware|mobile|iphone|laptop|engine|gadget|display)', re.I), "Arjun", "Senior Technician", "repair"),
    (re.compile(r'(photo|album|shoot|wedding|teaser|video|print|frames|gallery|edit|reels|camera)', re.I), "Kavita", "Studio Manager", "photography"),
    (re.compile(r'(tile|plumb|civil|renovat|wall|paint|site|construct|measurement|carpenter|flooring)', re.I), "Vikram", "Site Engineer", "renovation"),
    (re.compile(r'(clinic|doctor|blood|report|lab|test|lipid|scan|prescription|medic|patient|consultation)', re.I), "Kavita", "Clinic Coordinator", "healthcare"),
]

def parse_relative_time(text: str, base_time: Optional[datetime] = None) -> tuple[datetime, str, str]:
    """
    Parses relative time expressions into a specific ISO datetime and clean human text.
    Returns: (target_datetime, human_friendly_text, urgency_level)
    """
    if not base_time:
        base_time = datetime.now()
    
    text_lower = text.lower()
    target_dt = base_time + timedelta(days=2)
    human_text = "In 2 days"
    urgency = "medium"

    hour = 17
    minute = 0
    if re.search(r'morning|10\s*am|11\s*am', text_lower):
        hour = 10
    elif re.search(r'afternoon|2\s*pm|1\s*pm|3\s*pm', text_lower):
        hour = 14
        minute = 30
    elif re.search(r'evening|6\s*pm|5\s*pm|7\s*pm', text_lower):
        hour = 18
    elif re.search(r'night|8\s*pm|9\s*pm', text_lower):
        hour = 20
    
    # Specific time match e.g. "4 pm", "4:30 pm", "11:00 am"
    time_match = re.search(r'(\b[0-1]?[0-9]|2[0-3])(?::([0-5][0-9]))?\s*(am|pm)\b', text_lower)
    if time_match:
        h = int(time_match.group(1))
        m = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3)
        if ampm == 'pm' and h < 12:
            h += 12
        elif ampm == 'am' and h == 12:
            h = 0
        hour = h
        minute = m

    if "today" in text_lower or "tonight" in text_lower or "within 2 hours" in text_lower or "by 6 pm today" in text_lower:
        target_dt = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        human_text = f"Today by {hour:02d}:{minute:02d}"
        urgency = "critical"
    elif "tomorrow" in text_lower or "next day" in text_lower:
        target_dt = (base_time + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        human_text = f"Tomorrow by {hour:02d}:{minute:02d}"
        urgency = "high"
    elif "day after tomorrow" in text_lower:
        target_dt = (base_time + timedelta(days=2)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        human_text = f"In 2 days by {hour:02d}:{minute:02d}"
        urgency = "medium"
    else:
        matched_day = None
        for day_name, day_idx in WEEKDAYS.items():
            if re.search(rf'\b{day_name}\b', text_lower):
                current_day_idx = base_time.weekday()
                days_ahead = day_idx - current_day_idx
                if days_ahead <= 0:
                    days_ahead += 7
                target_dt = (base_time + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                matched_day = day_name.capitalize()
                human_text = f"{matched_day} by {hour:02d}:{minute:02d}"
                urgency = "high" if days_ahead <= 2 else "medium"
                break
        
        if not matched_day:
            in_days_match = re.search(r'in\s+(\d+)\s+days?', text_lower)
            if in_days_match:
                days = int(in_days_match.group(1))
                target_dt = (base_time + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                human_text = f"In {days} days"
                urgency = "high" if days <= 2 else "medium"

            in_hours_match = re.search(r'in\s+(\d+)\s+hours?', text_lower)
            if in_hours_match:
                hrs = int(in_hours_match.group(1))
                target_dt = base_time + timedelta(hours=hrs)
                human_text = f"In {hrs} hours"
                urgency = "critical"

    return target_dt, human_text, urgency

def extract_currency_and_amount(text: str) -> tuple[float, str]:
    curr = "₹"
    if "$" in text or "dollar" in text.lower():
        curr = "$"
    elif "€" in text or "euro" in text.lower():
        curr = "€"
    elif "£" in text or "pound" in text.lower():
        curr = "£"

    k_match = re.search(r'(?:₹|rs\.?|\$|€|£)?\s*(\d+(?:\.\d+)?)\s*(?:k|thousand)\b', text, re.I)
    if k_match:
        try:
            return float(k_match.group(1)) * 1000, curr
        except ValueError:
            pass

    num_match = re.search(r'(?:₹|rs\.?|\$|€|£)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)', text, re.I)
    if num_match:
        clean = num_match.group(1).replace(",", "")
        try:
            return float(clean), curr
        except ValueError:
            pass

    pay_match = re.search(r'(?:pay|advance|transfer|deposit|amount of)\s+(\d+000|\d{4,6})', text, re.I)
    if pay_match:
        try:
            return float(pay_match.group(1)), curr
        except ValueError:
            pass

    return 0.0, curr

def extract_customer_name(chat_text: str, default_name: str = "Valued Customer") -> str:
    lines = chat_text.strip().split("\n")
    for line in lines:
        match = re.match(r'^(?:customer|client|from|buyer|patient):\s*([a-zA-Z\s]{2,30})', line, re.I)
        if match:
            return match.group(1).strip()
            
    for line in lines:
        line_clean = re.sub(r'^(?:\[.*?\]|\d{1,2}:\d{2}\s*(?:am|pm)?\s*[-–]?)\s*', '', line, flags=re.I).strip()
        sender_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*:', line_clean)
        if sender_match:
            candidate = sender_match.group(1).strip()
            if candidate.lower() not in ['owner', 'shop', 'admin', 'you', 'me', 'agent', 'support', 'designer', 'team', 'technician']:
                return candidate
                
    greeting_match = re.search(r'\b(?:hi|hello|hey|dear)\s+([A-Z][a-z]+)\b', chat_text)
    if greeting_match:
        return greeting_match.group(1).strip()

    return default_name

def assign_responsible_team_member(deliverable_text: str) -> tuple[str, str, str]:
    for pattern, name, role, cat in DEPARTMENT_MAP:
        if pattern.search(deliverable_text):
            return name, role, cat
    return "Sameer", "Logistics & Delivery", "general"

def extract_promises_from_dialogue(text: str) -> List[Dict[str, Any]]:
    """
    Specialized parser for multi-line customer-owner dialogues:
    Customer: "Can you deliver the table by Friday?"
    Owner: "Yes, Friday evening."
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if len(lines) >= 2:
        cust_line = lines[0]
        owner_line = lines[1]
        
        # Check if customer asked for something and owner agreed
        if re.search(r'can\s+you|could\s+you|when\s+will|is\s+it\s+possible|deliver|ready|repair|send', cust_line, re.I) and \
           re.search(r'yes|done|sure|definitely|ready|will\s+do|confirmed|evening|morning|afternoon|sharp', owner_line, re.I):
            
            customer_name = extract_customer_name(text)
            combined_context = f"{cust_line} {owner_line}"
            
            target_dt, human_dt, urgency = parse_relative_time(combined_context)
            amt, curr = extract_currency_and_amount(combined_context)
            resp_name, resp_role, cat = assign_responsible_team_member(combined_context)
            
            # Identify deliverable
            if "table" in combined_context.lower() or "furniture" in combined_context.lower():
                title = "Table / Furniture Delivery"
                deliverable = "Deliver customer table & installation"
            elif "design" in combined_context.lower() or "figma" in combined_context.lower():
                title = "Design Deliverable"
                deliverable = "Send completed UI/UX design mockups"
            elif "repair" in combined_context.lower() or "screen" in combined_context.lower() or "phone" in combined_context.lower():
                title = "Phone / Device Repair Ready"
                deliverable = "Device repair inspection & handover"
            else:
                title = f"{cat.capitalize()} Commitment"
                deliverable = cust_line.split(":")[-1].strip() if ":" in cust_line else cust_line

            return [{
                "customer_name": customer_name,
                "direction": "business_to_customer",
                "category": cat,
                "title": title,
                "deliverable": deliverable,
                "due_date": target_dt.strftime("%Y-%m-%d %H:%M"),
                "due_date_text": human_dt,
                "payment_amount": amt,
                "currency": curr,
                "responsible_person": resp_name,
                "responsible_role": resp_role,
                "priority": urgency,
                "original_message": f"{cust_line}\n{owner_line}",
                "channel": "whatsapp"
            }]

    return []

def extract_promises_from_text(text: str, customer_override: Optional[str] = None, gemini_api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Main extraction entrypoint.
    If gemini_api_key is provided and valid, calls Gemini 2.0 / Flash.
    Otherwise uses high-precision heuristic NLP parser.
    """
    # Try LLM if API key provided
    if gemini_api_key and gemini_api_key.strip():
        try:
            llm_result = extract_with_gemini(text, gemini_api_key)
            if llm_result:
                return llm_result
        except Exception as e:
            print(f"Gemini API fallback to local parser due to: {e}")

    # Step 1: Check if it's a multi-turn dialogue question/answer
    dialogue_promises = extract_promises_from_dialogue(text)
    if dialogue_promises:
        return dialogue_promises

    # Step 2: Clause based parser
    extracted = []
    customer_name = customer_override or extract_customer_name(text)
    text_clean = text.strip()
    
    # Split by conjunctions & clauses
    clauses = []
    raw_lines = text_clean.split("\n")
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        subparts = re.split(r'\b(?:and(?:\s+then|\s+you|\s+i|\s+we)?|also|meanwhile|plus)\b', line, flags=re.I)
        for part in subparts:
            part = part.strip()
            if len(part) > 3:
                clauses.append((line, part))

    for full_line, clause in clauses:
        # Check customer payment promise
        if re.search(r'\b(i(\'ll|\swill)?|client|customer|we(\'ll)?)\s*(pay|send|transfer|deposit|bring|share|give|clear)\b', clause, re.I) or \
           (re.search(r'(?:pay|transfer|advance|upi)\s*(?:₹|rs\.?|\$)?\s*\d+', clause, re.I) and not re.search(r'\byou\s+pay\b', clause, re.I)):
            amt, curr = extract_currency_and_amount(clause)
            target_dt, human_dt, urgency = parse_relative_time(clause)
            title = f"Payment Commitment ({curr}{int(amt):,})" if amt > 0 else "Customer Payment Commitment"
            deliverable = f"₹{int(amt):,} payment transfer / confirmation from {customer_name}" if amt > 0 else f"Payment deposit as agreed by {customer_name}"
            
            extracted.append({
                "customer_name": customer_name,
                "direction": "customer_to_business",
                "category": "payment",
                "title": title,
                "deliverable": deliverable,
                "due_date": target_dt.strftime("%Y-%m-%d %H:%M"),
                "due_date_text": human_dt,
                "payment_amount": amt,
                "currency": curr,
                "responsible_person": "Priya",
                "responsible_role": "Finance & Accounts",
                "priority": urgency,
                "original_message": clause,
                "channel": "whatsapp"
            })

    for full_line, clause in clauses:
        # Business deliverable promise
        is_biz_promise = False
        if re.search(r'\b(you|we|i|shop|team|us)\s*(send|deliver|dispatch|make|share|finish|repair|fix|mail|provide)\b', clause, re.I):
            is_biz_promise = True
        elif re.search(r'\b(send|deliver|dispatch|finish|repair|share)\s+(?:the\s+)?(design|mockup|table|sofa|report|album|photos|renders?|product|order|files?)\b', clause, re.I):
            is_biz_promise = True
        elif re.search(r'\b(will\s+be\s+ready|ready\s+by|available\s+by)\b', clause, re.I):
            is_biz_promise = True

        if is_biz_promise:
            # Check if this was accidentally categorized as payment
            if re.search(r'^\s*i(\'ll|\swill)\s+pay', clause, re.I):
                continue

            target_dt, human_dt, urgency = parse_relative_time(clause)
            resp_name, resp_role, cat = assign_responsible_team_member(clause + " " + text_clean)
            
            if "design" in clause.lower() or "figma" in clause.lower() or "mockup" in clause.lower():
                title = "Figma Design Mockups v1"
                deliverable_desc = "Deliver completed UI/UX design mockups and Figma review link"
            elif "table" in clause.lower() or "furniture" in clause.lower():
                title = "Table / Furniture Delivery"
                deliverable_desc = "Delivery and placement of customer order at destination"
            elif "render" in clause.lower() or "3d" in clause.lower():
                title = "3D Architectural Render"
                deliverable_desc = "4K Photorealistic interior 3D visualizations"
            elif "repair" in clause.lower() or "screen" in clause.lower() or "phone" in clause.lower():
                title = "Device Repair & Handover"
                deliverable_desc = "Completed hardware diagnosis, replacement & QC inspection"
            elif "photo" in clause.lower() or "album" in clause.lower() or "teaser" in clause.lower():
                title = "Photography Teaser / Album Delivery"
                deliverable_desc = "Curated album gallery preview and high-res print export"
            elif "report" in clause.lower() or "test" in clause.lower():
                title = "Medical Diagnostic Report Delivery"
                deliverable_desc = "Lab analysis results & WhatsApp PDF dispatch"
            else:
                title = f"{cat.capitalize()} Deliverable"
                deliverable_desc = clause.strip()

            amt, curr = extract_currency_and_amount(clause)

            extracted.append({
                "customer_name": customer_name,
                "direction": "business_to_customer",
                "category": cat,
                "title": title,
                "deliverable": deliverable_desc,
                "due_date": target_dt.strftime("%Y-%m-%d %H:%M"),
                "due_date_text": human_dt,
                "payment_amount": amt,
                "currency": curr,
                "responsible_person": resp_name,
                "responsible_role": resp_role,
                "priority": urgency,
                "original_message": clause,
                "channel": "whatsapp"
            })

    # Fallback if nothing specific matched
    if not extracted:
        target_dt, human_dt, urgency = parse_relative_time(text_clean)
        amt, curr = extract_currency_and_amount(text_clean)
        resp_name, resp_role, cat = assign_responsible_team_member(text_clean)
        
        extracted.append({
            "customer_name": customer_name,
            "direction": "business_to_customer",
            "category": cat,
            "title": f"Commitment for {customer_name}",
            "deliverable": text_clean[:120],
            "due_date": target_dt.strftime("%Y-%m-%d %H:%M"),
            "due_date_text": human_dt,
            "payment_amount": amt,
            "currency": curr,
            "responsible_person": resp_name,
            "responsible_role": resp_role,
            "priority": urgency,
            "original_message": text_clean,
            "channel": "whatsapp"
        })

    # Deduplicate
    unique_extracted = []
    seen = set()
    for item in extracted:
        key = (item["customer_name"], item["direction"], item["title"], item["due_date_text"])
        if key not in seen:
            seen.add(key)
            unique_extracted.append(item)

    return unique_extracted

def extract_with_gemini(text: str, api_key: str) -> Optional[List[Dict[str, Any]]]:
    """Optional external LLM call to Google Gemini for complex contextual extractions."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    prompt = f"""
You are an expert AI Promise Extractor for business operations.
Extract every customer commitment and business promise made in this conversation:
Text:
\"\"\"{text}\"\"\"

Return ONLY a JSON array of objects with the following schema:
[
  {{
    "customer_name": string,
    "direction": "business_to_customer" or "customer_to_business",
    "category": "delivery" | "payment" | "design" | "repair" | "photography" | "renovation" | "healthcare" | "general",
    "title": string,
    "deliverable": string,
    "due_date": "YYYY-MM-DD HH:MM",
    "due_date_text": string,
    "payment_amount": number,
    "currency": "₹" | "$",
    "responsible_person": string,
    "responsible_role": string,
    "priority": "critical" | "high" | "medium" | "low",
    "original_message": string
  }}
]
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        return json.loads(raw_text)
