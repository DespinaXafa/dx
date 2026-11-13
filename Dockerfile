# Hugging Face Spaces (Docker SDK) — βλ. README «Δημοσίευση»
FROM python:3.11-slim
RUN useradd -m -u 1000 user
WORKDIR /app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
USER user
ENV HF_HOME=/app/.cache PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
