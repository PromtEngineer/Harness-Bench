FROM python:3.12-slim
LABEL version="2.3.0"
LABEL org.opencontainers.image.title="lattice-cli"
COPY . /app
RUN pip install /app
ENTRYPOINT ["lattice"]
