from fastapi import FastAPI, HTTPException
import uvicorn
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()


app = FastAPI()
@app.get("/")
def index():
    return "데이브 더 다이브 게임 가이드 입니다"

@app.post("/generate-response/")
async def generate_response(situation: str, user_input: str):
    if situation == "item_shop":
        system_content = "당신은 게임 내 아이템 상점의 게임 가이드입니다. 사용자가 아이템 구매에 대해 문의할 때 친절하고 유용한 정보를 제공하세요."
    elif situation == "quest_guide":
        system_content = "당신은 게임 내 퀘스트를 안내하는 게임 가이드입니다. 사용자가 퀘스트에 대해 문의할 때 명확하고 상세한 지침을 제공하세요."
    elif situation == "npc_guide":
        system_content = "당신은 게임 내 동료 NPC들을 소개하는 게임 가이드입니다. 사용자가 새로운 동료에 대해 문의할 때 그들의 특성과 이야기를 생생하게 전달하세요."
    else:
        raise HTTPException(status_code=400, detail="알 수 없는 상황입니다.")
    user_content = user_input

    completion = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ],
        temperature=0.5,
        max_tokens=150
    )
    return completion.choices[0].message.content

# Uvicorn 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)