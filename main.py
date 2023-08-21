import asyncio

from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from src.routes import auth, contacts
from starlette.middleware.cors import CORSMiddleware
import uvicorn
app = FastAPI()

app.include_router(auth.router)
app.include_router(contacts.router, prefix='/api')

app.mount("/static", StaticFiles(directory="src/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def tack():
    await asyncio.sleep(3)
    print("Send email")
    return True

@app.get("/")
async def read_root(background_task: BackgroundTasks):
    background_task.add_task(tack)
    return {"message": "CONTACTS"}


if __name__ =='__main__':
    uvicorn.run("main:app", host="localhost", reload=True, log_level="info")