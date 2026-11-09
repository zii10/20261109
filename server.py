import os
import random
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

# 任務三：戰績統計（全域變數）
stats = {
    "total_games": 0,
    "wins": 0
}

# 記憶體儲存遊戲狀態
games_db: Dict[str, dict] = {}


@app.post("/api/new-game")
def start_new_game(hard_mode: bool = Body(False, embed=True)):
    """ 任務四：允許接收 hard_mode 參數 """
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    
    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": hard_mode,
        "confirmed_green": [None] * 5  # 記錄綠色位置
    }
    
    stats["total_games"] += 1

    return {
        "game_id": game_id,
        "message": "New game started!",
        "hard_mode": hard_mode,
        "stats": get_stats_data()
    }


@app.post("/api/guess")
def process_guess(
    game_id: str = Body(...),
    guess: str = Body(...)
):
    guess_word = guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")

    game = games_db[game_id]

    if len(guess_word) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：字典庫檢查
    if guess_word not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    # 任務四：Hard Mode 邏輯驗證
    if game["hard_mode"]:
        for i in range(5):
            req_char = game["confirmed_green"][i]
            if req_char is not None and guess_word[i] != req_char:
                raise HTTPException(
                    status_code=400, 
                    detail="Hard Mode: Must use revealed hint at green position"
                )

    target = game["target"]
    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 標記綠色 correct 並更新 Hard Mode 鎖定位置
    for i in range(5):
        if guess_word[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess_word[i]] -= 1
            game["confirmed_green"][i] = guess_word[i]

    # 標記黃色 present
    for i in range(5):
        if feedback[i] != "correct" and guess_word[i] in target:
            if target_letter_counts[guess_word[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess_word[i]] -= 1

    game["attempts"] += 1
    is_correct = (guess_word == target)
    
    # 判斷遊戲結束
    target_word_reveal = None
    if is_correct:
        game["status"] = "WON"
        stats["wins"] += 1
        target_word_reveal = target
    elif game["attempts"] >= 6:
        game["status"] = "LOST"
        target_word_reveal = target  # 任務一：第 6 次猜錯時回傳 target_word

    return {
        "guess": guess_word,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": target_word_reveal,  # 未結束為 None，結束為 target
        "attempts_left": 6 - game["attempts"],
        "stats": get_stats_data()
    }


def get_stats_data():
    total = stats["total_games"]
    wins = stats["wins"]
    win_rate = round((wins / total * 100)) if total > 0 else 0
    return {
        "total_games": total,
        "wins": wins,
        "win_rate": win_rate
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
