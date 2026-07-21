import streamlit as st, os, json, time, bcrypt, streamlit_authenticator as stauth
from google import genai
from google.genai import types

DB, INDEX = "users_db.json", "chat_rooms_index.json"

def load_j(f, d):
    try: return json.load(open(f, "r", encoding="utf-8")) if os.path.exists(f) else d
    except: return d
def save_j(f, d): json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=4)

# 1. 유저 DB 로드 및 인증 초기화
db = load_j(DB, {"usernames": {"admin": {"name": "관리자", "password": stauth.Hasher.hash("12345")}}})
save_j(DB, db)
auth = stauth.Authenticate(db, "k_cookie", "k_key", 30)

try: auth.login(form_name="로그인", location="main")
except: auth.login("main", "fields")

if not st.session_state.get('authentication_status'):
    if st.session_state.get('authentication_status') is False: st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
    else: st.warning("🔒 승인된 계정으로 로그인 후 이용해 주세요.")
    st.stop()

# 2. 로그인 성공 시 메인 앱 실행
st.set_page_config(page_title="kangmini", page_icon="✨", layout="wide")
uid, name = st.session_state.username, st.session_state.name
idx = load_j(INDEX, {})
if uid not in idx: idx[uid] = {}

with st.sidebar:
    st.subheader("🛠️ 설정")
    # 관리자 기능 (계정 생성/삭제)
    if uid == "admin":
        tc, tm = st.tabs(["➕생성", "⚙️관리"])
        with tc:
            with st.form("c_f", clear_on_submit=True):
                nid, nn, np = st.text_input("ID").strip(), st.text_input("이름").strip(), st.text_input("PW", type="password").strip()
                if st.form_submit_button("등록") and nid and nn and np:
                    if nid in db["usernames"]: st.error("중복 ID")
                    else: db["usernames"][nid] = {"name": nn, "password": stauth.Hasher.hash(np)}; save_j(DB, db); st.rerun()
        with tm:
            for u in [k for k in db["usernames"].keys() if k != "admin"]:
                if st.button(f"🗑️ {db['usernames'][u]['name']}({u})", key=f"d_{u}"):
                    del db["usernames"][u]; save_j(DB, db); st.rerun()
                    
    # 🛠️ [핵심 추가]: 내 정보 변경 (비번 및 아이디 변경 기능)
    with st.expander("👤 내 정보 변경하기"):
        # 비밀번호 변경 폼
        with st.form("p_f", clear_on_submit=True):
            st.markdown("**비밀번호 변경**")
            cp, np, cnp = st.text_input("현재 비번", type="password"), st.text_input("새 비번", type="password"), st.text_input("새 비번 확인", type="password")
            if st.form_submit_button("비밀번호 변경") and np == cnp and np:
                if bcrypt.checkpw(cp.encode(), db["usernames"][uid]["password"].encode()):
                    db["usernames"][uid]["password"] = stauth.Hasher.hash(np); save_j(DB, db); st.success("변경 완료!"); time.sleep(1); st.rerun()
                else: st.error("비번 불일치")
        
        # 아이디 변경 폼 (과거 대화방 데이터 완전 승계 이관 시스템 탑재)
        with st.form("id_f", clear_on_submit=True):
            st.markdown("**아이디(ID) 변경**")
            change_id_pw = st.text_input("본인 확인용 비밀번호", type="password")
            new_user_id = st.text_input("새로운 아이디 (영문/숫자)").strip()
            if st.form_submit_button("아이디 변경 적용") and new_user_id:
                if new_user_id in db["usernames"]: st.error("이미 사용 중인 아이디")
                elif not bcrypt.checkpw(change_id_pw.encode(), db["usernames"][uid]["password"].encode()): st.error("비밀번호 불일치")
                else:
                    # 1) 유저 데이터베이스 키 이관
                    db["usernames"][new_user_id] = db["usernames"].pop(uid)
                    save_j(DB, db)
                    # 2) 대화방 인덱스 정보 이관
                    if uid in idx:
                        idx[new_user_id] = idx.pop(uid)
                        # 3) 실제 저장된 개별 대화 내역 JSON 파일명 일괄 변경
                        for old_rid in list(idx[new_user_id].keys()):
                            new_rid = old_rid.replace(f"r_{uid}_", f"r_{new_user_id}_")
                            if os.path.exists(f"h_{old_rid}.json"): os.rename(f"h_{old_rid}.json", f"h_{new_rid}.json")
                            idx[new_user_id][new_rid] = idx[new_user_id].pop(old_rid)
                        save_j(INDEX, idx)
                    st.success("ID 변경 완료! 다시 로그인해 주세요.")
                    # 세션 강제 만료 및 쿠키 무효화 처리 후 로그인 창으로 리다이렉트
                    st.session_state['authentication_status'] = None
                    time.sleep(1.5); st.rerun()

    # 멀티 대화방 목록
    st.markdown("---"); st.header("🕒 최근 대화")
    if st.button("➕ 새로운 채팅", use_container_width=True): st.session_state.current_room_id = None; st.rerun()
    
    sorted_rooms = sorted(idx[uid].items(), key=lambda x: x['timestamp'], reverse=True)
    if "current_room_id" not in st.session_state: st.session_state.current_room_id = sorted_rooms if sorted_rooms else None
    
    for rid, rinfo in sorted_rooms:
        c1, c2 = st.columns([5, 1])
        with c1:
            if st.button(f"💬 {rinfo['title']}", key=f"r_{rid}", use_container_width=True, type="primary" if st.session_state.current_room_id == rid else "secondary"):
                st.session_state.current_room_id = rid; st.rerun()
        with c2:
            if st.button("❌", key=f"dr_{rid}", use_container_width=True):
                if os.path.exists(f"h_{rid}.json"): os.remove(f"h_{rid}.json")
                del idx[uid][rid]; save_j(INDEX, idx)
                if st.session_state.current_room_id == rid: st.session_state.current_room_id = None
                st.rerun()

# 3. 대화창 본문 구성
rid = st.session_state.current_room_id or f"r_{uid}_{int(time.time())}"
HF = f"h_{rid}.json"
msgs = load_j(HF, [])

c_t, c_l = st.columns([5, 1])
c_t.title("✨ 안녕, 나는 강미나이야 (kangmini)")
c_t.caption(f"👋 반갑습니다 {name}님!")
with c_l: st.write(""); auth.logout("로그아웃", "main")

for m in msgs:
    with st.chat_message("kangmini" if m["role"] == "assistant" else "user", avatar="✨" if m["role"] == "assistant" else None): st.write(m["content"])

if inp := st.chat_input("강미나이에게 물어보세요..."):
    st.chat_message("user").write(inp); msgs.append({"role": "user", "content": inp})
    if st.session_state.current_room_id is None:
        st.session_state.current_room_id = rid
        idx[uid][rid] = {"title": inp[:12] + "..." if len(inp) > 12 else inp, "timestamp": time.time()}; save_j(INDEX, idx)
    save_j(HF, msgs)

    with st.chat_message("kangmini", avatar="✨"), st.spinner("생각 중..."):
        try:
            os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
            fmt = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in msgs]
            sys = "당신의 이름은 '강미나이(kangmini)'입니다. 구글 제미나이 기반 친절하고 똑똑한 AI입니다. 가독성 좋게 답하세요."
            ans = genai.Client().models.generate_content(model='gemini-3.5-flash', contents=fmt, config=types.GenerateContentConfig(system_instruction=sys)).text
            st.write(ans); msgs.append({"role": "assistant", "content": ans}); save_j(HF, msgs); st.rerun()
        except Exception as e: st.error(f"오류: {e}")
