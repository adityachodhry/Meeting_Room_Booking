import streamlit as st
from email.message import EmailMessage
import smtplib
from datetime import datetime, date as dt_date
import re
import mysql.connector

# --- Email Configuration ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "aditya.choudhary@isalogistics.in"
SENDER_PASSWORD = "ldpq yrck kgyz hdxc"
COMPANY_DOMAIN = "isalogistics.in"
GROUP_ID = "Teamisa@isalogistics.in"

# --- MySQL Configuration ---
db_user = 'isa_user'
db_password = '4-]8sd51D£A6'
db_host = 'tp-vendor-db.ch6c0kme2q7u.ap-south-1.rds.amazonaws.com'
db_name = 'isa_logistics'
db_port = 3306

# --- Meeting Rooms ---
meeting_rooms = ["Room A", "Room B", "Room C"]

# --- Helper: Clean Email Input ---
def clean_emails(raw_emails):
    return [
        email.strip()
        for email in re.split(r'[,\n]+', raw_emails)
        if email.strip() and "@" in email
    ]

# --- Load bookings from MySQL ---
def load_bookings_from_mysql():
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port
        )
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM meeting_bookings")
        return cursor.fetchall()
    except mysql.connector.Error as e:
        st.error(f"MySQL Error: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# --- Save booking to MySQL ---
def insert_booking_to_mysql(booking):
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port
        )
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO meeting_bookings (
            booked_by, meeting_agenda, booked_meeting_room, meeting_date,
            start_time, end_time, to_email, cc_email
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (
            booking["booked_by"],
            booking.get("agenda", ""),
            booking["room"],
            booking["date"],
            booking["start_time"],
            booking["end_time"],
            ", ".join(booking["to"]),
            ", ".join(booking.get("cc", []))
        ))
        connection.commit()

    except mysql.connector.Error as e:
        st.error(f"MySQL Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# --- Streamlit UI ---
st.set_page_config(page_title="Meeting Room Booking", page_icon="📅")
st.title("📅 Meeting Room Booking")

# --- Sidebar: Room-wise Booking View ---
st.sidebar.header("📖 View Bookings by Room")

selected_room = st.sidebar.selectbox("🏢 Select Room to View Bookings", meeting_rooms)
all_bookings = load_bookings_from_mysql()
room_bookings = [b for b in all_bookings if b.get("booked_meeting_room") == selected_room]
room_bookings.sort(key=lambda b: (b.get("meeting_date"), b.get("start_time")))

if room_bookings:
    for i, b in enumerate(room_bookings, 1):
        to_list = b.get("to_email", "").split(",")
        to_emails = "\n".join([f"- {email.strip()}" for email in to_list if email.strip()])
        st.sidebar.markdown(
            f"""---  
**{i}. 🏢 Booked Meeting Room - `{b['booked_meeting_room']}`**  
👤 **Booked By:** `{b.get('booked_by', '')}`  
📆 **Date:** `{b['meeting_date']}`  
🕒 **Time:** `{datetime.strptime(str(b['start_time']), "%H:%M:%S").strftime("%I:%M %p")} - {datetime.strptime(str(b['end_time']), "%H:%M:%S").strftime("%I:%M %p")}`  
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
        start_dt = datetime.combine(date, start_time_input)
        end_dt = datetime.combine(date, end_time_input)

        formatted_start_time = start_time_input.strftime("%I:%M %p")
        formatted_end_time = end_time_input.strftime("%I:%M %p")

        if not booked_by or not to_emails:
            st.error("❌ 'Meeting Booked By' and 'To Emails' are required.")
        elif start_dt >= end_dt:
            st.error("❌ End time must be after start time.")
        else:
            # Check for conflicts
            conflict = False
            for booking in all_bookings:
                # Ensure the room and date match
                if booking["booked_meeting_room"] == room and str(booking["meeting_date"]) == str(date):
                    try:
                        # Convert stored time values safely to datetime objects
                        existing_start = datetime.combine(
                            datetime.strptime(str(booking["meeting_date"]), "%Y-%m-%d").date(),
                            datetime.strptime(str(booking["start_time"]), "%H:%M:%S").time()
                        )
                        existing_end = datetime.combine(
                            datetime.strptime(str(booking["meeting_date"]), "%Y-%m-%d").date(),
                            datetime.strptime(str(booking["end_time"]), "%H:%M:%S").time()
                        )

                        # Check overlap logic
                        if start_dt < existing_end and end_dt > existing_start:
                            conflict = True
                            break
                    except Exception as e:
                        st.error(f"⛔ Error in conflict check: {e}")

            if conflict:
                st.warning("⚠️ This room is already booked for the selected time slot.")
            else:
                raw_to_list = clean_emails(to_emails)
                cc_list = clean_emails(cc_emails)

                internal_to = [e for e in raw_to_list if e.endswith(f"@{COMPANY_DOMAIN}")]
                external_to = [e for e in raw_to_list if not e.endswith(f"@{COMPANY_DOMAIN}")]
                final_to_list = external_to.copy()
                if internal_to:
                    final_to_list.append(GROUP_ID)

                # Compose Email
                content = f"""
📅 New Meeting Booking

Booked By: {booked_by}
Meeting Agenda: {agenda or '(No agenda provided)'}
Meeting Room: {room}
Start Time: {date} at {formatted_start_time}
End Time: {date} at {formatted_end_time}

(This is an automated message.)
"""
                msg = EmailMessage()
                msg["Subject"] = "New Meeting Booking Update"
                msg["From"] = SENDER_EMAIL
                msg["To"] = ", ".join(final_to_list)
                if cc_list:
                    msg["Cc"] = ", ".join(cc_list)
                msg.set_content(content)

                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.send_message(msg)

                # Save to MySQL
                booking_data = {
                    "room": room,
                    "date": str(date),
                    "start_time": str(start_time_input),
                    "end_time": str(end_time_input),
                    "to": raw_to_list,
                    "cc": cc_list,
                    "booked_by": booked_by,
                    "agenda": agenda
                }

                insert_booking_to_mysql(booking_data)

                st.success("✅ Meeting booked and email sent successfully!")

    except Exception as e:
        st.error(f"❌ Error: {e}")

    