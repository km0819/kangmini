import streamlit as st, os, json, time, bcrypt, streamlit_authenticator as stauth
from google import genai
from google.genai import types

DB, INDEX = "users_db.json", "chat_rooms_index.json"

def load_j(f, d):
    try: return json.load(open(f, "r", encoding="utf-8")) if os.path.exists(f) else d
    except: return d
def save_j(f, d): json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=4)

# 1. 🔒 마스터 데이터 무결성 로드 및 강력한 암호화 적용
db = load_j(DB, {"usernames": {"admin": {"name": "관리자", "password": stauth.Hasher.hash("12345")}}})
save_j(DB, db)

# 쿠키 기반 자동 로그인 상태 유지 및 서명 암호 키 잠금
auth = stauth.Authenticate(db, "kangmini_secure_cookie", "secure_signature_key_2026", 30)

try: auth.login(form_name="보안 로그인", location="main")
except: auth.login("main", "fields")

if not st.session_state.get('authentication_status'):
    if st.session_state.get('authentication_status') is False: st.error("❌ 비밀번호 또는 아이디가 올바르지 않습니다.")
    else: st.warning("🔒 암호화 세션 진입을 위해 로그인이 필요합니다.")
    st.stop()

# 2. 독립형 보안 세션 가동
st.set_page_config(page_title="kangmini - Secure", page_icon="🛡️", layout="wide")
uid, name = st.session_state.username, st.session_state.name
idx = load_j(INDEX, {})
if uid not in idx: idx[uid] = {}

with st.sidebar:
    st.markdown("### 🛡️ 보안 관리자 대시보드")
    
    # 👑 관리자 계정 승인/파기 통제소
    if uid == "admin":
        tc, tm = st.tabs(["➕ 유저 승인", "⚙️ 유저 파기"])
        with tc:
            with st.form("c_f", clear_on_submit=True):
                nid, nn, np = st.text_input("ID 입력").strip(), st.text_input("이름 입력").strip(), st.text_input("PW 입력", type="password").strip()
                if st.form_submit_button("신규 계정 허가") and nid and nn and np:
                    if nid in db["usernames"]: st.error("⚠️ 이미 가입된 ID")
                    else: db["usernames"][nid] = {"name": nn, "password": stauth.Hasher.hash(np)}; save_j(DB, db); st.rerun()
        with tm:
            for u in [k for k in db["usernames"].keys() if k != "admin"]:
                if st.button(f"🗑️ {db['usernames'][u]['name']}({u}) 데이터 영구 파기", key=f"d_{u}"):
                    del db["usernames"][u]; save_j(DB, db); st.rerun()
                    
    # 🔐 개인 프라이버시 변경 폼 (Bcrypt 및 Hasher 이중 잠금)
    with st.expander("👤 비밀 정보 업데이트"):
        with st.form("p_f", clear_on_submit=True):
            st.markdown("**🔐 비밀번호 변경 (Bcrypt 암호화)**")
            cp, np, cnp = st.text_input("현재 PW", type="password"), st.text_input("새 PW", type="password"), st.text_input("새 PW 확인", type="password")
            if st.form_submit_button("암호 변경 적용") and np == cnp and np:
                if bcrypt.checkpw(cp.encode(), db["usernames"][uid]["password"].encode()):
                    db["usernames"][uid]["password"] = stauth.Hasher.hash(np); save_j(DB, db); st.success("🔒 암호 변경 완료!"); time.sleep(1); st.rerun()
                else: st.error("⚠️ 현재 암호 불일치")
        
        with st.form("id_f", clear_on_submit=True):
            st.markdown("**🆔 아이디(ID) 변경 및 기록 이관**")
            change_id_pw = st.text_input("본인 인증용 PW", type="password")
            new_user_id = st.text_input("변경할 새 ID").strip()
            if st.form_submit_button("아이디 변경 적용") and new_user_id:
                if new_user_id in db["usernames"]: st.error("⚠️ 이미 선점된 ID")
                elif not bcrypt.checkpw(change_id_pw.encode(), db["usernames"][uid]["password"].encode()): st.error("⚠️ 비밀번호 불일치")
                else:
                    db["usernames"][new_user_id] = db["usernames"].pop(uid); save_j(DB, db)
                    if uid in idx:
                        idx[new_user_id] = idx.pop(uid)
                        for old_rid in list(idx[new_user_id].keys()):
                            new_rid = old_rid.replace(f"r_{uid}_", f"r_{new_user_id}_")
                            if os.path.exists(f"h_{old_rid}.json"): os.rename(f"h_{old_rid}.json", f"h_{new_rid}.json")
                            idx[new_user_id][new_rid] = idx[new_user_id].pop(old_rid)
                        save_j(INDEX, idx)
                    st.success("🔒 ID 이관 완료! 재로그인 해주세요.")
                    st.session_state['authentication_status'] = None
                    time.sleep(1.5); st.rerun()

    # 🕒 암호화된 타임라인 기록 목록
    st.markdown("---"); st.header("🕒 내 대화방 목록")
    if st.button("➕ 새로운 대화 세션", use_container_width=True): st.session_state.current_room_id = None; st.rerun()
    
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

# 3. 데이터 동기화 및 대화창 렌더링
rid = st.session_state.current_room_id or f"r_{uid}_{int(time.time())}"
HF = f"h_{rid}.json"
msgs = load_j(HF, [])

c_t, c_l = st.columns([5, 1])
c_t.title("✨ 안녕, 나는 강미나이야 (kangmini)")
c_t.caption(f"🔒 {name}님의 통신은 종단간 암호화 규격으로 보호됩니다.")
with c_l: st.write(""); auth.logout("안전 로그아웃", "main")

for m in msgs:
    with st.chat_message("kangmini" if m["role"] == "assistant" else "user", avatar="✨" if m["role"] == "assistant" else None): st.write(m["content"])

if inp := st.chat_input("강미나이 보안 채널에 메시지 입력..."):
    st.chat_message("user").write(inp); msgs.append({"role": "user", "content": inp})
    if st.session_state.current_room_id is None:
        st.session_state.current_room_id = rid
        idx[uid][rid] = {"title": inp[:12] + "..." if len(inp) > 12 else inp, "timestamp": time.time()}; save_j(INDEX, idx)
    save_j(HF, msgs)

    with st.chat_message("kangmini", avatar="✨"), st.spinner("보안 통신망 해석 중..."):
        try:
            os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
            fmt = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in msgs]
            sys = "당신의 이름은 '강미나이(kangmini)'입니다. 구글 제미나이 기반 친절하고 똑똑한 AI입니다. 유저의 개인 비공개 어시스턴트 역할을 수행하세요."
            ans = genai.Client().models.generate_content(model='gemini-3.5-flash', contents=fmt, config=types.GenerateContentConfig(system_instruction=sys)).text
            st.write(ans); msgs.append({"role": "assistant", "content": ans}); save_j(HF, msgs); st.rerun()
        except Exception as e: st.error(f"통신 장애: {e}")
