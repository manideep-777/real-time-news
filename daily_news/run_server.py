from waitress import serve 
# import uvicorn
from main import app


if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=5000)
    serve(app, host="0.0.0.0", port=5000)