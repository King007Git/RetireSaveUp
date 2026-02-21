import os
from dotenv import load_dotenv

load_dotenv()

class DevEnv:
    def __init__(self):
        self.DATABASE_URL=os.getenv('DATABASE_URL', '***')
        self.VERSION=os.getenv('VERSION','default-v1')
        self.SECRET_KEY=os.getenv('SECRET_KEY','default-secret')

settings = DevEnv()