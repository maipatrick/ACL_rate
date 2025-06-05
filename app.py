import streamlit as st
import sqlite3
import bcrypt
import random
import pandas as pd

# ---------- CONFIGURATION ----------
VIDEO_LIST = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
    "https://www.youtube.com/watch?v=l482T0yNkeo"
]
DB_FILE = 'users.db'

# ---------- DATABASE FUNCTIONS ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            years_of_experience INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            username TEXT,
            video_url TEXT,
            rating INTEGER,
            PRIMARY KEY (username, video_url)
        )
    ''')
    conn.commit()
    conn.close()

def register_user(username, password, years_of_experience):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password_hash, years_of_experience) VALUES (?, ?, ?)',
                  (username, password_hash, years_of_experience))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    if result:
        return bcrypt.checkpw(password.encode(), result[0].encode())
    return False

def get_unrated_videos(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT video_url FROM ratings WHERE username = ?', (username,))
    rated_videos = [row[0] for row in c.fetchall()]
    conn.close()
    return [v for v in VIDEO_LIST if v not in rated_videos]

def save_rating(username, video_url, rating):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO ratings (username, video_url, rating) VALUES (?, ?, ?)',
              (username, video_url, rating))
    conn.commit()
    conn.close()

def get_years_of_experience(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT years_of_experience FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_years_of_experience(username, years):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET years_of_experience = ? WHERE username = ?', (years, username))
    conn.commit()
    conn.close()

# ---------- MAIN APP ----------
def main():
    st.set_page_config(page_title="Video Rating App", layout="centered")
    st.title("🔐 Secure Login App")

    # Session states
    for key in ["view", "logged_in", "user", "remaining_videos", "current_video", "temp_user"]:
        if key not in st.session_state:
            st.session_state[key] = None

    # ---------- LOGIN/REGISTER INTERFACE ----------
    if not st.session_state.logged_in:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔑 Login"):
                st.session_state.view = "login"
        with col2:
            if st.button("📝 Register"):
                st.session_state.view = "register"

        if st.session_state.view == "login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login Now"):
                if login_user(username, password):
                    years = get_years_of_experience(username)
                    if years is None:
                        st.session_state.temp_user = username
                        st.session_state.view = "collect_info"
                        st.rerun()
                    else:
                        st.session_state.logged_in = True
                        st.session_state.user = username
                        st.session_state.remaining_videos = get_unrated_videos(username)
                        random.shuffle(st.session_state.remaining_videos)
                        st.session_state.current_video = None
                        st.success(f"Welcome {username}!")
                        st.rerun()
                else:
                    st.error("Invalid username or password")

        elif st.session_state.view == "register":
            st.subheader("Register")
            username = st.text_input("New Username")
            password = st.text_input("New Password", type="password")
            years = st.number_input("Years of research experience", min_value=0, max_value=100, step=1)

            if st.button("Register Now"):
                if register_user(username, password, int(years)):
                    st.success("Account created. Go to Login.")
                else:
                    st.warning("Username already taken.")

        elif st.session_state.view == "collect_info":
            st.subheader("Additional Info Required")
            st.write("Please provide additional info before continuing.")
            years = st.number_input("Years of research experience", min_value=0, max_value=100, step=1)
            if st.button("Submit Info"):
                update_years_of_experience(st.session_state.temp_user, int(years))
                st.session_state.logged_in = True
                st.session_state.user = st.session_state.temp_user
                st.session_state.temp_user = None
                st.session_state.remaining_videos = get_unrated_videos(st.session_state.user)
                random.shuffle(st.session_state.remaining_videos)
                st.session_state.current_video = None
                st.rerun()

    else:
        # ---------- VIDEO RATING INTERFACE ----------
        st.success(f"Logged in as: {st.session_state.user}")
        if st.button("🚪 Logout"):
            for key in ["logged_in", "user", "remaining_videos", "current_video"]:
                st.session_state[key] = None
            st.rerun()

        if not st.session_state.remaining_videos and st.session_state.current_video is None:
            st.info("🎉 You've rated all available videos!")

        else:
            if st.session_state.current_video is None:
                st.session_state.current_video = st.session_state.remaining_videos.pop()

            st.video(st.session_state.current_video)
            rating = st.slider("Rate this video", 1, 5, 3)

            if st.button("Save Rating and Show Next"):
                save_rating(st.session_state.user, st.session_state.current_video, rating)
                st.session_state.current_video = None
                st.rerun()

        # ---------- ADMIN TOOLS ----------
        if st.session_state.user == "admin":
            st.markdown("---")
            st.subheader("🛠 Admin Panel")

            with open(DB_FILE, "rb") as f:
                st.download_button("📦 Download users.db", f, file_name="users.db")

            conn = sqlite3.connect(DB_FILE)
            df_ratings = conn.execute("SELECT * FROM ratings").fetchall()
            df_users = conn.execute("SELECT * FROM users").fetchall()
            conn.close()

            if df_ratings:
                df_ratings = pd.DataFrame(df_ratings, columns=["username", "video_url", "rating"])
                st.dataframe(df_ratings)
                csv_ratings = df_ratings.to_csv(index=False).encode("utf-8")
                st.download_button("📄 Download ratings as CSV", csv_ratings, file_name="video_ratings.csv")
            else:
                st.info("No ratings found yet.")

            if df_users:
                df_users = pd.DataFrame(df_users, columns=["username", "password_hash", "years_of_experience"])
                st.dataframe(df_users[["username", "years_of_experience"]])  # hide password hash
                csv_users = df_users.to_csv(index=False).encode("utf-8")
                st.download_button("📄 Download user info as CSV", csv_users, file_name="user_info.csv")

if __name__ == '__main__':
    init_db()
    main()
