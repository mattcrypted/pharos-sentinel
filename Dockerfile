# Sentinel UI — read-only on-chain risk gate (Foundry cast + Python).
# Keyless by design: it only runs `cast call`/`code`/`storage`, never `cast send`.
FROM python:3.12-slim

# Foundry's installer needs curl + git + TLS roots.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Foundry (cast/forge) — the engine's mandated execution path.
RUN curl -L https://foundry.paradigm.xyz | bash
ENV PATH="/root/.foundry/bin:${PATH}"
RUN foundryup

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Hosts inject $PORT; bind all interfaces inside the container.
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["python", "sentinel_ui.py"]
