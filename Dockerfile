FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md pulsar.py ./
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

LABEL org.opencontainers.image.title="pulsar-psr"
LABEL org.opencontainers.image.description="Parser y herramientas para el formato PULSAR (.psr)"
LABEL org.opencontainers.image.source="https://github.com/jeironpro/pulsar"
LABEL org.opencontainers.image.licenses="MIT"

COPY --from=builder /install /usr/local
ENTRYPOINT ["psr"]
CMD ["--help"]
