from fastapi import FastAPI
from app.routes.chat import router
app=FastAPI();app.include_router(router)
@app.get('/health')
def h(): return {'status':'ok','version':'Sprint2'}
