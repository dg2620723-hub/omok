import http.server
import socketserver
import json
import copy
import random
import sys

BOARD_SIZE = 15
EMPTY = 0
BLACK = 1
WHITE = 2

# ==========================================
# 1. 렌주룰 엔진 & 승리 라인 탐색
# ==========================================
class RenjuEngine:
    DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]

    @staticmethod
    def count_consecutive(board, r, c, dr, dc, color):
        count = 0
        nr, nc = r + dr, c + dc
        while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == color:
            count += 1
            nr += dr
            nc += dc
        return count

    @classmethod
    def get_line_length(cls, board, r, c, dr, dc, color):
        f = cls.count_consecutive(board, r, c, dr, dc, color)
        b = cls.count_consecutive(board, r, c, -dr, -dc, color)
        return f + b + 1

    @classmethod
    def is_exact_five(cls, board, r, c, color):
        for dr, dc in cls.DIRECTIONS:
            if cls.get_line_length(board, r, c, dr, dc, color) == 5:
                return True
        return False

    @classmethod
    def is_overline(cls, board, r, c, color):
        for dr, dc in cls.DIRECTIONS:
            if cls.get_line_length(board, r, c, dr, dc, color) >= 6:
                return True
        return False

    @classmethod
    def is_open_three(cls, board, r, c, dr, dc, color):
        tb = copy.deepcopy(board)
        tb[r][c] = color
        line = []
        for i in range(-4, 5):
            nr, nc = r + dr * i, c + dc * i
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                line.append(tb[nr][nc])
            else:
                line.append(-1)
        center = 4
        for ws in [5, 6]:
            for st in range(max(0, center - ws + 1), min(len(line) - ws + 1, center + 1)):
                sub = line[st:st + ws]
                if sub[0] == EMPTY and sub[-1] == EMPTY and sub.count(color) == 3 and sub.count(EMPTY) == ws - 3 and sub.count(3 - color) == 0 and sub.count(-1) == 0:
                    return True
        return False

    @classmethod
    def is_four(cls, board, r, c, dr, dc, color):
        tb = copy.deepcopy(board)
        tb[r][c] = color
        line = []
        for i in range(-4, 5):
            nr, nc = r + dr * i, c + dc * i
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                line.append(tb[nr][nc])
            else:
                line.append(-1)
        center = 4
        for ws in [5]:
            for st in range(max(0, center - ws + 1), min(len(line) - ws + 1, center + 1)):
                sub = line[st:st + ws]
                if sub.count(color) == 4 and sub.count(EMPTY) == 1 and sub.count(-1) == 0 and sub.count(3 - color) == 0:
                    return True
        return False

    @classmethod
    def is_forbidden_move(cls, board, r, c, color):
        if color != BLACK or board[r][c] != EMPTY:
            return False
        if cls.is_exact_five(board, r, c, BLACK):
            return False
        if cls.is_overline(board, r, c, BLACK):
            return True
        c_3 = sum(1 for dr, dc in cls.DIRECTIONS if cls.is_open_three(board, r, c, dr, dc, BLACK))
        if c_3 >= 2:
            return True
        c_4 = sum(1 for dr, dc in cls.DIRECTIONS if cls.is_four(board, r, c, dr, dc, BLACK))
        if c_4 >= 2:
            return True
        return False

    @classmethod
    def check_winner(cls, board, last_r, last_c):
        if last_r is None or last_c is None:
            return EMPTY
        col = board[last_r][last_c]
        if col == EMPTY:
            return EMPTY
        for dr, dc in cls.DIRECTIONS:
            l = cls.get_line_length(board, last_r, last_c, dr, dc, col)
            if col == BLACK and l == 5:
                return BLACK
            if col == WHITE and l >= 5:
                return WHITE
        return EMPTY

    @classmethod
    def get_winning_line(cls, board, last_r, last_c):
        if last_r is None or last_c is None:
            return []
        color = board[last_r][last_c]
        if color == EMPTY:
            return []

        for dr, dc in cls.DIRECTIONS:
            line = [[last_r, last_c]]
            nr, nc = last_r + dr, last_c + dc
            while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == color:
                line.append([nr, nc])
                nr += dr
                nc += dc
            nr, nc = last_r - dr, last_c - dc
            while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == color:
                line.append([nr, nc])
                nr -= dr
                nc -= dc

            if color == BLACK and len(line) == 5:
                return line
            elif color == WHITE and len(line) >= 5:
                return line
        return []


# ==========================================
# 2. AI 모듈
# ==========================================
class BaseAI:
    def __init__(self, color):
        self.color = color

    def get_move(self, board, history):
        raise NotImplementedError


class SmartGomokuAI(BaseAI):
    def evaluate_point(self, board, r, c, color):
        score = 0
        opp = 3 - color
        for dr, dc in RenjuEngine.DIRECTIONS:
            ml = RenjuEngine.get_line_length(board, r, c, dr, dc, color)
            if ml >= 5: score += 100000
            elif ml == 4: score += 5000
            elif ml == 3: score += 500

            ol = RenjuEngine.get_line_length(board, r, c, dr, dc, opp)
            if ol >= 5: score += 80000
            elif ol == 4: score += 4000
            elif ol == 3: score += 300

        dist = abs(r - 7) + abs(c - 7)
        score += (14 - dist) * 5
        return score

    def get_move(self, board, history):
        if not history:
            return (7, 7)
        best_score = -1
        best_moves = []
        candidates = set()
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] != EMPTY:
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == EMPTY:
                                if self.color == BLACK and RenjuEngine.is_forbidden_move(board, nr, nc, BLACK):
                                    continue
                                candidates.add((nr, nc))
        if not candidates:
            candidates.add((7, 7))

        for r, c in candidates:
            sc = self.evaluate_point(board, r, c, self.color)
            if sc > best_score:
                best_score = sc
                best_moves = [(r, c)]
            elif sc == best_score:
                best_moves.append((r, c))
        return random.choice(best_moves) if best_moves else (7, 7)


# ==========================================
# 3. 게임 상태 관리자
# ==========================================
class GomokuGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.history = []
        self.current_turn = BLACK
        self.winner = EMPTY
        self.game_over = False
        self.status = "당신의 차례입니다 (흑돌)"
        self.winning_line = []
        self.ai = SmartGomokuAI(color=WHITE)

    def get_forbidden_moves(self):
        fouls = []
        if self.current_turn == BLACK and not self.game_over:
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if self.board[r][c] == EMPTY:
                        if RenjuEngine.is_forbidden_move(self.board, r, c, BLACK):
                            fouls.append([r, c])
        return fouls

    def play_move(self, r, c):
        if self.game_over or self.current_turn != BLACK:
            return self.to_dict()

        if self.board[r][c] != EMPTY or RenjuEngine.is_forbidden_move(self.board, r, c, BLACK):
            return self.to_dict()

        # 흑돌 착수
        self.board[r][c] = BLACK
        self.history.append([r, c])

        w = RenjuEngine.check_winner(self.board, r, c)
        if w != EMPTY:
            self.winner = w
            self.game_over = True
            self.status = "🎉 흑돌(플레이어) 승리!"
            self.winning_line = RenjuEngine.get_winning_line(self.board, r, c)
            return self.to_dict()

        if len(self.history) == BOARD_SIZE * BOARD_SIZE:
            self.game_over = True
            self.status = "🤝 무승부입니다!"
            return self.to_dict()

        # 백돌(AI) 착수
        self.current_turn = WHITE
        ai_r, ai_c = self.ai.get_move(self.board, self.history)
        self.board[ai_r][ai_c] = WHITE
        self.history.append([ai_r, ai_c])

        w_ai = RenjuEngine.check_winner(self.board, ai_r, ai_c)
        if w_ai != EMPTY:
            self.winner = w_ai
            self.game_over = True
            self.status = "🤖 백돌(AI) 승리!"
            self.winning_line = RenjuEngine.get_winning_line(self.board, ai_r, ai_c)
        elif len(self.history) == BOARD_SIZE * BOARD_SIZE:
            self.game_over = True
            self.status = "🤝 무승부입니다!"
        else:
            self.current_turn = BLACK
            self.status = "당신의 차례입니다 (흑돌)"

        return self.to_dict()

    def to_dict(self):
        return {
            "board": self.board,
            "history": self.history,
            "current_turn": self.current_turn,
            "winner": self.winner,
            "game_over": self.game_over,
            "status": self.status,
            "winning_line": self.winning_line,
            "forbidden_moves": self.get_forbidden_moves()
        }


game = GomokuGame()

# ==========================================
# 4. 담백한 결과창 적용된 HTML/JS 프론트엔드
# ==========================================
HTML_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>오목의 달인 - Codespaces</title>
    <style>
        * { box-sizing: border-box; }
        body { background: #1c1510; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; overflow: hidden; }
        
        .container { display: flex; gap: 25px; background: #2d2218; padding: 25px; border-radius: 16px; box-shadow: 0 15px 40px rgba(0,0,0,0.7); position: relative; z-index: 10; transition: transform 0.1s; }
        
        .shake { animation: screenShake 0.5s ease-in-out; }
        @keyframes screenShake {
            0%, 100% { transform: translate(0, 0); }
            10%, 30%, 50%, 70%, 90% { transform: translate(-10px, 0); }
            20%, 40%, 60%, 80% { transform: translate(10px, 0); }
        }

        canvas#board { background: #e2b072; border: 4px solid #5a3d28; border-radius: 8px; cursor: pointer; box-shadow: inset 0 0 20px rgba(0,0,0,0.2); }
        
        .panel { width: 240px; display: flex; flex-direction: column; justify-content: space-between; }
        h1 { color: #ffd700; margin: 0 0 5px 0; font-size: 26px; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
        .sub { color: #a08c78; font-size: 13px; margin-bottom: 20px; }
        .info-box { background: #1a130c; padding: 18px; border-radius: 10px; font-size: 14px; line-height: 1.7; border: 1px solid #3d2f22; }
        
        .btn { background: linear-gradient(135deg, #4a76a8, #2b4e75); color: white; border: none; padding: 14px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.4); }
        .foul-list { font-size: 12px; color: #8c7864; margin-top: 15px; }

        #fxCanvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 90; }

        /* 승리/패배 결과 팝업 */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(8px); display: flex; justify-content: center; align-items: center; z-index: 100; opacity: 0; pointer-events: none; transition: opacity 0.3s ease; }
        .modal-overlay.active { opacity: 1; pointer-events: auto; }

        .modal-card { text-align: center; background: #251b14; padding: 35px 50px; border-radius: 20px; border: 2px solid #ffd700; box-shadow: 0 0 50px rgba(255, 215, 0, 0.3); transform: scale(0.7); transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        .modal-overlay.active .modal-card { transform: scale(1); }

        .modal-card.defeat { border-color: #ff3333; box-shadow: 0 0 50px rgba(255, 51, 51, 0.4); }

        .banner-icon { font-size: 75px; margin-bottom: 10px; display: block; animation: bounce 1s infinite alternate; }
        @keyframes bounce { from { transform: translateY(0); } to { transform: translateY(-12px); } }

        .banner-title { font-size: 46px; font-weight: 900; letter-spacing: 3px; margin-bottom: 25px; }
        .victory-title { background: linear-gradient(to bottom, #ffe066, #ff9900); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 0 20px rgba(255, 215, 0, 0.5); }
        .defeat-title { background: linear-gradient(to bottom, #ff6666, #cc0000); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 0 20px rgba(255, 0, 0, 0.5); }

        .modal-btn { background: linear-gradient(135deg, #ffd700, #ff8c00); color: #1a130c; font-size: 18px; font-weight: bold; padding: 14px 40px; border: none; border-radius: 30px; cursor: pointer; box-shadow: 0 5px 20px rgba(255, 140, 0, 0.4); transition: 0.2s; }
        .modal-btn:hover { transform: scale(1.08); box-shadow: 0 8px 25px rgba(255, 140, 0, 0.6); }
        .modal-btn.defeat-btn { background: linear-gradient(135deg, #ff4d4d, #b30000); color: white; box-shadow: 0 5px 20px rgba(255, 0, 0, 0.4); }
    </style>
</head>
<body>
    <canvas id="fxCanvas"></canvas>

    <div class="container" id="mainContainer">
        <canvas id="board" width="600" height="600"></canvas>
        <div class="panel">
            <div>
                <h1>오목의 달인</h1>
                <div class="sub">[ 렌주룰 (Renju) 적용 ]</div>
                <div class="info-box">
                    <div>총 수: <b id="moveCount">0</b>수</div>
                    <div>턴: <b id="turn">흑돌 (플레이어)</b></div>
                    <hr style="border-color:#3d2f22; margin: 10px 0;">
                    <div id="status" style="color:#ff9d00; font-weight:bold;">당신의 차례입니다 (흑돌)</div>
                </div>
                <div class="foul-list">
                    ※ 흑돌 금수 규칙:<br>
                    - 3x3, 4x4 금지<br>
                    - 6목 이상(장목) 금지<br>
                    - 금수 위치 마우스 이동 시 <b>❌</b> 표시
                </div>
            </div>
            <button class="btn" onclick="resetGame()">게임 다시시작</button>
        </div>
    </div>

    <!-- 승리/패배 깔끔한 팝업 -->
    <div class="modal-overlay" id="resultModal">
        <div class="modal-card" id="modalCard">
            <span class="banner-icon" id="bannerIcon">🏆</span>
            <div class="banner-title" id="bannerTitle">VICTORY</div>
            <button class="modal-btn" id="modalBtn" onclick="resetGame()">다시 하기</button>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('board');
        const ctx = canvas.getContext('2d');
        const fxCanvas = document.getElementById('fxCanvas');
        const fxCtx = fxCanvas.getContext('2d');

        const margin = 40;
        const gridSize = (canvas.width - margin * 2) / 14;
        let gameState = {};
        let hoverCell = null;
        let fxParticles = [];
        let fxAnimationId = null;

        function resizeFxCanvas() {
            fxCanvas.width = window.innerWidth;
            fxCanvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resizeFxCanvas);
        resizeFxCanvas();

        function fetchState() {
            fetch('/api/state').then(res => res.json()).then(data => {
                gameState = data;
                draw();
                if (gameState.game_over) {
                    triggerGameOverEffect(gameState.winner);
                }
            });
        }

        function drawBoard() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = '#3d2612';
            ctx.lineWidth = 1;

            for (let i = 0; i < 15; i++) {
                ctx.beginPath();
                ctx.moveTo(margin + i * gridSize, margin);
                ctx.lineTo(margin + i * gridSize, canvas.height - margin);
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(margin, margin + i * gridSize);
                ctx.lineTo(canvas.width - margin, margin + i * gridSize);
                ctx.stroke();
            }

            const stars = [[3,3], [3,11], [7,7], [11,3], [11,11]];
            stars.forEach(([r, c]) => {
                ctx.beginPath();
                ctx.arc(margin + c * gridSize, margin + r * gridSize, 4, 0, Math.PI * 2);
                ctx.fillStyle = '#3d2612';
                ctx.fill();
            });
        }

        function drawStones() {
            if (!gameState.board) return;
            for (let r = 0; r < 15; r++) {
                for (let c = 0; c < 15; c++) {
                    const color = gameState.board[r][c];
                    if (color !== 0) {
                        const x = margin + c * gridSize;
                        const y = margin + r * gridSize;

                        ctx.beginPath();
                        ctx.arc(x + 2, y + 2, gridSize / 2 - 2, 0, Math.PI * 2);
                        ctx.fillStyle = 'rgba(0,0,0,0.35)';
                        ctx.fill();

                        const grad = ctx.createRadialGradient(x - 3, y - 3, 2, x, y, gridSize / 2);
                        if (color === 1) {
                            grad.addColorStop(0, '#666');
                            grad.addColorStop(1, '#111');
                        } else {
                            grad.addColorStop(0, '#fff');
                            grad.addColorStop(1, '#ccc');
                        }
                        ctx.beginPath();
                        ctx.arc(x, y, gridSize / 2 - 2, 0, Math.PI * 2);
                        ctx.fillStyle = grad;
                        ctx.fill();
                    }
                }
            }

            if (gameState.history && gameState.history.length > 0) {
                const [lastR, lastC] = gameState.history[gameState.history.length - 1];
                const x = margin + lastC * gridSize;
                const y = margin + lastR * gridSize;
                ctx.beginPath();
                ctx.arc(x, y, gridSize / 4, 0, Math.PI * 2);
                ctx.strokeStyle = '#e74c3c';
                ctx.lineWidth = 3;
                ctx.stroke();
            }

            if (gameState.winning_line && gameState.winning_line.length >= 5) {
                const pts = gameState.winning_line.map(([r, c]) => [margin + c * gridSize, margin + r * gridSize]);
                
                ctx.beginPath();
                ctx.moveTo(pts[0][0], pts[0][1]);
                for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
                ctx.strokeStyle = gameState.winner === 1 ? '#ffd700' : '#ff3333';
                ctx.lineWidth = 8;
                ctx.shadowColor = gameState.winner === 1 ? '#ffcc00' : '#ff0000';
                ctx.shadowBlur = 15;
                ctx.stroke();
                ctx.shadowBlur = 0;

                pts.forEach(([px, py]) => {
                    ctx.beginPath();
                    ctx.arc(px, py, gridSize / 2, 0, Math.PI * 2);
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 3;
                    ctx.stroke();
                });
            }
        }

        function drawHover() {
            if (!hoverCell || gameState.game_over || gameState.current_turn !== 1) return;
            const [r, c] = hoverCell;
            if (gameState.board[r][c] !== 0) return;

            const x = margin + c * gridSize;
            const y = margin + r * gridSize;
            const isFoul = gameState.forbidden_moves && gameState.forbidden_moves.some(([fr, fc]) => fr === r && fc === c);

            if (isFoul) {
                ctx.strokeStyle = '#ff3333';
                ctx.lineWidth = 4;
                const d = 10;
                ctx.beginPath();
                ctx.moveTo(x - d, y - d); ctx.lineTo(x + d, y + d);
                ctx.moveTo(x + d, y - d); ctx.lineTo(x - d, y + d);
                ctx.stroke();
            } else {
                ctx.beginPath();
                ctx.arc(x, y, gridSize / 2 - 2, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
                ctx.fill();
            }
        }

        function updateUI() {
            document.getElementById('moveCount').innerText = gameState.history ? gameState.history.length : 0;
            document.getElementById('turn').innerText = gameState.current_turn === 1 ? '흑돌 (플레이어)' : '백돌 (AI)';
            document.getElementById('status').innerText = gameState.status || '';
        }

        function draw() {
            drawBoard();
            drawStones();
            drawHover();
            updateUI();
        }

        function createConfetti() {
            fxParticles = [];
            const colors = ['#ffd700', '#ff0055', '#00e5ff', '#76ff03', '#ff9100', '#ffffff'];
            for (let i = 0; i < 150; i++) {
                fxParticles.push({
                    x: window.innerWidth / 2,
                    y: window.innerHeight / 2 - 100,
                    vx: (Math.random() - 0.5) * 18,
                    vy: (Math.random() - 0.7) * 18,
                    size: Math.random() * 8 + 4,
                    color: colors[Math.floor(Math.random() * colors.length)],
                    rotation: Math.random() * 360,
                    rSpeed: (Math.random() - 0.5) * 10,
                    gravity: 0.25,
                    opacity: 1
                });
            }
        }

        function createDefeatEmbers() {
            fxParticles = [];
            for (let i = 0; i < 100; i++) {
                fxParticles.push({
                    x: Math.random() * window.innerWidth,
                    y: window.innerHeight + 20,
                    vx: (Math.random() - 0.5) * 3,
                    vy: -Math.random() * 5 - 2,
                    size: Math.random() * 6 + 2,
                    color: '#ff3333',
                    gravity: 0,
                    opacity: Math.random() * 0.8 + 0.2
                });
            }
        }

        function renderFx() {
            fxCtx.clearRect(0, 0, fxCanvas.width, fxCanvas.height);
            fxParticles.forEach((p) => {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += p.gravity;
                if (p.rSpeed) p.rotation += p.rSpeed;

                fxCtx.save();
                fxCtx.translate(p.x, p.y);
                if (p.rotation) fxCtx.rotate((p.rotation * Math.PI) / 180);
                fxCtx.globalAlpha = p.opacity;
                fxCtx.fillStyle = p.color;
                fxCtx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
                fxCtx.restore();

                if (p.y > window.innerHeight + 50) {
                    p.opacity -= 0.02;
                }
            });

            fxParticles = fxParticles.filter(p => p.opacity > 0);
            if (fxParticles.length > 0) {
                fxAnimationId = requestAnimationFrame(renderFx);
            }
        }

        function triggerGameOverEffect(winner) {
            const modal = document.getElementById('resultModal');
            const card = document.getElementById('modalCard');
            const icon = document.getElementById('bannerIcon');
            const title = document.getElementById('bannerTitle');
            const btn = document.getElementById('modalBtn');
            const container = document.getElementById('mainContainer');

            if (winner === 1) {
                icon.innerText = '🏆';
                title.innerText = 'VICTORY';
                title.className = 'banner-title victory-title';
                btn.className = 'modal-btn';
                card.className = 'modal-card';
                
                createConfetti();
                renderFx();
            } else if (winner === 2) {
                container.classList.add('shake');
                setTimeout(() => container.classList.remove('shake'), 500);

                icon.innerText = '💀';
                title.innerText = 'DEFEAT';
                title.className = 'banner-title defeat-title';
                btn.className = 'modal-btn defeat-btn';
                card.className = 'modal-card defeat';

                createDefeatEmbers();
                renderFx();
            }

            setTimeout(() => {
                modal.classList.add('active');
            }, 500);
        }

        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const c = Math.round((x - margin) / gridSize);
            const r = Math.round((y - margin) / gridSize);

            if (r >= 0 && r < 15 && c >= 0 && c < 15) {
                hoverCell = [r, c];
            } else {
                hoverCell = null;
            }
            draw();
        });

        canvas.addEventListener('click', () => {
            if (!hoverCell || gameState.game_over || gameState.current_turn !== 1) return;
            const [r, c] = hoverCell;

            fetch('/api/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ r, c })
            }).then(res => res.json()).then(data => {
                gameState = data;
                draw();
                if (gameState.game_over) {
                    triggerGameOverEffect(gameState.winner);
                }
            });
        });

        function resetGame() {
            document.getElementById('resultModal').classList.remove('active');
            if (fxAnimationId) cancelAnimationFrame(fxAnimationId);
            fxCtx.clearRect(0, 0, fxCanvas.width, fxCanvas.height);

            fetch('/api/reset', { method: 'POST' }).then(res => res.json()).then(data => {
                gameState = data;
                draw();
            });
        }

        fetchState();
    </script>
</body>
</html>
"""

# ==========================================
# 5. 파이썬 웹 서버 실행기
# ==========================================
class ServerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif self.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(game.to_dict()).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        data = json.loads(body) if body else {}

        if self.path == '/api/move':
            r, c = data.get('r'), data.get('c')
            res = game.play_move(r, c)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/api/reset':
            game.reset()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(game.to_dict()).encode('utf-8'))

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    PORT = 8000
    print(f"🚀 오목 서버 시작 (Port {PORT})")
    with socketserver.TCPServer(("", PORT), ServerHandler) as httpd:
        httpd.serve_forever()