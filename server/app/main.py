from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, groups, subscriptions, links

app = FastAPI(title="Price Monitoring API")

# Настройка CORS (чтобы фронтенд мог стучаться)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(subscriptions.router)
app.include_router(links.router)

@app.get("/")
def read_root():
    return {"message": "Сервер работает!"}