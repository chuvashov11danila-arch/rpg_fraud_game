import psycopg2
import streamlit as st
import os
from PIL import Image, ImageOps

# ========== ФУНКЦИЯ ПОИСКА ФАЙЛА ==========
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

# ========== ИСПРАВЛЕНИЕ ПОВОРОТА ФОТО ==========
def fix_image_orientation(path):
    try:
        image = Image.open(path)
        image = ImageOps.exif_transpose(image)
        return image
    except Exception as e:
        return None

# ========== АВТОПРОКРУТКА ВВЕРХ ==========
def scroll_to_top():
    st.markdown("""
    <script>
        window.scrollTo(0, 0);
    </script>
    """, unsafe_allow_html=True)

# ========== ПОДКЛЮЧЕНИЕ К БД (ЧЕРЕЗ st.secrets) ==========
def get_db_connection():
    try:
        return psycopg2.connect(
            host=st.secrets["connections"]["postgresql"]["host"],
            port=st.secrets["connections"]["postgresql"]["port"],
            user=st.secrets["connections"]["postgresql"]["username"],
            password=st.secrets["connections"]["postgresql"]["password"],
            database=st.secrets["connections"]["postgresql"]["database"]
        )
    except Exception as e:
        st.error(f"❌ Ошибка подключения к БД: {e}")
        return None

# ========== РАБОТА С ИГРОКАМИ ==========
def get_or_create_player(name):
    try:
        conn = get_db_connection()
        if not conn:
            st.error("❌ Нет подключения к БД")
            return None
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM public.players WHERE full_name = %s', (name,))
        row = cursor.fetchone()
        if row:
            player_id = row[0]
        else:
            cursor.execute('INSERT INTO public.players (full_name) VALUES (%s) RETURNING player_id', (name,))
            player_id = cursor.fetchone()[0]
            conn.commit()
        cursor.close()
        conn.close()
        return player_id
    except Exception as e:
        st.error(f"❌ Ошибка в get_or_create_player: {e}")
        return None

def save_result(player_id, quest_id, user_action, is_correct):
    try:
        conn = get_db_connection()
        if not conn:
            st.error("❌ Нет подключения к БД")
            return
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO public.game_results (player_id, quest_id, answer, is_correct)
            VALUES (%s, %s, %s, %s)
        ''', (player_id, quest_id, user_action, is_correct))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"❌ Ошибка в save_result: {e}")

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

# ========== ИНИЦИАЛИЗАЦИЯ СЕССИИ ==========
if 'started' not in st.session_state:
    st.session_state.started = False
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
if 'show_meme' not in st.session_state:
    st.session_state.show_meme = False
if 'current_meme' not in st.session_state:
    st.session_state.current_meme = ""
if 'answered' not in st.session_state:
    st.session_state.answered = False
if 'feedback' not in st.session_state:
    st.session_state.feedback = ""

# ========== ВВОД ИМЕНИ ==========
if not st.session_state.started:
    st.title("🕵️‍♂️ Охотник за фродом")
    welcome_text = """
    👋 **Добро пожаловать в конкурс!**  
    Ты — агент отдела «Охотник за фродом».  
    Твоя задача — проверять документы и ловить мошенников.

    ⚠️ **ВАЖНО!**  
    Твоя задача — проверить **действительность документа** и определить, является ли клиент **мошенником**.  
    Не обращай внимание на качество фото, размытость, цвет, угол съёмки и т.д.  
    Смотри только на **подлинность** и на **действительность документа**.

    - Если паспорт **недействительный** — отклоняй, как недействительный.
    - Если паспорт **действительный и не подделан**, то **принимай** (даже если есть блики, плохое качество, данные закрыты руками, скрин).
    - Если документ **явно поддельный** — отправляй в **ЧС**.

    **Ваша задача** — проверить документ на действительность и подлинность, а не на качество съёмки!
    """
    st.markdown(welcome_text)
    
    name = st.text_input("Введите ваше ФИО для начала:")
    if st.button("🚀 Начать охоту"):
        if name.strip():
            st.session_state.user_name = name
            st.session_state.started = True
            st.session_state.step = 0
            
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT quest_id, descriptions, case_image, meme_path, correct_action 
                    FROM public.quests 
                    ORDER BY RANDOM()
                ''')
                st.session_state.cases = cursor.fetchall()
                cursor.close()
                conn.close()
            scroll_to_top()
            st.rerun()
        else:
            st.warning("⚠️ Введите ваше ФИО!")

# ========== ОСНОВНОЙ ЦИКЛ ИГРЫ ==========
else:
    if not st.session_state.cases:
        st.error("❌ Кейсы не загружены. Проверьте подключение к базе данных.")
        if st.button("🔄 Перезапустить"):
            st.session_state.started = False
            st.session_state.step = 0
            st.session_state.score = 0
            st.session_state.lives = 3
            st.session_state.game_over = False
            st.session_state.show_meme = False
            st.session_state.answered = False
            st.session_state.feedback = ""
            st.rerun()
        st.stop()

    if st.session_state.game_over:
        st.title("💀 GAME OVER")
        st.markdown("**Ты потерял все жизни. Мошенники победили...**")
        img = find_image_file("mem_frod/meme_gameover.jpg")
        if img:
            st.image(img, width=500)
        else:
            st.warning("⚠️ Мем не найден, показываю запасной")
            fallback = find_image_file("mem_frod/meme1.jpg")
            if fallback:
                st.image(fallback, width=500)
        if st.button("🔁 Начать заново"):
            st.session_state.started = False
            st.session_state.step = 0
            st.session_state.score = 0
            st.session_state.lives = 3
            st.session_state.game_over = False
            st.session_state.show_meme = False
            st.session_state.answered = False
            st.session_state.feedback = ""
            st.rerun()
        st.stop()
    
    if st.session_state.cases and st.session_state.step >= len(st.session_state.cases):
        st.balloons()
        st.title("🏆 ПОБЕДА!")
        st.markdown(f"**{st.session_state.user_name}**, ты прошёл все кейсы!")
        st.markdown(f"✅ **Правильных ответов:** {st.session_state.score}")
        st.markdown(f"❤️ **Осталось жизней:** {st.session_state.lives}")
        img = find_image_file("mem_frod/meme_victory.jpg")
        if img:
            st.image(img, width=500)
        else:
            st.warning("⚠️ Мем не найден, показываю запасной")
            fallback = find_image_file("mem_frod/meme1.jpg")
            if fallback:
                st.image(fallback, width=500)
        if st.button("🔁 Пройти заново"):
            st.session_state.started = False
            st.session_state.step = 0
            st.session_state.score = 0
            st.session_state.lives = 3
            st.session_state.game_over = False
            st.session_state.show_meme = False
            st.session_state.answered = False
            st.session_state.feedback = ""
            st.rerun()
        st.stop()
    
    # ========== ТЕКУЩИЙ КЕЙС ==========
    case = st.session_state.cases[st.session_state.step]
    quest_id, description, case_image, meme_path, correct_action = case
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown(f"**👤 Агент:** {st.session_state.user_name}")
    with col2:
        st.markdown(f"**❤️ Жизни:** {'❤️' * st.session_state.lives}")
    with col3:
        st.markdown(f"**📊 Кейс {st.session_state.step + 1} из {len(st.session_state.cases)}**")
    
    st.divider()
    
    col_left, col_right = st.columns([1.5, 2])
    
    with col_left:
        if case_image:
            img_file = find_image_file(case_image)
            if img_file:
                img = fix_image_orientation(img_file)
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.warning(f"⚠️ Не удалось обработать фото: {case_image}")
            else:
                st.warning(f"⚠️ Фото не найдено: {case_image}")
    
    with col_right:
        if not st.session_state.answered:
            clean_description = description.replace('\\n', '\n')
            st.markdown(clean_description)
        st.divider()
        
        st.markdown("""
        ---
        🔍 **Подсказка по решению:**
        - 🟢 **Принять** — если паспорт действительный и не подделан (блики, плохое качество, скрин — не важны)
        - 🟡 **Недействительный** — если документ недействителен (просрочен, не совпадают данные)
        - 🔴 **В ЧС** — если документ явно поддельный (фотошоп, фальшивка)
        ---
        """)
        
        if not st.session_state.answered and not st.session_state.show_meme:
            action = st.radio(
                "**Что делаем?**",
                ["Принять", "Недействительный", "В ЧС"]
            )
            
            if st.button("✅ Отправить решение"):
                st.session_state.answered = True
                action_map = {
                    "Принять": "approve",
                    "Недействительный": "reject",
                    "В ЧС": "blacklist"
                }
                user_action = action_map[action]
                is_correct = (user_action == correct_action)
                
                if is_correct:
                    st.session_state.score += 1
                    st.session_state.feedback = "✅ **Верно!** Ты принял правильное решение."
                else:
                    st.session_state.lives -= 1
                    st.session_state.feedback = "❌ **Ошибка!** Ты ошибся."
                    fail_meme = find_image_file("mem_frod/meme_fail.jpg")
                    st.session_state.current_meme = fail_meme if fail_meme else meme_path or "mem_frod/meme1.jpg"
                    
                    if st.session_state.lives <= 0:
                        st.session_state.game_over = True
                        st.rerun()
                
                if is_correct:
                    st.session_state.current_meme = meme_path
                
                player_id = get_or_create_player(st.session_state.user_name)
                if player_id:
                    save_result(player_id, quest_id, user_action, is_correct)
                else:
                    st.error("❌ Не удалось сохранить результат: игрок не найден/создан")
                
                st.session_state.show_meme = True
                st.rerun()
    
    if st.session_state.show_meme:
        st.markdown(st.session_state.feedback)
        
        if st.session_state.current_meme:
            meme_file = find_image_file(st.session_state.current_meme)
            if meme_file:
                st.image(meme_file, width=500)
            else:
                st.warning(f"⚠️ Мем не найден: {st.session_state.current_meme}")
                fallback = find_image_file("mem_frod/meme1.jpg")
                if fallback:
                    st.image(fallback, width=500)
        else:
            fallback = find_image_file("mem_frod/meme1.jpg")
            if fallback:
                st.image(fallback, width=500)
        
        if st.button("➡️ Следующий кейс"):
            st.session_state.step += 1
            st.session_state.show_meme = False
            st.session_state.answered = False
            st.session_state.feedback = ""
            st.session_state.current_meme = ""
            scroll_to_top()
            st.rerun()
    
    if st.button("🚪 Выйти"):
        st.session_state.started = False
        st.session_state.step = 0
        st.session_state.score = 0
        st.session_state.lives = 3
        st.session_state.game_over = False
        st.session_state.show_meme = False
        st.session_state.answered = False
        st.session_state.feedback = ""
        st.rerun()
