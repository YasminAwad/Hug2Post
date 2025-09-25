# services/database_service.py
import json
import asyncpg
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

DATABASE_URL = "postgresql://paperuser:yasmin@localhost/paperhelper"  # Configure this


# Database Models
class Paper(BaseModel):
    id: Optional[int] = None
    title: str
    abstract: str
    key_findings: List[str]
    methodology: str
    significance: str
    paper_path: str  # Path to markdown file
    summary_path: str  # Path to markdown file
    timestamp: datetime

class LinkedInPost(BaseModel):
    id: Optional[int] = None
    title: str  # Foreign key to papers.title
    post: str


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.pool = None
    
    async def connect(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(self.database_url)
        await self.create_tables()
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def create_tables(self):
        """Create database tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Create papers table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id SERIAL PRIMARY KEY,
                    title TEXT UNIQUE NOT NULL,
                    abstract TEXT NOT NULL,
                    key_findings JSONB NOT NULL,
                    methodology TEXT NOT NULL,
                    significance TEXT NOT NULL,
                    paper_path TEXT NOT NULL,
                    summary_path TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            """)
            
            # Create linkedin_posts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS linkedin_posts (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    post TEXT NOT NULL,
                    FOREIGN KEY (title) REFERENCES papers(title) ON DELETE CASCADE
                )
            """)
            
            # Create conversations table for memory
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    intent TEXT,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

    async def drop_tables(self):
        """Drop database tables if they exist"""
        async with self.pool.acquire() as conn:
            # Drop child table first (to respect foreign key constraint)
            await conn.execute("DROP TABLE IF EXISTS linkedin_posts CASCADE")
            await conn.execute("DROP TABLE IF EXISTS papers CASCADE")
            await conn.execute("DROP TABLE IF EXISTS conversations CASCADE")

    
    async def save_paper(self, paper: Paper) -> int:
        """Save a paper to the database"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO papers (title, abstract, key_findings, methodology, 
                                significance, paper_path, summary_path, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (title) DO UPDATE SET
                    abstract = EXCLUDED.abstract,
                    key_findings = EXCLUDED.key_findings,
                    methodology = EXCLUDED.methodology,
                    significance = EXCLUDED.significance,
                    paper_path = EXCLUDED.paper_path,
                    summary_path = EXCLUDED.summary_path,
                    timestamp = EXCLUDED.timestamp
                RETURNING id
            """, 
            paper.title, 
            paper.abstract, 
            json.dumps(paper.key_findings),  # ✅ This should work since key_findings is a list
            paper.methodology, 
            paper.significance, 
            paper.paper_path,
            paper.summary_path, 
            paper.timestamp)
            
            return result['id']
        
# async def save_paper(self, paper: Paper):
#         """Save a paper to the database"""
#         async with self.pool.acquire() as conn:
#             row = await conn.execute("""
#                 INSERT INTO papers (title, abstract, key_findings, methodology, significance, paper_path, summary_path, timestamp)
#                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
#                 ON CONFLICT (title) DO UPDATE SET
#                     abstract = $2,
#                     key_findings = $3,
#                     methodology = $4,
#                     significance = $5,
#                     paper_path = $6, 
#                     summary_path = $7,
#                     timestamp = $8
#             """, paper.title, paper.abstract, json.dumps(paper.key_findings), 
#                 paper.methodology, paper.significance, paper.paper_path, paper.summary_path, paper.timestamp)
#             return row["id"]
    
    async def get_paper_by_title(self, title: str) -> Optional[Paper]:
        """Get a paper by title"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM papers WHERE title = $1
            """, title)
            
            if row:
                return Paper(
                    id=row['id'],
                    title=row['title'],
                    abstract=row['abstract'],
                    key_findings=json.loads(row['key_findings']),
                    methodology=row['methodology'],
                    significance=row['significance'],
                    paper_path=row['paper_path'],
                    summary_path=row['summary_path'],
                    timestamp=row['timestamp']
                )
            return None
    
    async def get_papers_by_date(self, date: str) -> List[Paper]:
        """Get papers by date (YYYY-MM-DD)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM papers 
                WHERE DATE(timestamp) = $1
                ORDER BY timestamp DESC
            """, datetime.strptime(date, "%Y-%m-%d").date())
            
            return [Paper(
                id=row['id'],
                title=row['title'],
                abstract=row['abstract'],
                key_findings=json.loads(row['key_findings']),
                methodology=row['methodology'],
                significance=row['significance'],
                paper_path=row['paper_path'],
                summary_path=row['summary_path'],
                timestamp=row['timestamp']
            ) for row in rows]
    
    async def save_linkedin_post(self, linkedin_post: LinkedInPost):
        """Save a LinkedIn post"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO linkedin_posts (title, post)
                VALUES ($1, $2)
            """, linkedin_post.title, linkedin_post.post)
    
    
    