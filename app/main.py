from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from app.modules.stocks.router.stock_router import stock_router
from app.modules.news.router.news_router import stock_router as news_router

load_dotenv()

app = FastAPI()
app.include_router(stock_router)
app.include_router(news_router)

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/")
def read_root():
    return {"Hello": "World"}