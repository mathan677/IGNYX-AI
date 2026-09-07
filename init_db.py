from database import Base, engine
from models import Conversation, Message


print("Creating IGNYX database tables...")

Base.metadata.create_all(bind=engine)

print("Database tables created successfully.")