import sqlite3
import json
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "duet_studio.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        asset_id TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        duration REAL DEFAULT 0.0,
        width INTEGER DEFAULT 0,
        height INTEGER DEFAULT 0,
        checksum TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS segments (
        segment_id TEXT PRIMARY KEY,
        asset_id TEXT NOT NULL,
        start_ms INTEGER NOT NULL,
        end_ms INTEGER NOT NULL,
        speaker_id TEXT,
        FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_turns (
        turn_id TEXT PRIMARY KEY,
        segment_id TEXT,
        transcript TEXT,
        reply_to TEXT,
        relationship TEXT,
        confidence REAL DEFAULT 1.0,
        FOREIGN KEY(segment_id) REFERENCES segments(segment_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generations (
        generation_id TEXT PRIMARY KEY,
        parent_assets TEXT, -- JSON list of asset IDs
        segments TEXT, -- JSON list of segment definitions
        layout TEXT, -- side-by-side, alternating, stacked
        edit_recipe TEXT, -- JSON recipe details
        output_asset_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(output_asset_id) REFERENCES assets(asset_id)
    )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
