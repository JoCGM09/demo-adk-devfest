# 1. Base compatible con asyncpg (Python 3.12)
FROM python:3.12-slim

WORKDIR /app

COPY . .

# 2. INSTALAR HERRAMIENTAS DE COMPILACIÓN y dependencias
RUN apt-get update && apt-get install -y --no-install-recommends \
    # gcc y herramientas para compilar C
    build-essential \
    gcc \
    libffi-dev \
    # Dependencias de compilación para asyncpg
    libpq-dev \
    python3-dev \
    # Instalar uv de forma global, en lugar de dentro de un venv o cache
    # Luego eliminamos la cache de apt
    && pip install --no-cache-dir uv==0.7.13 \
    && rm -rf /var/lib/apt/lists/*

# 3. CREAR E INSTALAR DEPENDENCIAS (Forzando el uso de Python 3.12)
# Borramos el venv anterior (por si acaso) y forzamos a uv a usar el Python del sistema
# Usamos `uv venv` para crear el .venv
# Usamos `uv pip install` para instalar las dependencias
# Esto debería usar el Python de la imagen base (3.12)
RUN uv venv --seed && \
    /app/.venv/bin/pip install .
    
EXPOSE 8080

# 4. CMD: Ejecutar uvicorn desde el entorno virtual 3.12
CMD ["/app/.venv/bin/uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]