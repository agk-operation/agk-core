FROM python:3.13-bookworm

WORKDIR /agk-core

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt update && apt -y install cron && apt -y install nano

COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD cron ; python manage.py migrate && python manage.py runserver 0.0.0.0:8000