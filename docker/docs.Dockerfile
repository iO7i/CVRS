FROM python:3.13-slim
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir ".[adoption,docs]"
RUN useradd --create-home runner
USER runner
ENTRYPOINT ["cvrs"]
CMD ["doctor"]
