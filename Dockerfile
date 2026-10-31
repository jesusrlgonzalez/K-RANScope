FROM python:3.11-slim
WORKDIR /work
COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH=/work/src
USER 65532:65532
EXPOSE 8000
CMD ["uvicorn","i35.api:app","--host","0.0.0.0","--port","8000"]
