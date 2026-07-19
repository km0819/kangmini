import streamlit as st
from google import genai
from google.genai import types
import json
import os

# 대화 내역을 저장할 JSON 파일 경로
HISTORY_FILE = "chat_history.json"

# 1. 스트림릿 페이지 설정 및 UI 구성
st.set_page_config(page_title="kangmini - AI 어시스턴트", page_icon="✨")
st.title("✨ 안녕, 나는 강미나이야 (kangmini)")
st.caption("Google의 Gemini 기술을 기반으로 작동하는 당신의 개인 AI 어시스턴트입니다.")

# 2. 파일에서 대화 내역 불러오는 함수
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# 3. 파일에 대화 내역 저장하는 함수
def save_history(messages):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

# 4. 🔒 보안 강화: 스트림릿 Secrets를 시스템 환경 변수로 완벽 동기화
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
else:
    st.error("🔑 API 키가 설정되지 않았습니다. Streamlit Secrets 또는 secrets.toml 파일을 확인해주세요.")
    st.stop()

# 구글 모듈이 위의 환경 변수를 가장 정확하고 안전하게 읽어옵니다.
client = genai.Client()

# 5. 세션 상태 초기화 (처음 실행 시 파일에서 내역을 읽어옴)
if "messages" not in st.session_state:
    st.session_state.messages = load_history()

# 6. 상단 사이드바에 내역 관리 및 프로필 추가
with st.sidebar:
    st.header("✨ AI 프로필")
    st.markdown("**이름:** 강미나이 (kangmini)")
    st.markdown("**기반 기술:** Gemini 3.5 Flash")
    st.markdown("---")
    if st.button("🗑️ 대화 내역 전체 삭제"):
        st.session_state.messages = []
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.rerun()

# 7. 보관된 이전 대화 기록을 화면에 안전하게 표시
for message in st.session_state.messages:
    if isinstance(message, dict) and "role" in message and "content" in message:
        # 화면 표시 아이디는 kangmini로 설정
        display_role = "kangmini" if message["role"] == "assistant" else "user"
        avatar = "✨" if message["role"] == "assistant" else None
        with st.chat_message(display_role, avatar=avatar):
            st.write(message["content"])

# 8. 사용자로부터 채팅 입력 받기
if user_input := st.chat_input("궁금한 점이 있다면 무엇이든 물어보세요..."):
    # 사용자가 입력한 메시지를 화면에 출력하고 세션에 저장
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_history(st.session_state.messages)

    # AI의 답변 공간 생성 및 로딩 표시
    with st.chat_message("kangmini", avatar="✨"):
        with st.spinner("생각 중..."):
            try:
                # 맥락 전달을 위한 전체 대화 내역 빌드
                formatted_contents = []
                for msg in st.session_state.messages:
                    role = "model" if msg["role"] == "assistant" else "user"
                    formatted_contents.append({
                        "role": role,
                        "parts": [{"text": msg["content"]}]
                    })

                # 💡 강미나이(kangmini) 페르소나 및 행동 수칙 주입
                system_prompt = (
                    "당신의 이름은 한글로 '강미나이', 영문으로는 'kangmini'입니다. 구글의 제미나이(Gemini) 모델을 기반으로 만들어진 "
                    "매우 똑똑하고 친절한 AI 어시스턴트입니다. 사용자가 이름을 물어보면 반드시 '강미나이(kangmini)'라고 답해야 합니다. "
                    "답변 스타일은 구글 제미나이 공식 서비스처럼 정중하고, 가독성이 높으며(마크다운, 글머리 기호 적극 사용), "
                    "유용하고 유익한 정보를 명확하게 제공해야 합니다. 무례하거나 부적절한 질문에는 침착하고 객관적으로 거절하세요."
                )

                # 최신 안정화 모델(gemini-3.5-flash) 및 설정 적용 호출
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=formatted_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt
                    )
                )
                ai_response = response.text
                
                # 답변 출력 및 세션/파일에 저장
                st.write(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                save_history(st.session_state.messages)
                
            except Exception as e:
                st.error(f"통신 중 오류가 발생했습니다: {e}")
