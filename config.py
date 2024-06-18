import os

class Config:
    SECRET_KEY = 'you-will-never-guess'
    MONGO_URI = 'mongodb://localhost:27017/schoolThingy'

config = Config()
g