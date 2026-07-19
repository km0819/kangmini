import streamlit as st
from google import genai
from google.genai import types
import streamlit_authenticator as stauth
import json
import os

# 파일 경로 정의
USER_DB_FILE = "users_db.json"

# 1. 📂 회원 정보 불러오기 및 저장 함수
def load_users():
    """저장된 회원 목록을 불러옵니다. 파일이 없으면 기본 마스터 관리자(admin)를 생성합니다."""
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    # 초기 실행 시 마스터 관리자 계정 생성 (아이디: admin / 비밀번호: 12345)
    default_db = {
        "usernames": {
            "admin": {
                "name": "마스터 관리자",
                "password": stauth.Hasher.hash("12345")
            }
        }
    }
    save_users(default_db)
    return default_db

def save_users(user_data):
    """회원 목록을 JSON 파일로 저장합니다."""
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

# 회원 데이터베이스 로드
credentials = load_users()

# 2. 🔒 로그인 인증 객체 생성 (30일 로그인 유지)
authenticator = stauth.Authenticate(
    credentials,
    cookie_name="kangmini_login_cookie",
    cookie_key="kangmini_secret_signature_key",
    cookie_expiry_days=30
)

# 로그인 화면 출력
name, authentication_status, username = authenticator.login(location="main")

if authentication_status is False:
    st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
    st.stop()
elif authentication_status is None:
    st.warning("🔒 승인된 계정으로 로그인 후 이용해 주세요.")
    st.stop()

# 3. 🎉 로그인 성공 시 메인 프로그램 작동
elif authentication_status:
    
    # ⚙️ 스트림릿 기본 페이지 설정
    st.set_page_config(page_title="kangmini - AI 어시스턴트", page_icon="✨", layout="wide")

    # 4. 👑 관리자 전용 회원 생성 대시보드 (오직 'admin' 계정에게만 표시됨)
    if username == "admin":
        with st.sidebar:
            st.subheader("👑 관리자 메뉴 (계정 생성)")
            
            with st.form("new_user_form", clear_on_submit=True):
                new_id = st.text_input("새 사용자 ID (영문/숫자)").strip()
                new_name = st.text_input("새 사용자 이름(닉네임)").strip()
                new_pw = st.text_input("새 사용자 비밀번호", type="password").strip()
                submit_btn = st.form_submit_button("🚀 신규 계정 승인 및 저장")
                
                if submit_btn:
                    if not new_id or not new_name or not new_pw:
                        st.error("모든 칸을 입력해 주세요.")
                    elif new_id in credentials["usernames"]:
                        st.error("이미 존재하는 아이디입니다.")
                    else:
                        # 비밀번호 암호화 후 데이터베이스에 추가
                        credentials["usernames"][new_id] = {
                            "name": new_name,
                            "password": stauth.Hasher.hash(new_pw)
                        }
                        save_users(credentials) # 파일에 즉시 저장
                        st.success(f"🎉 '{new_name}'님의 계정이 승인되어 보관되었습니다!")
                        st.rerun() # 새로고침하여 인증 모듈에 즉시 반영

    # --- 메인 AI 대화 공간 ---
    # 사용자별 독립된 대화 내역 파일명 지정
    HISTORY_FILE = f"chat_history_{username}.json"

    # 메인 화면 상단 레이아웃을 2개의 칸(제목 칸, 로그아웃 버튼 칸)으로 분할
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.title("✨ 안녕, 나는 강미나이야 (kangmini)")
        st.caption(f"👋 반갑습니다 {name}(@{username})님! 당신만의 안전한 전용 대화방입니다.")
        
    with col2:
        # 우측 상단에 로그아웃 버튼 배치
        st.write("") 
        authenticator.logout("로그아웃", "main")

    def load_history():
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_history(messages):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)

    # 제미나이 API 환경 변수 설정
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    else:
        st.error("🔑 API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
        st.stop()

    client = genai.Client()

    if "messages" not in st.session_state:
        st.session_state.messages = load_history()

    # 사이드바 공통 메뉴
    with st.sidebar:
        st.header("✨ AI 프로필")
        st.markdown(f"**현재 유저:** {name}님")
        st.markdown("**기반 기술:** Gemini 3.5 Flash")
        st.markdown("---")
        
        if st.button("🗑️ 내 대화 내역만 삭제"):
            st.session_state.messages = []
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            st.rerun()

    # 이전 기록 출력
    for message in st.session_state.messages:
        if isinstance(message, dict) and "role" in message and "content" in message:
            display_role = "kangmini" if message["role"] == "assistant" else "user"
            avatar = "✨" if message["role"] == "assistant" else None
            with st.chat_message(display_role, avatar=avatar):
                st.write(message["content"])

    # 채팅 입력 및 답변 처리
    if user_input := st.chat_input("강미나이에게 무엇이든 물어보세요..."):
        st.chat_message("user").write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_history(st.session_state.messages)

        with st.chat_message("kangmini", avatar="✨"):
            with st.spinner("생각 중..."):
                try:
                    formatted_contents = []
                    for msg in st.session_state.messages:
                        role = "model" if msg["role"] == "assistant" else "user"
                        formatted_contents.append({
                            "role": role,
                            "parts": [{"text": msg["content"]}]
                        })

                    system_prompt = (
                        "당신의 이름은 한글로 '강미나이', 영문으로는 'kangmini'입니다. 구글의 제미나이(Gemini) 모델을 기반으로 만들어진 "
                        "매우 똑똑하고 친절한 AI 어시스턴트입니다. 사용자가 이름을 물어보면 반드시 '강미나이(kangmini)'라고 답해야 합니다. "
                        "답변 스타일은 구글 제미나이 공식 서비스처럼 정중하고, 가독성이 높으며(마크다운, 글머리 기호 적극 사용), "
                        "유용하고 유익한 정보를 명확하게 제공해야 합니다. 무례하거나 부적절한 질문에는 침착하고 객관적으로 거절하세요."
                    )

                    response = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=formatted_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt
                        )
                    )
                    ai_response = response.text
                    
                    st.write(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    save_history(st.session_state.messages)
                    
                except Exception as e:
                    st.error(f"통신 중 오류가 발생했습니다: {e}")
