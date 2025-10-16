# Usa imagem estável e compatível
FROM python:3.13-bookworm

# Define diretório de trabalho
WORKDIR /agk-core

# Variáveis de ambiente (formato moderno)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema
RUN apt update && apt install -y cron nano && rm -rf /var/lib/apt/lists/*

# Copia apenas requirements.txt primeiro (para cache de pip)
COPY requirements.txt .

# Atualiza pip e instala dependências do projeto
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Agora copia o resto do projeto (código e settings.py)
COPY . .

# Expõe porta e define comando de inicialização
EXPOSE 8000

CMD service cron start && python manage.py migrate && python manage.py runserver 0.0.0.0:8000
