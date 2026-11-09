import sys
import os
import pygame
import requests

# 部署至 Render 的服務網址
API_BASE_URL = "https://two0261109.onrender.com"
# API_BASE_URL = "http://127.0.0.1:8000"

COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)   # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色
COLOR_PANEL_BG = (30, 30, 32)
COLOR_LINE = (80, 80, 80)

pygame.init()
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)
panel_font = pygame.font.SysFont("Arial", 20, bold=True)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.hard_mode = False
        self.history_words = []
        self.stats = {"total_games": 0, "wins": 0, "win_rate": 0}
        # 畫面提示更新為 Ctrl+R 與 Ctrl+H
        self.message = "Press ENTER to submit | Ctrl+R to restart | Ctrl+H for Hard Mode"
        self.start_new_game()

    def start_new_game(self):
        """ 向 FastAPI 請求開局 """
        try:
            payload = {"hard_mode": self.hard_mode}
            res = requests.post(f"{API_BASE_URL}/api/new-game", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.history_words = []
                if "stats" in data:
                    self.stats = data["stats"]
                self.message = "New game started! (6 tries left)"
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def submit_guess(self):
        """ 發送猜測 """
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                self.history_words.append(guess_word)
                if "stats" in data:
                    self.stats = data["stats"]

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press Ctrl+R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    tries_left = data.get("attempts_left", 6 - self.row)
                    
                    if self.row == 6 or tries_left == 0:
                        target = data.get("target_word", "UNKNOWN")
                        self.message = f"Game Over! The word was {target}. Press Ctrl+R to restart."
                        self.game_over = True
                    else:
                        self.message = f"Keep guessing! ({tries_left} tries left)"
            else:
                err_detail = res.json().get("detail", "")
                if "dictionary" in err_detail or res.status_code == 400:
                    if "Hard Mode" in err_detail:
                        self.message = "Hard Mode: Must use revealed hint at green position"
                    else:
                        self.message = "Not in word list!"
                else:
                    self.message = err_detail
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        # 檢查是否按下 Ctrl 鍵 (Windows/Linux 為 KMOD_CTRL，Mac 為 KMOD_META)
        mods = pygame.key.get_mods()
        ctrl_pressed = bool(mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META)

        # 1. 組合鍵處理 (Ctrl + R 重開, Ctrl + H 切換 Hard Mode)
        if ctrl_pressed:
            if event.key == pygame.K_r:
                self.start_new_game()
                return
            elif event.key == pygame.K_h:
                self.hard_mode = not self.hard_mode
                self.start_new_game()
                return

        # 2. 退格鍵 (Backspace)
        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
            return

        # 3. 提交鍵 (Enter)
        if event.key == pygame.K_RETURN:
            self.submit_guess()
            return

        # 4. 遊戲結束後不接收英文字母輸入
        if self.game_over:
            return

        # 5. 一般英文字母輸入 (包含 R、H 等所有字母)
        if event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        
        # 1. 主遊戲網格 (6x5)
        margin_x, margin_y = 50, 50
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, COLOR_LINE, rect, width=2, border_radius=4)

                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 2. 右側面板 (x: 500 ~ 700)
        pygame.draw.line(surface, COLOR_LINE, (500, 0), (500, HEIGHT), 2)
        panel_rect = pygame.Rect(500, 0, 200, HEIGHT)
        pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect)

        # 右上角模式狀態顯示
        mode_text = "Mode: HARD" if self.hard_mode else "Mode: Normal"
        mode_color = (235, 87, 87) if self.hard_mode else (87, 200, 235)
        mode_surf = panel_font.render(mode_text, True, mode_color)
        surface.blit(mode_surf, (515, 20))

        # 歷史單字列表
        hist_title = small_font.render("History Guesses:", True, COLOR_TEXT)
        surface.blit(hist_title, (515, 60))
        for idx, word in enumerate(self.history_words):
            w_surf = small_font.render(f"{idx+1}. {word}", True, COLOR_TEXT)
            surface.blit(w_surf, (525, 90 + idx * 25))

        # 快捷鍵提示區域 (明確提示 Ctrl+R 與 Ctrl+H)
        help_y = 270
        pygame.draw.line(surface, COLOR_LINE, (510, help_y), (690, help_y), 1)
        surface.blit(panel_font.render("Shortcuts", True, (200, 200, 200)), (515, help_y + 8))
        surface.blit(small_font.render("Ctrl + R : Restart", True, (160, 160, 160)), (515, help_y + 35))
        surface.blit(small_font.render("Ctrl + H : Toggle Hard", True, (160, 160, 160)), (515, help_y + 55))

        # 戰績統計顯示
        stat_y = 360
        pygame.draw.line(surface, COLOR_LINE, (510, stat_y), (690, stat_y), 1)
        
        stat_title = panel_font.render("Statistics", True, COLOR_TEXT)
        surface.blit(stat_title, (515, stat_y + 8))
        
        tot_str = f"Total Games: {self.stats['total_games']}"
        win_str = f"Wins: {self.stats['wins']}"
        rate_str = f"Win Rate: {self.stats['win_rate']}%"
        
        surface.blit(small_font.render(tot_str, True, COLOR_TEXT), (515, stat_y + 35))
        surface.blit(small_font.render(win_str, True, COLOR_TEXT), (515, stat_y + 60))
        surface.blit(small_font.render(rate_str, True, COLOR_TEXT), (515, stat_y + 85))

        # 3. 底部提示訊息
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(250, HEIGHT - 35))
        surface.blit(msg_surface, msg_rect)

def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
