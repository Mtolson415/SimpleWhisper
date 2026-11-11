FROM python:3.14.0-slim@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e
WORKDIR /app
COPY service.py ./
COPY audio_segments.py ./
COPY transcript_quality.py ./
COPY rolling_audio.py ./
COPY revision_span.py ./
COPY locked_target.py ./
USER 65534:65534
EXPOSE 8080
CMD ["python", "-B", "service.py"]
