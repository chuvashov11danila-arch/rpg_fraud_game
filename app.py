import streamlit as st
import psycopg2
import os
from PIL import Image, ImageOps
from dotenv import load_dotenv

load_dotenv()

# ========== НАСТРОЙКА СТРАНИЦЫ ==========
st.set_page_config(
    page_title="Охотник за фродом",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# ========== ПАРОЛЬ ==========
PASSWORD = "охотник2026"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Доступ к конкурсу")
    user_pass = st.text_input("Введите пароль для входа:", type="password")
    if st.button("Войти"):
        if user_pass == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Неверный пароль!")
    st.stop()

# ========== ПОДКЛЮЧЕНИЕ К БД ==========
def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return None

# ========== ПОИСК ФАЙЛОВ ==========
def find_image_file(path):
    if not path:
        return None
    if os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    for ext in ['.jpg', '.jpeg', '.png', '.gif']:
        test_path = base + ext
        if os.path.exists(test_path):
            return test_path
    return None

# ========== ИНИЦИАЛИЗАЦИЯ ==========
if 'step' not in st.session_state:
    st.session_state.step = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'lives' not in st.session_state:
    st.session_state.lives = 3
if 'game_over' not in st.session_state:
    st.session_state.game_over = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'cases' not in st.session_state:
    st.session_state.cases = []
if 'started' not in st.session_state:
    st.session_state.started = False

# ========== ЗАГРУЗКА КЕЙСОВ ==========
if not st.session_state.started:
    st.title("🕵️‍♂️ Охотник за фродом")
    st.markdown("""
    👋 **Добро пожаловать в конкурс!**  
    Ты — агент отдела «Охотник за фродом».  
    Твоя задача — проверять документы и ловить мошенников.
    """)
    
    name = st.text_input("Введите ваше ФИО для начала:")
    if st.button("🚀 Начать охоту"):
        if name.strip():
            st.session_state.user_name = name
            st.session_state.started = True
            
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT quest_id, descriptions, case_image, meme_path, correct_action FROM public.quests ORDER BY quest_id;")
                    rows = cursor.fetchall()
                    st.session_state.cases = rows
                    st.success(f"✅ Загружено {len(rows)} кейсов!")
                except Exception as e:
                    st.error(f"❌ Ошибка загрузки: {e}")
                finally:
                    cursor.close()
                    conn.close()
            st.rerun()
        else:
            st.warning("⚠️ Введите ФИО!")

# ========== ОСНОВНОЙ ЦИКЛ ==========
else:
    if not st.session_state.cases:
        st.error("❌ Кейсы не загружены.")
        if st.button("🔄 Начать сначала"):
            st.session_state.started = False
            st.session_state.step = 0
            st.session_state.cases = []
            st.rerun()
        st.stop()

    if st.session_state.game_over:
        st.title("💀 GAME OVER")
        if st.button("🔁 Начать заново"):
            st.session_state.started = False
            st.session_state.step = 0
            st.session_state.score = 0
            st.session_state.lives = 3
            st.session_state.game_over = False
            st.session_state.cases = []
            st.rerun()
        st.stop()

    if st.session_state.step >= len(st.session_state.cases):
        st.balloons()
        st.title("🏆 ПОБЕДА!")
        st.markdown(f"**{st.session_state.user_name}**, ты прошёл все кейсы!")
        st.markdown(f"✅ **Правильных ответов:** {st.session_state.score}")
        st.markdown(f"❤️ **Осталось жизней:** {st.session_state.lives}")
        if st.button("🔁 Пройти заново"):
            st.session_state.started = False
            st.session_state.step = 0
            st.session_state.score = 0
            st.session_state.lives = 3
            st.session_state.game_over = False
            st.session_state.cases = []
            st.rerun()
        st.stop()

    case = st.session_state.cases[st.session_state.step]
    quest_id, description, case_image, meme_path, correct_action = case

    st.markdown(f"**👤 Агент:** {st.session_state.user_name}")
    st.markdown(f"**❤️ Жизни:** {'❤️' * st.session_state.lives}")
    st.markdown(f"**📊 Кейс {st.session_state.step + 1} из {len(st.session_state.cases)}**")
    st.divider()

    col1, col2 = st.columns([1, 1])
    with col1:
        if case_image:
            img = find_image_file(case_image)
            if img:
                st.image(img, width=400)
            else:
                st.warning("Фото не найдено")
    with col2:
        st.markdown(description.replace('\\n', '\n'))
        st.markdown("---")
        action = st.radio("Что делаем?", ["Принять", "Недействительный", "В ЧС"])
        if st.button("✅ Отправить решение"):
            action_map = {"Принять": "approve", "Недействительный": "reject", "В ЧС": "blacklist"}
            user_action = action_map[action]
            if user_action == correct_action:
                st.session_state.score += 1
                st.success("✅ Верно!")
            else:
                st.session_state.lives -= 1
                st.error("❌ Ошибка!")
                if st.session_state.lives <= 0:
                    st.session_state.game_over = True
            st.session_state.step += 1
            st.rerun()

    if st.button("🚪 Выйти"):
        st.session_state.started = False
        st.session_state.step = 0
        st.session_state.score = 0
        st.session_state.lives = 3
        st.session_state.game_over = False
        st.session_state.cases = []
        st.rerun()
