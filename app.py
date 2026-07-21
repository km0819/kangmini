import streamlit as st, os, json, time, bcrypt
from google import genai
from google.genai import types
from supabase import create_client, Client

# 1. 🔑 Supabase 클라이언트 보안 초기화
@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

# 📂 데이터베이스 강제 무결성 보장 함수
def init_secure_db():
    try:
        # 데이터베이스 서버 연결 및 기존 계정 검색
        res = supabase.table("users_db").select("*").execute()
        users_data = res.data
    except Exception:
        users_data = []

    # 데이터베이스에 admin 계정이 없으면 암호화하여 강제 재생성
    admin_exists = any(u["id"] == "admin" for u in users_data)
    if not admin_exists:
        hashed_pw = bcrypt.hashpw("12345".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            supabase.table("users_db").delete().eq("id", "admin").execute()
            supabase.table("users_db").insert({"id": "admin", "name": "마스터 관리자", "password": hashed_pw}).execute()
        except Exception:
            pass

init_secure_db()

# 2. 🔒 외부 라이브러리 우회형 하이브리드 직접 인증 시스템 가동
if "auth_status" not in st.session_state:
    st.session_state.auth_status = False
if "username" not in st.session_state:
    st.session_state.username = None
if "name" not in st.session_state:
    st.session_state.name = None

# 로그인 성공 여부에 따른 화면 분기
if not st.session_state.auth_status:
    st.title("🔒 강미나이 보안 로그인 시스템")
    with st.form("direct_login_form"):
        input_id = st.text_input("아이디(ID)").strip()
        input_pw = st.text_input("비밀번호(PW)", type="password").strip()
        if st.form_submit_button("로그인 인증 요청"):
            try:
                # 데이터베이스에서 입력한 ID 유저 검색
                res = supabase.table("users_db").select("*").eq("id", input_id).execute()
                if res.data:
                    user_info = res.data[0]
                    # 암호화된 Bcrypt 비밀번호 일치 검증
                    if bcrypt.checkpw(input_pw.encode('utf-8'), user_info["password"].encode('utf-8')):
                        st.session_state.auth_status = True
                        st.session_state.username = user_info["id"]
                        st.session_state.name = user_info["name"]
                        st.success("🔒 암호화 보안 세션 연결 성공!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ 비밀번호가 올바르지 않습니다.")
                else:
                    st.error("❌ 존재하지 않는 아이디입니다.")
            except Exception as e:
                st.error(f"데이터베이스 연결 오류: {e}")
    st.stop()

# 3. 🛡️ [로그인 완료 상태] 메인 프로그램 작동
st.set_page_config(page_title="kangmini - Database", page_icon="🛡️", layout="wide")
uid, name = st.session_state.username, st.session_state.name

# 유저 목록 가상 동기화를 위한 최신 디비 로드 함수
def get_current_users():
    res = supabase.table("users_db").select("id, name, password").execute()
    return {u["id"]: u for u in res.data}

db_users = get_current_users()

with st.sidebar:
    st.markdown("### 🛡️ 데이터베이스 제어 센터")
    
    # 👑 마스터 관리자 유저 추가/삭제 통제
    if uid == "admin":
        tc, tm = st.tabs(["➕ 유저 승인", "⚙️ 유저 파기"])
        with tc:
            with st.form("c_f", clear_on_submit=True):
                nid, nn, np = st.text_input("ID").strip(), st.text_input("이름").strip(), st.text_input("PW", type="password").strip()
                if st.form_submit_button("신규 계정 허가") and nid and nn and np:
                    if nid in db_users: st.error("⚠️ 이미 가입된 ID")
                    else:
                        h_pw = bcrypt.hashpw(np.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        supabase.table("users_db").insert({"id": nid, "name": nn, "password": h_pw}).execute()
                        st.success(f"🎉 계정 생성 완료!"); time.sleep(0.5); st.rerun()
        with tm:
            for u in [k for k in db_users.keys() if k != "admin"]:
                if st.button(f"🗑️ {db_users[u]['name']}({u}) 파기", key=f"d_{u}"):
                    supabase.table("users_db").delete().eq("id", u).execute()
                    supabase.table("chat_rooms").delete().eq("username", u).execute()
                    st.success("데이터 영구 파기 완료!"); time.sleep(0.5); st.rerun()
                    
    # 🔐 내 개인 정보 업데이트 (비번 및 아이디 변경 기능)
    with st.expander("👤 비밀 정보 업데이트"):
        with st.form("p_f", clear_on_submit=True):
            st.markdown("**🔐 비밀번호 변경 (Bcrypt)**")
            cp, np, cnp = st.text_input("현재 PW", type="password"), st.text_input("새 PW", type="password"), st.text_input("새 PW 확인", type="password")
            if st.form_submit_button("암호 변경 적용") and np == cnp and np:
                if bcrypt.checkpw(cp.encode('utf-8'), db_users[uid]["password"].encode('utf-8')):
                    new_h_pw = bcrypt.hashpw(np.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    supabase.table("users_db").update({"password": new_h_pw}).eq("id", uid).execute()
                    st.success("🔒 암호 변경 완료!"); time.sleep(1); st.rerun()
                else: st.error("⚠️ 현재 암호 불일치")
        
        with st.form("id_f", clear_on_submit=True):
            st.markdown("**🆔 아이디(ID) 변경 및 전 데이터 이관**")
            change_id_pw = st.text_input("본인 인증용 PW", type="password")
            new_user_id = st.text_input("변경할 새 ID").strip()
            if st.form_submit_button("아이디 변경 적용") and new_user_id:
                if new_user_id in db_users: st.error("⚠️ 이미 선점된 ID")
                elif not bcrypt.checkpw(change_id_pw.encode('utf-8'), db_users[uid]["password"].encode('utf-8')): st.error("⚠️ 비밀번호 불일치")
                else:
                    u_info = db_users[uid]
                    supabase.table("users_db").insert({"id": new_user_id, "name": u_info["name"], "password": u_info["password"]}).execute()
                    supabase.table("chat_rooms").update({"username": new_user_id}).eq("username", uid).execute()
                    supabase.table("users_db").delete().eq("id", uid).execute()
                    st.success("🔒 데이터베이스 마이그레이션 성공! 재로그인 해주세요.")
                    st.session_state.auth_status = False
                    time.sleep(1.5); st.rerun()

    # 🕒 DB 저장 기반 제미나이 멀티 대화방 리스트 출력
    st.markdown("---"); st.header("🕒 내 대화방 목록")
    if st.button("➕ 새로운 대화 세션", use_container_width=True): st.session_state.current_room_id = None; st.rerun()
    
    res_rooms = supabase.table("chat_rooms").select("room_id, title, timestamp").eq("username", uid).order("timestamp", desc=True).execute()
    rooms = res_rooms.data
    
    if "current_room_id" not in st.session_state: st.session_state.current_room_id = rooms[0]["room_id"] if rooms else None
    
    for r in rooms:
        c1, c2 = st.columns([4, 1])
        with c1:
            if st.button(f"💬 {r['title']}", key=f"r_{r['room_id']}", use_container_width=True, type="primary" if st.session_state.current_room_id == r['room_id'] else "secondary"):
                st.session_state.current_room_id = r['room_id']; st.rerun()
        with c2:
            if st.button("🗑️", key=f"dr_{r['room_id']}", use_container_width=True):
                supabase.table("chat_rooms").delete().eq("room_id", r['room_id']).execute()
                if st.session_state.current_room_id == r['room_id']: st.session_state.current_room_id = None
                st.rerun()

# 4. 대화방 메시지 바인딩 및 렌더링
active_room_id = st.session_state.current_room_id or f"room_{uid}_{int(time.time())}"

room_data = supabase.table("chat_rooms").select("*").eq("room_id", active_room_id).execute()
msgs = room_data.data[0]["messages"] if room_data.data else []

c_t, c_l = st.columns([5, 1])
c_t.title("✨ 안녕, 나는 강미나이야 (kangmini)")
c_t.caption(f"🛡️ 반갑습니다 {name}님! 모든 데이터가 클라우드 DB(Supabase)에 실시간 영구 보관됩니다.")
with c_l:
    st.write("")
    if st.button("안전 로그아웃", use_container_width=True):
        st.session_state.auth_status = False
        st.session_state.username = None
        st.rerun()

for m in msgs:
    with st.chat_message("kangmini" if m["role"] == "assistant" else "user", avatar="✨" if m["role"] == "assistant" else None): st.write(m["content"])

# 5. 실시간 메시지 발송 및 실시간 DB 동기화 업서트(Upsert)
if inp := st.chat_input("강미나이 보안 채널에 메시지 입력..."):
    st.chat_message("user").write(inp); msgs.append({"role": "user", "content": inp})
    
    is_new = (st.session_state.current_room_id is None)
    if is_new: st.session_state.current_room_id = active_room_id
    
    title = inp[:12] + "..." if len(inp) > 12 else inp
    room_payload = {"room_id": active_room_id, "username": uid, "title": title, "messages": msgs, "timestamp": time.time()}
    supabase.table("chat_rooms").upsert(room_payload).execute()

    with st.chat_message("kangmini", avatar="✨"), st.spinner("보안 통신망 해석 중..."):
        try:
            os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
            fmt = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in msgs]
            sys = "당신의 이름은 '강미나이(kangmini)'입니다. 구글 제미나이 기반 친절하고 똑똑한 AI입니다."
            ans = genai.Client().models.generate_content(model='gemini-3.5-flash', contents=fmt, config=types.GenerateContentConfig(system_instruction=sys)).text
            st.write(ans); msgs.append({"role": "assistant", "content": ans})
            
            room_payload["messages"] = msgs
            supabase.table("chat_rooms").upsert(room_payload).execute()
            st.rerun()
        except Exception as e: st.error(f"통신 장애: {e}")
