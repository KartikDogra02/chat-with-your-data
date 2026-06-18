from fastapi import FastAPI

app = FastAPI(title="Chat With Your Data")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "chat_with_your_data.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )