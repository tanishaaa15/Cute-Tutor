import streamlit as st
from datetime import datetime
from groq import Groq
from fpdf import FPDF
import json, os, pandas as pd
from collections import defaultdict

# -------------------- CONSTANTS --------------------
DATA_DIR   = "data"
USERS_JSON = os.path.join(DATA_DIR, "users.json")
FONT_PATH  = "NotoSans-Regular.ttf"    # put this .ttf next to ai_app.py

# -------------------- STARTUP & FOLDERS --------------------
os.makedirs(DATA_DIR, exist_ok=True)

# -------------------- HELPERS --------------------
def load_users():
    if os.path.exists(USERS_JSON):
        with open(USERS_JSON, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_JSON, "w") as f:
        json.dump(users, f, indent=2)

def save_report_as_pdf(text, filename="Weekly_Report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("UFont", "", FONT_PATH, uni=True)
    pdf.set_font("UFont", size=12)
    for line in text.split("\n"):
        pdf.multi_cell(0, 8, line)
    path = os.path.join(DATA_DIR, filename)
    pdf.output(path)
    return path

# -------------------- LOGIN / REGISTER --------------------
users = load_users()
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login Portal")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state.update({"logged_in": True,
                                     "username": username,
                                     "user_info": users[username]})
            st.success("Login successful!"); st.rerun()
        else:
            st.error("Invalid credentials")

    if st.button("Register"):
        if username in users:
            st.warning("Username already exists.")
        else:
            users[username] = {"password": password,
                               "student_name": "",
                               "parent_name": "",
                               "parent_phone": "",
                               "tutor_history": [],
                               "reports": []}
            save_users(users)
            st.success("Registered! Please login.")
    st.stop()

# -------------------- SESSION SHORTCUTS --------------------
username   = st.session_state.username
user_info  = users[username]

# -------------------- INIT GROQ --------------------
client = Groq(api_key=st.secrets["groq_api_key"])
def ask_groq(prompt):
    res = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content

# -------------------- SIDEBAR NAV --------------------
page = st.sidebar.radio(
    "Go to",
    ["🏠 Home", "📊 Learning Style", "🧑‍🏫 Cute Tutor",
     "🧘 Counselor", "👨‍👩‍👧 Parent Report", "📅 Progress Tracker"]
)

# -------------------- PAGES --------------------
# --- HOME ---
if page == "🏠 Home":
    st.title("🎓 Welcome to Your AI Educational Assistant – Cute Tutor")
    st.markdown("""This assistant helps you with:
- Understanding learning style  
- Personalized tutoring  
- Emotional check‑ins  
- Weekly PDF parent reports""")

    with st.form("profile"):
        st.subheader("👤 Student & Parent Info")
        user_info["student_name"] = st.text_input("Student Name", user_info.get("student_name", ""))
        user_info["parent_name"]  = st.text_input("Parent Name",  user_info.get("parent_name",  ""))
        user_info["parent_phone"] = st.text_input("Parent Mobile", user_info.get("parent_phone", ""))
        if st.form_submit_button("Save"):
            users[username] = user_info
            save_users(users)
            st.success("Profile saved.")

# --- LEARNING STYLE ---
elif page == "📊 Learning Style":
    st.title("📊 Discover Your Learning Style")
    v = st.slider("I learn best with images", 1,5); a = st.slider("…by listening",1,5); k = st.slider("…by doing",1,5)
    if st.button("Analyze"):
        style = max({"Visual":v,"Auditory":a,"Kinesthetic":k}, key=lambda x: {"Visual":v,"Auditory":a,"Kinesthetic":k}[x])
        st.session_state.learning_style = style
        st.success(f"Your dominant style: *{style}*")

# --- CUTE TUTOR ---
elif page == "🧑‍🏫 Cute Tutor":
    st.title("🧑‍🏫 Cute Tutor")
    topic = st.text_input("Topic")
    level = st.selectbox("Level", ["Beginner","Intermediate","Advanced"])
    style = st.session_state.get("learning_style","Visual")
    tips  = {"Visual":"diagrams & vivid examples","Auditory":"story‑style explanations","Kinesthetic":"hands‑on tasks"}[style]

    if st.button("Teach Me") and topic.strip():
        prompt = (f"You are Cute Tutor. Explain '{topic}' to a {level} student using {style} approach "
                  f"({tips}). Make it fun and clear.")
        answer = ask_groq(prompt)
        st.markdown("### 🐣 Cute Tutor Says:")
        st.write(answer)

        # store session with date stamp
        user_info["tutor_history"].append({
            "topic":topic, "level":level, "style":style,
            "content":answer, "date":datetime.now().strftime("%Y-%m-%d")
        }); save_users(users)

# --- COUNSELOR ---
elif page == "🧘 Counselor":
    st.title("🧘 Emotional Check‑in with Cute Tutor")
    if "chat_history" not in st.session_state: st.session_state.chat_history=[]
    for who,msg in st.session_state.chat_history:
        st.markdown(f"{'*You:' if who=='child' else 'Cute Tutor:*'} {msg}")
    child_msg = st.text_input("How are you feeling?")
    if st.button("Send") and child_msg.strip():
        st.session_state.chat_history.append(("child",child_msg))
        convo = "\n".join(("Child: "+m if w=="child" else "Cute Tutor: "+m) for w,m in st.session_state.chat_history)
        reply = ask_groq("You are Cute Tutor, a gentle counselor.\n"+convo+"\nCute Tutor:")
        st.session_state.chat_history.append(("tutor", reply.strip()))
        st.rerun()

# --- PARENT REPORT ---
elif page == "👨‍👩‍👧 Parent Report":
    st.title("👨‍👩‍👧 Weekly Parent Report")

    if user_info["tutor_history"]:
        st.markdown("### Topics This Week")
        for t in user_info["tutor_history"]:
            st.markdown(f"- {t['topic']} ({t['level']}, {t['style']})")
    else:
        st.info("No tutoring sessions yet.")

    topics_note  = st.text_area("📝 Topic Performance Summary")
    emotions     = st.text_area("💬 Emotional Notes")
    improvements = st.text_area("🧠 Challenges & Recommendations")

    def generate_report():
        summary = "\n".join(f"- {t['topic']} ({t['level']}): {t['content'][:200]}…" for t in user_info["tutor_history"])
        date = datetime.now().strftime("%d %B %Y")
        prompt = f"""
You are an educational counselor.

Write a concise weekly report (bullet style) for parent {user_info['parent_name']} about {user_info['student_name']} (contact {user_info['parent_phone']}). Date: {date}

1. Topics Covered:
{summary or 'None this week.'}

2. Emotional Well‑being:
{emotions or 'No notes provided.'}

3. Areas for Improvement & Recommendations:
{improvements or 'No issues noted.'}

If the student is auditory, suggest podcasts or read‑aloud tools.

End with: Best regards, Cute Tutor."""
        return ask_groq(prompt).strip()

    if st.button("Generate Weekly Report"):
        report = generate_report()
        st.subheader("📝 Preview")
        st.text_area("Report", report, height=300)
        # save record
        user_info["reports"].append({"date":datetime.now().strftime("%Y-%m-%d"),"report":report})
        save_users(users)
        # save & download pdf
        pdf_name = f"{username}_{datetime.now().strftime('%Y%m%d')}_Report.pdf"
        path = save_report_as_pdf(report, pdf_name)
        with open(path,"rb") as f:
            st.download_button("📥 Download PDF", f, file_name=pdf_name, mime="application/pdf")
        st.success("Report saved!")

# --- PROGRESS TRACKER ---
elif page == "📅 Progress Tracker":
    st.title("📅 Progress Tracker")

    # line chart
    if user_info["tutor_history"]:
        counts = defaultdict(int)
        for s in user_info["tutor_history"]:
            week = datetime.strptime(s["date"], "%Y-%m-%d").strftime("%Y‑W%U")
            counts[week]+=1
        df = pd.DataFrame(sorted(counts.items()), columns=["Week","Topics"]).set_index("Week")
        st.line_chart(df)
    else:
        st.info("No tutoring data to chart yet.")

    # past reports viewer
    st.subheader("📄 Past Weekly Reports")
    if user_info["reports"]:
        report_dates = [r["date"] for r in user_info["reports"]][::-1]
        choice = st.selectbox("Select a date", report_dates)
        report = next(r["report"] for r in user_info["reports"] if r["date"]==choice)
        st.text_area("Report Content", report, height=400)
    else:
        st.info("No reports saved yet.")