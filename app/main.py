import os

from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.modules.stocks.router.stock_router import stock_router, market_router
from app.modules.news.router.news_router import stock_router as news_router
from .logging_setup import setup_logging
from app.modules.users.router import user_router
from app.modules.auth.router import auth_router
from app.modules.markets.router import markets_router as global_markets_router
from app.modules.watchlist.alert_router import price_alert_router
from app.modules.watchlist.router import watchlist_router
from app.modules.cam_ai.router import conversation_router
import logging

load_dotenv()



app = FastAPI()

setup_logging()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origins=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(stock_router)
app.include_router(news_router)
app.include_router(market_router)
app.include_router(global_markets_router)
app.include_router(watchlist_router)
app.include_router(price_alert_router)
app.include_router(conversation_router)

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def read_root():
    return {"Hello": "World"}
