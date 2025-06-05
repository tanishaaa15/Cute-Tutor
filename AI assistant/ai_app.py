import streamlit as st
from groq import Groq
from fpdf import FPDF
import json
import os
from datetime import datetime

# -------------------- SETUP --------------------
if not os.path.exists("data"):
    os.makedirs("data")

# -------------------- AUTH & USER DATA --------------------
def load_users():
    try:
        with open("data/users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open("data/users.json", "w") as f:
        json.dump(users, f, indent=4)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

users = load_users()

if not st.session_state.logged_in:
    st.title("🔐 Login Portal")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_info = users[username]
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.markdown("Don't have an account?")
    if st.button("Register"):
        if username in users:
            st.warning("Username already exists.")
        else:
            users[username] = {
                "password": password,
                "student_name": "",
                "parent_name": "",
                "parent_phone": "",
                "tutor_history": [],
                "reports": []
            }
            save_users(users)
            st.success("Registered! Please login.")
    st.stop()

username = st.session_state.username
user_info = users[username]

# -------------------- INIT GROQ --------------------
client = Groq(api_key=st.secrets["groq_api_key"])

def ask_groq(prompt):
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# -------------------- SIDEBAR --------------------
st.sidebar.title("📚 AI Educational Assistant")
page = st.sidebar.radio("Go to", ["🏠 Home", "📊 Learning Style", "🧑‍🏫 Cute Tutor", "🧘 Counselor", "👨‍👩‍👧 Parent Report"])

# -------------------- HOME --------------------
if page == "🏠 Home":
    st.title("🎓 Welcome to Your AI Educational Assistant- Cute Tutor")
    st.markdown("""
    **This assistant helps you with:**
    - Understanding your learning style
    - Personalized teaching with Cute Tutor
    - Emotional check-ins with a friendly chat
    - Weekly PDF reports for parents
    """)

    with st.form("user_info_form"):
        st.markdown("#### 👤 Student & Parent Information")
        user_info["student_name"] = st.text_input("Student Name", value=user_info.get("student_name", ""))
        user_info["parent_name"] = st.text_input("Parent Name", value=user_info.get("parent_name", ""))
        user_info["parent_phone"] = st.text_input("Parent Mobile Number", value=user_info.get("parent_phone", ""))
        if st.form_submit_button("Save Info"):
            users[username].update(user_info)
            save_users(users)
            st.success("Information saved.")

# -------------------- LEARNING STYLE --------------------
elif page == "📊 Learning Style":
    st.title("📊 What's Your Learning Style?")
    visual = st.slider("I learn best with images", 1, 5)
    auditory = st.slider("I learn best by listening", 1, 5)
    kinesthetic = st.slider("I learn best by doing", 1, 5)

    if st.button("Analyze"):
        scores = {"Visual": visual, "Auditory": auditory, "Kinesthetic": kinesthetic}
        dominant = max(scores, key=scores.get)
        st.session_state.learning_style = dominant
        st.success(f"You're mostly a **{dominant}** learner!")

# -------------------- CUTE TUTOR --------------------
elif page == "🧑‍🏫 Cute Tutor":
    st.title("🧑‍🏫 Cute Tutor")
    topic = st.text_input("Topic you want help with")
    level = st.selectbox("Choose your level", ["Beginner", "Intermediate", "Advanced"])
    style = st.session_state.get("learning_style", "Visual")

    style_instructions = {
        "Visual": "Use simple diagrams, analogies, and vivid descriptions.",
        "Auditory": "Explain concepts clearly with examples, emphasizing listening and storytelling.",
        "Kinesthetic": "Suggest hands-on activities, experiments, or real-world practice."
    }
    teaching_style_detail = style_instructions.get(style, "")

    if st.button("Teach Me") and topic.strip() != "":
        prompt = (
            f"You are Cute Tutor, a fun and encouraging AI tutor.\n"
            f"Explain the topic '{topic}' to a {level} level student using a {style} learning style.\n"
            f"Make it engaging and easy to understand.\n"
            f"Here are style tips: {teaching_style_detail}"
        )
        result = ask_groq(prompt)
        st.markdown("### 🐣 Cute Tutor Says:")
        st.write(result)

        user_info["tutor_history"].append({
            "topic": topic,
            "level": level,
            "style": style,
            "content": result
        })
        save_users(users)

# -------------------- EMOTIONAL COUNSELOR CHAT --------------------
elif page == "🧘 Counselor":
    st.title("🧘 Emotional Check-in Chat with Cute Tutor")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for speaker, text in st.session_state.chat_history:
        if speaker == "child":
            st.markdown(f"**You:** {text}")
        else:
            st.markdown(f"**Cute Tutor:** {text}")

    child_msg = st.text_input("How are you feeling or what do you want to talk about?")

    if st.button("Send") and child_msg.strip() != "":
        st.session_state.chat_history.append(("child", child_msg))
        convo_text = ""
        for speaker, text in st.session_state.chat_history:
            if speaker == "child":
                convo_text += f"Child: {text}\n"
            else:
                convo_text += f"Cute Tutor: {text}\n"

        prompt = (
            f"You are Cute Tutor, a warm and friendly emotional coach for children.\n"
            f"Have a gentle conversation with the child to help them express their feelings and offer comfort.\n"
            f"Keep responses short, supportive, and encourage openness.\n\n"
            f"Conversation so far:\n{convo_text}\nCute Tutor:"
        )
        response = ask_groq(prompt).strip()
        st.session_state.chat_history.append(("tutor", response))
        st.rerun()

# -------------------- PARENT REPORT --------------------
elif page == "👨‍👩‍👧 Parent Report":
    st.title("👨‍👩‍👧 Weekly Parent Report")

    if user_info["tutor_history"]:
        st.markdown("### Topics Covered This Week:")
        for item in user_info["tutor_history"]:
            st.markdown(f"- **{item['topic']}** ({item['level']}) - taught with **{item['style']}** style")
    else:
        st.info("No tutoring sessions recorded yet.")

    topics_covered = st.text_area("Topics covered and performance")
    emotions = st.text_area("Child's Emotional Well-being Notes (from observation or conversation)")
    improvements_and_recommendations = st.text_area("Areas for Improvement or Challenges Noticed and Recommendations")

    def generate_report(emotions, improvements_and_recommendations):
        topics_summary = ""
        for t in user_info["tutor_history"]:
            topics_summary += f"- {t['topic']} ({t['level']}): {t['content'][:200]}...\n"

        current_date = datetime.now().strftime("%d %B %Y")

        prompt = f"""
You are an expert educational counselor.

Write a detailed, warm, and clear weekly report for the parent {user_info['parent_name']} about their child, {user_info['student_name']}  (Contact: {user_info['parent_phone']}).
Date: {current_date}

Format the report with these sections:

1. Topics Covered:
{topics_summary or 'No topics covered this week.'}

2. Emotional Well-being:
{emotions or 'No emotional notes provided.'}

3. Areas for Improvement and Recommendations:
{improvements_and_recommendations or 'No specific challenges noted and no recommendations provided.'}

Additionally, if the student is an auditory learner, suggest helpful auditory techniques like listening to educational podcasts or using read-aloud tools for revision.

Write this report in a brief and concise format using bullet points, while keeping the tone supportive and optimistic. End the report with "Best regards, Cute Tutor".
"""
        return ask_groq(prompt).strip()

    def save_report_as_pdf(report_text, filename="Weekly_Report.pdf"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        for line in report_text.split('\n'):
            pdf.multi_cell(0, 10, line)

        filepath = f"data/{filename}"
        pdf.output(filepath)
        return filepath

    if st.button("Generate Report"):
        report_text = generate_report(emotions, improvements_and_recommendations)
        st.markdown("### 📝 Weekly Report:")
        st.write(report_text)

        user_info["reports"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "report": report_text
        })
        save_users(users)

        pdf_path = save_report_as_pdf(report_text, filename=f"{user_info['student_name']}_Weekly_Report.pdf")
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 Download PDF",
                data=f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf"
            )
