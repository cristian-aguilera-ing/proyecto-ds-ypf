FROM python:3.14-slim
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --chown=app:app control_remoto/servidor.py .
USER app
ENV PYTHONUNBUFFERED=1
EXPOSE 8091
CMD ["python", "servidor.py"]
