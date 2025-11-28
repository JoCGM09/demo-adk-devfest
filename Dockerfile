# 1. Usar Python 3.12 como base, ya que es compatible con asyncpg
FROM python:3.12-slim

# Instala uv
RUN pip install --no-cache-dir uv==0.7.13

WORKDIR /app

COPY . .

# 2. INSTALAR HERRAMIENTAS DE COMPILACIÓN
# Esto es esencial para compilar asyncpg y otros paquetes que usan extensiones C.
# --no-install-recommends: reduce el tamaño de la imagen.
# rm -rf /var/lib/apt/lists/*: limpia la caché de apt para reducir el tamaño de la capa.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Opcional: crea el entorno virtual (.venv)
RUN uv venv --seed

# 3. Instala las dependencias en el venv (esto ahora encontrará 'cc')
# Usamos `uv pip install .` para que lea tu pyproject.toml
RUN uv pip install .

EXPOSE 8080

# 4. CMD: Ejecutar uvicorn desde el entorno virtual para asegurar el PATH
CMD ["/app/.venv/bin/uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]