import os

class Config:
    SECRET_KEY = "your_super_secret_key_change_this"
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    DATABASE = "database.db"