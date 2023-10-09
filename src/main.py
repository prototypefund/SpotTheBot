#!/usr/bin/env python3
import uvicorn

import frontend
from fastapi import FastAPI

app = FastAPI()
frontend.run(app)


def main() -> None:
    # `uvicorn main:app --reload --log-level debug --port 8000 --host 0.0.0.0`
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="debug", reload=True)


if __name__ == '__main__':
    main()