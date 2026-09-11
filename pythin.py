import os
import streamlit as st
import numpy as np
import torch
import torch.nn as nn

BOARD_SIZE = 15

# --- AI 신경망 구조 ---
class OmokNet(nn.Module):
    def __init__(self):
        super(OmokNet, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(64 * BOARD_SIZE * BOARD_SIZE, 128)
        self.fc2 = nn.Linear(128, BOARD_SIZE * BOARD_SIZE)

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

def load_ai_model(difficulty):
    model = OmokNet()
    path_map = {
        "쉬움 (Easy - 100 Epochs)": "easy_model.pt",
        "보통 (Medium - 500 Epochs)": "medium_model.pt",
        "어려움 (Hard - 1000 Epochs)": "hard_model.pt"
    }
    model_path = path_map.get(difficulty, "easy_model.pt")
    
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path))
        model.eval()
    return model

# --- 오목 규칙 & 렌주룰 검사 ---
def is_valid(r, c):
    return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE

def count_line(board, r, c, dr, dc, player):
    count = 1
    i = 1
    while is_valid(r + dr * i, c + dc * i) and board[r + dr * i, c + dc * i] == player:
        count += 1
        i += 1
    i = 1
    while is_valid(r - dr * i, c - dc * i) and board[r - dr * i, c - dc * i] == player:
        count += 1
        i += 1
    return count

def check_win(board, player):
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r, c] == player:
                for dr, dc in [(0, 1), (1, 0), (1, 1), (-1, 1)]:
                    cnt = count_line(board, r, c, dr, dc, player)
                    if player == 1:
                        if cnt == 5:
                            return True
                    else:
                        if cnt >= 5:
                            return True
    return False

def is_forbidden(board, r, c):
    if board[r, c] != 0:
        return False, ""
    
    board[r, c] = 1
    for dr, dc in [(0, 1), (1, 0), (1, 1), (-1, 1)]:
        if count_line(board, r, c, dr, dc, 1) >= 6:
            board[r, c] = 0
            return True, "6목 이상(장목) 금수입니다!"
            
    board[r, c] = 0
    return False, ""

def get_ai_move(model, board):
    empty_cells = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if board[r, c] == 0]
    if not empty_cells:
        return None

    board_tensor = torch.FloatTensor(board).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        output = model(board_tensor).squeeze(0)

    sorted_indices = torch.argsort(output, descending=True)
    for idx in sorted_indices:
        r, c = idx.item() // BOARD_SIZE, idx.item() % BOARD_SIZE
        if board[r, c] == 0:
            return r, c
    return empty_cells[0]

# --- UI 설정 및 바둑판 커스텀 CSS ---
st.set_page_config(page_title="오목", layout="centered")

# 바둑판 나무 질감 & 실제 오목판 스타일링
st.markdown("""
<style>
    /* 제목 스타일 */
    .title-text {
        text-align: center;
        font-size: 42px;
        font-weight: bold;
        color: #222;
        margin-bottom: 10px;
    }
    
    /* 열(Column) 여백 제거 */
    div[data-testid="column"] {
        padding: 0px !important;
        margin: 0px !important;
    }
    
    /* 진짜 바둑판 교차점 격자 스타일 */
    div.stButton > button {
        width: 100% !important;
        height: 36px !important;
        border-radius: 0px !important;
        background-color: #DC9D54 !important; /* 바둑판 원목 색상 */
        border: 1px solid #111111 !important; /* 선명한 검은색 격자선 */
        font-size: 24px !important;
        font-weight: bold !important;
        line-height: 1 !important;
        padding: 0px !important;
        margin: 0px !important;
        box-shadow: none !important;
    }
    
    div.stButton > button:hover {
        background-color: #c98c45 !important;
        border-color: #000000 !important;
    }
    
    div.stButton > button:disabled {
        background-color: #DC9D54 !important;
        color: #000000 !important;
        opacity: 1.0 !important;
    }
</style>
""", unsafe_allow_html=True)

# 요구사항: 제목을 '오목'으로 변경
st.markdown('<div class="title-text">오목</div>', unsafe_allow_html=True)

difficulty = st.sidebar.selectbox("AI 학습 난이도 선택", [
    "쉬움 (Easy - 100 Epochs)",
    "보통 (Medium - 500 Epochs)",
    "어려움 (Hard - 1000 Epochs)"
])

# 세션 상태 관리
if 'board' not in st.session_state:
    st.session_state.board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
if 'turn' not in st.session_state:
    st.session_state.turn = 1
if 'winner' not in st.session_state:
    st.session_state.winner = 0
if 'msg' not in st.session_state:
    st.session_state.msg = ""

if st.button("🔄 게임 초기화"):
    st.session_state.board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
    st.session_state.turn = 1
    st.session_state.winner = 0
    st.session_state.msg = ""
    st.rerun()

if st.session_state.msg:
    st.warning(st.session_state.msg)

if st.session_state.winner == 1:
    st.success("🎉 플레이어(흑돌) 승리!")
elif st.session_state.winner == -1:
    st.error("🤖 AI(백돌) 승리!")

# AI Turn
if st.session_state.turn == -1 and st.session_state.winner == 0:
    ai_model = load_ai_model(difficulty)
    move = get_ai_move(ai_model, st.session_state.board)
    if move:
        r, c = move
        st.session_state.board[r, c] = -1
        if check_win(st.session_state.board, -1):
            st.session_state.winner = -1
        else:
            st.session_state.turn = 1
        st.rerun()

# 15x15 진짜 바둑판 구현
for r in range(BOARD_SIZE):
    cols = st.columns(BOARD_SIZE)
    for c in range(BOARD_SIZE):
        val = st.session_state.board[r, c]
        
        # 선명한 검은원(⚫)과 흰원(⚪) 바둑돌 표시
        label = " "
        if val == 1:
            label = "⚫"
        elif val == -1:
            label = "⚪"
            
        if cols[c].button(label, key=f"{r}_{c}", disabled=(val != 0 or st.session_state.winner != 0)):
            forbidden, reason = is_forbidden(st.session_state.board, r, c)
            if forbidden:
                st.session_state.msg = f"⚠️ 착수 불가: {reason}"
                st.rerun()
            else:
                st.session_state.msg = ""
                st.session_state.board[r, c] = 1
                if check_win(st.session_state.board, 1):
                    st.session_state.winner = 1
                else:
                    st.session_state.turn = -1
                st.rerun()