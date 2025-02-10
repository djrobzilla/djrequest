FROM python:3.13

WORKDIR /app

COPY . .

#RUN apt-get update

RUN pip install -r requirements.txt

CMD ["python", "app.py"]