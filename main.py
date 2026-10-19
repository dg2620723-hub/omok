import sys
import math
import copy
import time
import pygame

# ==========================================
# 1. 게임 기본 설정 및 색상 정의
# ==========================================
BOARD_SIZE = 15          # 15x15 바둑판
GRID_SIZE = 44           # 격자 간격 (픽셀)
MARGIN = 50              # 바둑판 여백
PANEL_WIDTH = 240        # 우측 정보 패널 너비

SCREEN_WIDTH = MARGIN * 2 + GRID_SIZE * (BOARD_SIZE - 1) + PANEL_WIDTH
SCREEN_HEIGHT = MARGIN * 2 + GRID_SIZE * (BOARD_SIZE - 1)

# 돌 상태 값
EMPTY = 0
BLACK = 1
WHITE = 2

# 색상 정의 ('오목의 달인' 풍 테마)
COLOR_BG = (222, 184, 135)       # 따뜻한 원목 바탕색
COLOR_BOARD = (238, 197, 134)    # 바둑판 상판색
COLOR_GRID = (60, 40, 20)        # 격자선 색상
COLOR_PANEL = (45, 35, 25)       # 우측 패널 배경
COLOR_PANEL_TEXT = (230, 220, 200)

COLOR_BLACK = (20, 20, 20)
COLOR_WHITE = (245, 245, 245)
COLOR_LAST_MOVE = (235, 60, 60)   # 마지막 둔 돌 표시 (빨간 링)
COLOR_FOUL = (220, 50, 50)        # 금수 위치 표시 (X)
COLOR_HOVER = (100, 100, 100, 120)


# ==========================================
# 2. 렌주룰 엔진 (Renju Rule Engine)
# ==========================================
class RenjuEngine:
    """
    렌주룰 규칙 판정 클래스
    - 흑(BLACK): 3x3 금지, 4x4 금지, 장목(6목 이상) 금지. 오직 정확히 5목만 승리.
    - 백(WHITE): 금수 없음. 3x3, 4x4, 6목 이상 모두 허용 (6목 이상도 승리).
    """

    DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]

    @staticmethod
    def count_consecutive(board, r, c, dr, dc, color):
        """특정 방향(dr, dc)으로 연속된 돌의 개수를 측정"""
        count = 0
        nr, nc = r + dr, c + dc
        while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == color:
            count += 1
            nr += dr
            nc += dc
        return count

    @classmethod
    def get_line_length(cls, board, r, c, dr, dc, color):
        """(r, c)에 돌을 두었을 때 해당 방향의 총 연속 돌 수"""
        forward = cls.count_consecutive(board, r, c, dr, dc, color)
        backward = cls.count_consecutive(board, r, c, -dr, -dc, color)
        return forward + backward + 1

    @classmethod
    def is_exact_five(cls, board, r, c, color):
        """정확히 5목이 완성되는지 확인"""
        for dr, dc in cls.DIRECTIONS:
            if cls.get_line_length(board, r, c, dr, dc, color) == 5:
                return True
        return False

    @classmethod
    def is_overline(cls, board, r, c, color):
        """6목 이상(장목)인지 확인"""
        for dr, dc in cls.DIRECTIONS:
            if cls.get_line_length(board, r, c, dr, dc, color) >= 6:
                return True
        return False

    @classmethod
    def is_open_three(cls, board, r, c, dr, dc, color):
        """
        간략화된 열린 삼(Open Three / 활삼) 판정
        (한 수를 더 두어 닫히지 않은 4가 될 수 있는 패턴)
        """
        temp_board = copy.deepcopy(board)
        temp_board[r][c] = color

        # 양방향으로 탐색하며 열린 삼 패턴 검사
        line = []
        for i in range(-4, 5):
            nr, nc = r + dr * i, c + dc * i
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                line.append(temp_board[nr][nc])
            else:
                line.append(-1) # 경계 밖

        # 9칸 서브 스트링에서 '01110', '010110', '011010' 패턴 탐색
        center = 4
        # 주변 6~7칸 범위 패턴 체크
        for window_size in [5, 6]:
            for start in range(max(0, center - window_size + 1), min(len(line) - window_size + 1, center + 1)):
                sub = line[start:start + window_size]
                # 열린 삼 기본 조건: 양 끝이 빈칸(0)이고 내부에 color가 3개 포함
                if sub[0] == EMPTY and sub[-1] == EMPTY and sub.count(color) == 3 and sub.count(EMPTY) == window_size - 3 and sub.count(3 - color) == 0 and sub.count(-1) == 0:
                    return True
        return False

    @classmethod
    def is_four(cls, board, r, c, dr, dc, color):
        """사가 형성되는지 판정 (닫힌 사 포함)"""
        temp_board = copy.deepcopy(board)
        temp_board[r][c] = color

        line = []
        for i in range(-4, 5):
            nr, nc = r + dr * i, c + dc * i
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                line.append(temp_board[nr][nc])
            else:
                line.append(-1)

        center = 4
        for window_size in [5]:
            for start in range(max(0, center - window_size + 1), min(len(line) - window_size + 1, center + 1)):
                sub = line[start:start + window_size]
                if sub.count(color) == 4 and sub.count(EMPTY) == 1 and sub.count(-1) == 0 and sub.count(3 - color) == 0:
                    return True
        return False

    @classmethod
    def is_forbidden_move(cls, board, r, c, color):
        """
        흑돌의 금수 여부 판정 (3x3, 4x4, 6목 이상)
        단, 금수가 되더라도 동시에 5목이 완성되면 승리이므로 금수가 아님.
        """
        if color != BLACK:
            return False  # 백은 금수가 없음

        if board[r][c] != EMPTY:
            return True

        # 5목 완성 시 금수 예외 적용 (즉시 승리)
        if cls.is_exact_five(board, r, c, BLACK):
            return False

        # 1. 장목(6목 이상) 체크
        if cls.is_overline(board, r, c, BLACK):
            return True

        # 2. 3x3 (쌍삼) 체크
        open_three_count = 0
        for dr, dc in cls.DIRECTIONS:
            if cls.is_open_three(board, r, c, dr, dc, BLACK):
                open_three_count += 1
                if open_three_count >= 2:
                    return True

        # 3. 4x4 (쌍사) 체크
        four_count = 0
        for dr, dc in cls.DIRECTIONS:
            if cls.is_four(board, r, c, dr, dc, BLACK):
                four_count += 1
                if four_count >= 2:
                    return True

        return False

    @classmethod
    def check_winner(cls, board, last_r, last_c):
        """승리 조건 판정"""
        if last_r is None or last_c is None:
            return EMPTY

        color = board[last_r][last_c]
        if color == EMPTY:
            return EMPTY

        for dr, dc in cls.DIRECTIONS:
            length = cls.get_line_length(board, last_r, last_c, dr, dc, color)
            if color == BLACK:
                if length == 5: # 흑은 정확히 5목만 인정
                    return BLACK
            elif color == WHITE:
                if length >= 5: # 백은 5목 이상(장목 포함) 승리
                    return WHITE
        return EMPTY


# ==========================================
# 3. AI 인터페이스 및 기본 AI 구현
# ==========================================
class BaseAI:
    """
    [AI 확장 인터페이스]
    나중에 더 강력한 AI(AlphaZero, Minimax, MCTS, 신경망 등)를 연결할 때
    이 클래스를 상속받아 `get_move` 함수만 구현하면 됩니다.
    """
    def __init__(self, color):
        self.color = color

    def get_move(self, board, history):
        """
        :param board: 15x15 2D 리스트 (0: empty, 1: black, 2: white)
        :param history: 지금까지 둔 돌들의 위치 리스트 [(r, c), ...]
        :return: (r, c) 착수할 좌표 튜플
        """
        raise NotImplementedError("AI 착수 로직을 구현해야 합니다.")


class SmartGomokuAI(BaseAI):
    """
    기본 탑재된 미니맥스/휴리스틱 기반 오목 AI
    - 공격/방어 가중치를 계산하여 최적의 착수점을 선택합니다.
    """
    def __init__(self, color):
        super().__init__(color)

    def evaluate_point(self, board, r, c, color):
        """특정 위치의 가치 평가"""
        score = 0
        opponent = 3 - color

        for dr, dc in RenjuEngine.DIRECTIONS:
            # 내 돌 기여도
            my_len = RenjuEngine.get_line_length(board, r, c, dr, dc, color)
            if my_len >= 5: score += 100000
            elif my_len == 4: score += 5000
            elif my_len == 3: score += 500

            # 상대방 방어 기여도 (상대 흐름 끊기)
            opp_len = RenjuEngine.get_line_length(board, r, c, dr, dc, opponent)
            if opp_len >= 5: score += 80000  # 상대 5목 즉시 방어
            elif opp_len == 4: score += 4000
            elif opp_len == 3: score += 300

        # 중앙 선호 가중치
        dist_from_center = abs(r - 7) + abs(c - 7)
        score += (14 - dist_from_center) * 5

        return score

    def get_move(self, board, history):
        # 첫 번째 수라면 중앙 착수
        if not history:
            return (7, 7)

        best_score = -1
        best_moves = []

        # 바둑판 전체 검색 (이미 돌이 있는 주변 영역 위주 탐색)
        candidate_positions = set()
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] != EMPTY:
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == EMPTY:
                                # 흑 AI일 경우 금수 위치 제외
                                if self.color == BLACK and RenjuEngine.is_forbidden_move(board, nr, nc, BLACK):
                                    continue
                                candidate_positions.add((nr, nc))

        if not candidate_positions:
            candidate_positions.add((7, 7))

        for r, c in candidate_positions:
            score = self.evaluate_point(board, r, c, self.color)
            if score > best_score:
                best_score = score
                best_moves = [(r, c)]
            elif score == best_score:
                best_moves.append((r, c))

        import random
        return random.choice(best_moves) if best_moves else (7, 7)


# ==========================================
# 4. Pygame UI & 렌더링 클래스 ('오목의 달인' 스타일)
# ==========================================
class GomokuGameApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("오목의 달인 (Master of Gomoku) - Renju Rules")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # 폰트 설정
        # 여러 폰트를 순서대로 탐색하며, 없을 경우 기본 폰트로 자동 대체
        font_list = ["malgungothic", "nanumgothic", "arial", None]
        self.font_title = pygame.font.SysFont(font_list, 24, bold=True)
        self.font_status = pygame.font.SysFont(font_list, 18, bold=True)
        self.font_small = pygame.font.SysFont(font_list, 14)

        # 게임 상태 변수
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.current_turn = BLACK  # 플레이어: BLACK, AI: WHITE
        self.history = []          # [(r, c), ...]
        self.winner = EMPTY
        self.game_over = False
        self.status_message = "당신의 차례입니다 (흑돌)"

        # AI 탑재 (백돌)
        self.ai = SmartGomokuAI(color=WHITE)
        self.is_ai_thinking = False

    def reset_game(self):
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.current_turn = BLACK
        self.history = []
        self.winner = EMPTY
        self.game_over = False
        self.is_ai_thinking = False
        self.status_message = "당신의 차례입니다 (흑돌)"

    def board_to_screen(self, r, c):
        """바둑판 좌표(r, c) -> 화면 피셀 좌표(x, y) 변환"""
        x = MARGIN + c * GRID_SIZE
        y = MARGIN + r * GRID_SIZE
        return x, y

    def screen_to_board(self, x, y):
        """화면 피셀 좌표(x, y) -> 바둑판 좌표(r, c) 변환"""
        c = round((x - MARGIN) / GRID_SIZE)
        r = round((y - MARGIN) / GRID_SIZE)
        if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
            return r, c
        return None, None

    def handle_click(self, pos):
        if self.game_over or self.current_turn != BLACK or self.is_ai_thinking:
            return

        r, c = self.screen_to_board(pos[0], pos[1])
        if r is not None and c is not None:
            if self.board[r][c] == EMPTY:
                # 흑돌 금수 규칙 체크
                if RenjuEngine.is_forbidden_move(self.board, r, c, BLACK):
                    self.status_message = "⚠️ 금수 위치입니다! (3x3, 4x4, 장목)"
                    return

                # 착수 실행
                self.place_stone(r, c, BLACK)

    def place_stone(self, r, c, color):
        self.board[r][c] = color
        self.history.append((r, c))

        # 승리 검사
        winner = RenjuEngine.check_winner(self.board, r, c)
        if winner != EMPTY:
            self.winner = winner
            self.game_over = True
            self.status_message = "🎉 흑돌(플레이어) 승리!" if winner == BLACK else "🤖 백돌(AI) 승리!"
            return

        # 무승부 검사
        if len(self.history) == BOARD_SIZE * BOARD_SIZE:
            self.game_over = True
            self.status_message = "🤝 무승부입니다!"
            return

        # 턴 교체
        self.current_turn = 3 - color
        if self.current_turn == WHITE:
            self.status_message = "🤖 AI가 생각 중입니다..."

    def ai_turn(self):
        """AI 착수 진행 함수"""
        if self.game_over or self.current_turn != WHITE:
            return

        self.is_ai_thinking = True
        pygame.display.flip()
        
        # 딜레이 효과 (자연스러운 연출)
        pygame.time.delay(300)

        # AI 좌표 연산 실행
        r, c = self.ai.get_move(self.board, self.history)
        self.place_stone(r, c, WHITE)
        
        if not self.game_over:
            self.status_message = "당신의 차례입니다 (흑돌)"
        self.is_ai_thinking = False

    def draw_board(self):
        """ 고급 원목 바둑판 및 격자선 그리드 그리기"""
        # 바둑판 외곽 나무 테두리
        board_rect = pygame.Rect(
            MARGIN - 25, MARGIN - 25,
            (BOARD_SIZE - 1) * GRID_SIZE + 50,
            (BOARD_SIZE - 1) * GRID_SIZE + 50
        )
        pygame.draw.rect(self.screen, COLOR_BOARD, board_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_GRID, board_rect, width=3, border_radius=8)

        # 격자선
        for i in range(BOARD_SIZE):
            start_x, start_y = self.board_to_screen(i, 0)
            end_x, end_y = self.board_to_screen(i, BOARD_SIZE - 1)
            pygame.draw.line(self.screen, COLOR_GRID, (start_x, start_y), (end_x, end_y), 1)

            start_x, start_y = self.board_to_screen(0, i)
            end_x, end_y = self.board_to_screen(BOARD_SIZE - 1, i)
            pygame.draw.line(self.screen, COLOR_GRID, (start_x, start_y), (end_x, end_y), 1)

        # 화점(Star Points) 표시 (4개의 모서리 및 천원)
        star_points = [(3, 3), (3, 11), (7, 7), (11, 3), (11, 11)]
        for r, c in star_points:
            x, y = self.board_to_screen(r, c)
            pygame.draw.circle(self.screen, COLOR_GRID, (x, y), 4)

    def draw_stones(self):
        """3D 입체 그라데이션 오목돌 입히기"""
        radius = GRID_SIZE // 2 - 2

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                color = self.board[r][c]
                if color != EMPTY:
                    x, y = self.board_to_screen(r, c)
                    
                    # 돌 그림자 효과
                    pygame.draw.circle(self.screen, (100, 80, 60), (x + 2, y + 2), radius)

                    if color == BLACK:
                        # 흑돌 입체 하이라이트
                        pygame.draw.circle(self.screen, COLOR_BLACK, (x, y), radius)
                        pygame.draw.circle(self.screen, (70, 70, 70), (x - 3, y - 3), radius // 3)
                    elif color == WHITE:
                        # 백돌 입체 하이라이트
                        pygame.draw.circle(self.screen, COLOR_WHITE, (x, y), radius)
                        pygame.draw.circle(self.screen, (200, 200, 200), (x, y), radius, width=1)
                        pygame.draw.circle(self.screen, (255, 255, 255), (x - 3, y - 3), radius // 3)

        # 마지막 착수점 붉은색 링 가이드
        if self.history:
            last_r, last_c = self.history[-1]
            lx, ly = self.board_to_screen(last_r, last_c)
            pygame.draw.circle(self.screen, COLOR_LAST_MOVE, (lx, ly), radius // 2, width=2)

    def draw_hover_and_fouls(self):
        """마우스 호버 가이드 및 흑돌 금수(X) 위치 표시"""
        if self.game_over or self.current_turn != BLACK:
            return

        mx, my = pygame.mouse.get_pos()
        r, c = self.screen_to_board(mx, my)

        if r is not None and c is not None and self.board[r][c] == EMPTY:
            x, y = self.board_to_screen(r, c)

            # 금수 위치 체크
            if RenjuEngine.is_forbidden_move(self.board, r, c, BLACK):
                # 붉은색 X 표시
                d = 8
                pygame.draw.line(self.screen, COLOR_FOUL, (x - d, y - d), (x + d, y + d), 3)
                pygame.draw.line(self.screen, COLOR_FOUL, (x + d, y - d), (x - d, y + d), 3)
            else:
                # 착수 가능 투명 흑돌 호버 표시
                s = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(s, (0, 0, 0, 80), (GRID_SIZE // 2, GRID_SIZE // 2), GRID_SIZE // 2 - 2)
                self.screen.blit(s, (x - GRID_SIZE // 2, y - GRID_SIZE // 2))

    def draw_panel(self):
        """우측 스코어/게임 상태 정보 패널 렌더링"""
        panel_x = MARGIN * 2 + (BOARD_SIZE - 1) * GRID_SIZE
        panel_rect = pygame.Rect(panel_x, 0, PANEL_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect)

        # 타이틀
        title_surf = self.font_title.render("오목의 달인", True, (255, 215, 0))
        self.screen.blit(title_surf, (panel_x + 20, 30))

        rule_surf = self.font_small.render("[ 렌주룰 (Renju) 적용 ]", True, (180, 180, 180))
        self.screen.blit(rule_surf, (panel_x + 20, 65))

        # 현재 수 정보
        move_count_surf = self.font_status.render(f"총 수: {len(self.history)}수", True, COLOR_PANEL_TEXT)
        self.screen.blit(move_count_surf, (panel_x + 20, 120))

        # Turn 표시
        turn_str = "흑돌 (플레이어)" if self.current_turn == BLACK else "백돌 (AI)"
        turn_surf = self.font_status.render(f"턴: {turn_str}", True, COLOR_PANEL_TEXT)
        self.screen.blit(turn_surf, (panel_x + 20, 155))

        # 게임 진행 상태 메세지
        status_surf = self.font_small.render(self.status_message, True, (255, 128, 0) if "금수" in self.status_message else COLOR_PANEL_TEXT)
        self.screen.blit(status_surf, (panel_x + 20, 210))

        # 금수 설명 정보
        foul_info1 = self.font_small.render("※ 흑돌 금수 규칙:", True, (150, 150, 150))
        foul_info2 = self.font_small.render("- 3x3, 4x4 금지", True, (150, 150, 150))
        foul_info3 = self.font_small.render("- 6목 이상(장목) 금지", True, (150, 150, 150))
        self.screen.blit(foul_info1, (panel_x + 20, 280))
        self.screen.blit(foul_info2, (panel_x + 20, 305))
        self.screen.blit(foul_info3, (panel_x + 20, 325))

        # 재시작 버튼
        self.btn_rect = pygame.Rect(panel_x + 20, SCREEN_HEIGHT - 80, PANEL_WIDTH - 40, 45)
        pygame.draw.rect(self.screen, (70, 130, 180), self.btn_rect, border_radius=6)
        btn_surf = self.font_status.render("게임 다시시작 (R)", True, (255, 255, 255))
        self.screen.blit(btn_surf, (panel_x + 35, SCREEN_HEIGHT - 70))

    def run(self):
        """메인 게임 루프"""
        running = True
        while running:
            self.clock.tick(60)

            # 1. 이벤트 처리
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # 다시시작 버튼 클릭 검사
                    if hasattr(self, 'btn_rect') and self.btn_rect.collidepoint(event.pos):
                        self.reset_game()
                    else:
                        self.handle_click(event.pos)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # 'R' 키로 리셋
                        self.reset_game()

            # 2. AI 턴 실행
            if self.current_turn == WHITE and not self.game_over and not self.is_ai_thinking:
                self.ai_turn()

            # 3. 화면 그리기
            self.screen.fill(COLOR_BG)
            self.draw_board()
            self.draw_stones()
            self.draw_hover_and_fouls()
            self.draw_panel()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


# ==========================================
# 5. 실행 진입점
# ==========================================
if __name__ == "__main__":
    app = GomokuGameApp()
    app.run()