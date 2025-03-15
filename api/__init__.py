from flask import Flask

app = Flask(__name__)

# Импортируем маршруты после создания приложения
from api import routes