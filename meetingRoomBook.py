import streamlit as st
from email.message import EmailMessage
import smtplib
from datetime import datetime, date as dt_date
import re
import uuid
import json
import os
from PIL import Image

# --- Email Configuration ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "aditya.choudhary@isalogistics.in"  
SENDER_PASSWORD = "ldpq yrck kgyz hdxc" 
COMPANY_DOMAIN = "isalogistics.in"
GROUP_ID = "Teamisa@isalogistics.in"

# --- File to store bookings ---
BOOKING_FILE = "bookings.json"

# --- Meeting Rooms ---
meeting_rooms = ["Room A", "Room B", "Room C", "Room D"]

# --- Helper: Clean Email Input ---
def clean_emails(raw_emails):
    return [
        email.strip()
        for email in re.split(r'[,\n]+', raw_emails)
        if email.strip() and "@" in email
    ]

# --- Helper: Load all bookings ---
def load_bookings():
    if os.path.exists(BOOKING_FILE):
        with open(BOOKING_FILE, "r") as f:
            return json.load(f)
    return []

# --- Helper: Save a new booking ---
def save_booking(booking):
    bookings = load_bookings()
    bookings.append(booking)
    with open(BOOKING_FILE, "w") as f:
        json.dump(bookings, f, indent=2, default=str)

# --- Streamlit UI ---
st.set_page_config(page_title="Meeting Room Booking", page_icon="📅")

# # --- Display Logo ---
# logo = Image.open("Isa Group Logo.png")
# st.image(logo, use_column_width=False, width=2000)

st.title("📅 Meeting Room Booking")

# --- Sidebar: Room-wise Booking View ---S
st.sidebar.header("📖 View Bookings by Room")

selected_room = st.sidebar.selectbox("🏢 Select Room to View Bookings", meeting_rooms)
all_bookings = load_bookings()
room_bookings = [b for b in all_bookings if b.get("room") == selected_room]
room_bookings.sort(key=lambda b: (b.get("date"), b.get("start_time")))

if room_bookings:
    for i, b in enumerate(room_bookings, 1):
        to_list = b.get("to", [])
        to_emails = "\n".join([f"- {email}" for email in to_list]) if to_list else "- (No recipients)"
        booked_by = b.get("booked_by", "(Unknown)")
        st.sidebar.markdown(
            f"""---  
**{i}. 🏢 Booked Meeting Room - `{b['room']}`**  
👤 **Booked By:** `{booked_by}`  
📆 **Date:** `{b['date']}`  
🕒 **Time:** `{datetime.strptime(b['start_time'], "%H:%M:%S").strftime("%I:%M %p")} - {datetime.strptime(b['end_time'], "%H:%M:%S").strftime("%I:%M %p")}`  
📧 **To:** {to_emails}
"""
        )
else:
    st.sidebar.info("No bookings yet for this room.")

# --- Form Input ---
with st.form("booking_form"):
    booked_by = st.text_input("👤 Meeting Booked By Name").strip()
    agenda = st.text_input("📌 Meeting Agenda (optional)").strip()
    room = st.selectbox("🏢 Select Meeting Room", meeting_rooms)
    date = st.date_input("📆 Meeting Date", min_value=dt_date.today())
    start_time_input = st.time_input("🕒 Start Time")
    end_time_input = st.time_input("🕔 End Time")
    to_emails = st.text_area("✉️ To Emails (comma or newline separated)").strip()
    cc_emails = st.text_area("📤 Cc Emails (optional)").strip()
    submitted = st.form_submit_button("✅ Book and Send Email")

# --- Handle Submission ---
if submitted:
    try:
        # Combine date and time
        start_dt = datetime.combine(date, start_time_input)
        end_dt = datetime.combine(date, end_time_input)

        # Format AM/PM
        formatted_start_time = start_time_input.strftime("%I:%M %p")
        formatted_end_time = end_time_input.strftime("%I:%M %p")

        # Check conflict
        conflict = False
        for booking in all_bookings:
            if booking["room"] == room and booking["date"] == str(date):
                existing_start = datetime.strptime(f"{booking['date']} {booking['start_time']}", "%Y-%m-%d %H:%M:%S")
                existing_end = datetime.strptime(f"{booking['date']} {booking['end_time']}", "%Y-%m-%d %H:%M:%S")
                if start_dt < existing_end and end_dt > existing_start:
                    conflict = True
                    break

        if not booked_by or not to_emails:
            st.error("❌ 'Meeting Booked By' and 'To Emails' are required.")
        elif start_dt >= end_dt:
            st.error("❌ End time must be after start time.")
        elif conflict:
            st.warning("⚠️ This room is already booked for the selected time slot. Please choose another time or room.")
        else:
            # Clean and separate emails
            raw_to_list = clean_emails(to_emails)
            cc_list = clean_emails(cc_emails)

            # Filter internal and external
            internal_to = [email for email in raw_to_list if email.endswith(f"@{COMPANY_DOMAIN}")]
            external_to = [email for email in raw_to_list if not email.endswith(f"@{COMPANY_DOMAIN}")]
            final_to_list = external_to.copy()
            if internal_to:
                final_to_list.append(GROUP_ID)

            # Email content
            content = f"""
📅 New Meeting Booking

Booked By: {booked_by}
Meeting Agenda: {agenda or '(No agenda provided)'}
Meeting Room: {room}
Start Time: {date} at {formatted_start_time}
End Time: {date} at {formatted_end_time}

⚠️ This email is for **testing purposes** for the Meeting Room Booking system.  
**Please ignore this email.**

(This is an automated notification.)
"""
            # Send email
            msg = EmailMessage()
            msg["Subject"] = "New Booking Room Update (Test Email – Please Ignore)"
            msg["From"] = SENDER_EMAIL
            msg["To"] = ", ".join(final_to_list)
            if cc_list:
                msg["Cc"] = ", ".join(cc_list)
            msg["Message-ID"] = f"<{uuid.uuid4()}@booking.local>"
            msg.set_content(content)

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)

            # Save booking
            save_booking({
                "room": room,
                "date": str(date),
                "start_time": str(start_time_input),
                "end_time": str(end_time_input),
                "to": raw_to_list,
                "booked_by": booked_by
            })

            st.success("✅ Meeting booked and email sent successfully!")

    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")


