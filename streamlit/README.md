# UrbanGuard AI Streamlit dashboard

This is an isolated Streamlit client for the existing UrbanGuard FastAPI service. It does not replace or modify the Next.js dashboard.

## Run locally

From the repository root:

```powershell
python -m venv .streamlit-venv
.streamlit-venv\Scripts\Activate.ps1
pip install -r streamlit/requirements.txt
$env:URBANGUARD_API_URL="http://localhost:8000"
streamlit run streamlit/streamlit_app.py
```

Open `http://localhost:8501`.

## Share through Streamlit Community Cloud

1. Push this repository to GitHub.
2. Create a Streamlit Community Cloud app using `streamlit/streamlit_app.py` as the main file.
3. Add this secret under **Settings > Secrets**:

```toml
URBANGUARD_API_URL = "https://your-public-fastapi-url"
```

The FastAPI service must be reachable from the public Streamlit instance and allow the Streamlit app's origin through CORS. For a private/local backend, use a tunnel or deploy both services within the same controlled environment. Do not place credentials or personal data in the Streamlit app.
