import sqlite3
import chromadb
import uuid
import os
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
SQLITE_DB_PATH = "database/myriad_state.db"  # Path to your old database
CHROMA_DB_PATH = "database/vector_memory"    # Path where Chroma will save
# ==========================================

print("🚀 Starting Memory Migration Pipeline...")

# 1. Initialize the new Vector Database
print("🧠 Initializing ChromaDB and Embedding Model (this may take a minute to download the model)...")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection(name="conversation_history")

# 2. Connect to the old SQLite Database
if not os.path.exists(SQLITE_DB_PATH):
    print(f"❌ Error: Could not find SQLite database at {SQLITE_DB_PATH}")
    exit(1)

conn = sqlite3.connect(SQLITE_DB_PATH)
cursor = conn.cursor()

# 3. Find the messages table (Claude usually names it 'messages' or 'history')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]

target_table = None
for t in ['messages', 'chat_history', 'history']:
    if t in tables:
        target_table = t
        break

if not target_table:
    print(f"❌ Error: Could not find a messages table. Found: {tables}")
    exit(1)

# 4. Extract and Migrate
print(f"📂 Extracting memories from '{target_table}'...")
# Assuming standard Claude schema: id, role, content, timestamp (and maybe user_id)
cursor.execute(f"SELECT * FROM {target_table}")
rows = cursor.fetchall()
columns = [description[0] for description in cursor.description]

migrated_count = 0
for row in rows:
    # Map row data to a dictionary based on column names
    row_data = dict(zip(columns, row))
    
    # Extract the actual text content (usually under 'content' or 'message')
    content = row_data.get('content') or row_data.get('message')
    if not content:
        continue
        
    role = row_data.get('role', 'user')
    timestamp = row_data.get('timestamp', str(datetime.now()))
    
    # Create a unique ID for the vector
    memory_id = f"mem_{uuid.uuid4().hex[:8]}"
    
    # Inject into Vector Space
    collection.add(
        documents=[content],
        metadatas=[{"role": role, "timestamp": str(timestamp)}],
        ids=[memory_id]
    )
    migrated_count += 1

conn.close()
print(f"✅ Migration Complete! Successfully ported {migrated_count} memories into the Vector Graph.")
