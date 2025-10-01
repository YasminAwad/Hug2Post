# services/summary_service.py
import json
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
from app.services.llm import LLMService
from app.services.database import DatabaseService, Paper
from app.config.logging import logger
from app.utils.pdf_utils import extract_text
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

class SummaryService:
    """Service for creating paper summaries"""
    
    def __init__(self, llm_service: LLMService, database_service: DatabaseService, base_papers_dir: Path = Path("papers"), base_summaries_dir: Path = Path("summaries")):
        self.llm_service = llm_service
        self.database_service = database_service
        self.base_papers_dir = base_papers_dir
        self.base_summaries_dir = base_summaries_dir
    
    async def summarize_papers_for_date(self, target_date: str) -> Tuple[List[Dict[str, Any]], str]:
        """Summarize all papers for a given date"""
        date_folder = target_date.replace("-", "")
        papers_folder = self.base_papers_dir / date_folder
        summaries_folder = self.base_summaries_dir / date_folder
        summaries_folder.mkdir(exist_ok=True)
        
        if not papers_folder.exists():
            raise FileNotFoundError(f"No papers folder found for date {target_date}")
        
        pdf_files = list(papers_folder.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found for {target_date}")
        
        summaries = []
        processed_summary_ids = []
        processed_count = 0
        
        for pdf_file in pdf_files:
            try:
                print(f"Processing {pdf_file.name}...")
                
                text_content = await extract_text(pdf_file)
                paper_model = await self._create_paper_summary_and_save_to_db(
                    text_content, pdf_file.stem, papers_folder, summaries_folder, target_date
                )

                processed_summary_ids.append(paper_model.id)
                summaries.append({
                    "title": paper_model.title,
                    "abstract": paper_model.abstract
                })
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing {pdf_file.name}: {str(e)}")
                continue
        
        response_msg = f"Successfully summarized {processed_count} papers for {target_date}!"
        if processed_count > 0:
            response_msg += "\n\nSummaries created:"
            for i, summary in enumerate(summaries):
                response_msg += f"\n{i+1}. {summary['title']}"
                # response_msg += f"\n   {summary['abstract'][:100]}...\n"
        
        return processed_summary_ids, response_msg
    
    async def _create_paper_summary_and_save_to_db(
        self, 
        text_content: str, 
        paper_title: str, 
        papers_folder: Path,
        summaries_folder: Path,
        target_date: str
    ) -> Paper:
        """Create paper summary, save markdown file, and save metadata to database"""
        
        logger.info("Entered _create_paper_summary_and_save_to_db")
        # Create structured metadata
        metadata_dict = await self._create_paper_metadata(text_content, paper_title)
        
        # Create detailed summary
        detailed_summary = await self._create_detailed_summary(
            text_content, metadata_dict['title']
        )
        
        # Save detailed summary as markdown
        summary_md_filename = f"{paper_title}_detailed_summary.md"
        summary_md_path = summaries_folder / summary_md_filename
        logger.info(f"Saving detailed summary to {summary_md_path}")

        markdown_content = f"""{detailed_summary}"""
        
        async with aiofiles.open(summary_md_path, 'w', encoding='utf-8') as f:
            await f.write(markdown_content)

        # Create Paper model for database
        paper_model = Paper(
            title=str(metadata_dict['title']),
            abstract=str(metadata_dict['abstract']),
            key_findings=metadata_dict['key_findings'],
            methodology=metadata_dict['methodology'],
            significance=metadata_dict['significance'],
            paper_path=str(papers_folder / f"{paper_title}.pdf"),
            summary_path=str(summary_md_path),  # Store markdown file path
            timestamp=datetime.strptime(target_date, "%Y-%m-%d")
        )
        
        # Save to database
        paper_id = await self.database_service.save_paper(paper_model)
        paper_model.id = paper_id
        logger.info(f"Saved paper model: {paper_model}")
        #logger.info(f"Saved paper metadata to database: {paper_model.title}")
        
        return paper_model
    
    async def _create_paper_metadata(self, text_content: str, paper_title: str) -> Dict[str, Any]:
        """Create structured metadata from paper content"""
        logger.info("Entered _create_paper_metadata")
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Create structured metadata with the following fields. 
            Respond ONLY with a valid JSON object, without writing json at the start:

            {
                "title": "Extracted or inferred title, or None if not available",
                "abstract": "A brief 2-3 sentence summary, or None if not available",
                "key_findings": ["Finding 1", "Finding 2", "Finding 3",] or None if not available,
                "methodology": "Brief description of the approach, or None if not available",
                "significance": "Why this work matters, or None if not available"
            }"""),
            HumanMessage(content=f"Content:\n{text_content[:3000]}")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())
        
        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            logger.info("JSONDecodeError")
            logger.info(response)
            return {
                "title": paper_title,
                "abstract": "Could not generate abstract due to parsing error.",
                "key_findings": ["Could not extract key findings."],
                "methodology": "Could not extract methodology.",
                "significance": "Could not extract significance."
            }
        
    async def _create_detailed_summary(self, text_content: str, title: str) -> str:
        """Create detailed summary from paper content"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Write a comprehensive summary covering:
            1. Introduction and Background
            2. Problem Statement and Motivation  
            3. Proposed Method/Approach
            4. Experimental Setup and Data
            5. Results and Analysis
            6. Discussion and Implications
            7. Limitations and Future Work
            8. Conclusions

            Use markdown formatting with proper headers."""),
            HumanMessage(content=f"Paper: {title}\n\nContent:\n{text_content[:4000]}")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())
        return response.content