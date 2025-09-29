import asyncio
import logging
import os
from pathlib import Path
from typing import IO, Any, Dict, List, Literal, Optional, Tuple, Union
from uuid import uuid4

from agno.db.sqlite import SqliteDb
from agno.knowledge.chunking.semantic import SemanticChunking
from agno.knowledge.chunking.strategy import ChunkingStrategy
from agno.knowledge.content import Content, FileData
from agno.knowledge.document.base import Document
from agno.knowledge.embedder.google import GeminiEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.base import Reader
from agno.utils.string import generate_id
from agno.vectordb.lancedb import LanceDb, SearchType
from markitdown import MarkItDown
from openai import OpenAI
from notification_service import NotificationService
from agno.knowledge.chunking.document import DocumentChunking
from config import GEMINI_API_KEY  


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




class MarkItDownReader(Reader):
    def __init__(
        self,
        chunking_strategy: ChunkingStrategy,
        **kwargs,
    ):
        super().__init__(chunking_strategy=chunking_strategy, **kwargs)

        client = OpenAI(
            api_key=GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        self.md = MarkItDown(
            llm_client=client,
            llm_model="gemma-3-4b-it",
            llm_prompt="Your goal is generate write all the text in a well structured markdown format if given image contain textual data else just describe the image. NOTE: Don not write anything else. Only write image's textual content or description.",
        )

    def read(self, file, name: Optional[str] = None) -> List[Document]:
        """Read a file and return a list of documents (synchronous wrapper)"""
        return asyncio.run(self.async_read(file, name))

    async def async_read_impl(self, file, name: Optional[str] = None) -> List[Document]:
        """Read a file and return a list of documents (async implementation)"""
        try:
            # Run the potentially blocking convert operation in a thread pool
            result = await asyncio.to_thread(self.md.convert, file)
            
            if isinstance(file, Path):
                if not file.exists():
                    raise FileNotFoundError(f"Could not find file: {file}")
                logger.info(f"Reading: {file}")
                doc_name = name or file.stem
            else:
                doc_name = name or result.title

            documents = [
                Document(
                    name=doc_name,
                    id=str(uuid4()),
                    content=result.text_content,
                )
            ]

            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document))
                return chunked_documents
            return documents

        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return []

    async def async_read(
        self, file: Union[Path, IO[Any]], name: Optional[str] = None
    ) -> List[Document]:
        """Asynchronously read a file and return a list of documents"""
        try:
            return await self.async_read_impl(file, name)
        except Exception as e:
            logger.error(f"Error reading file asynchronously: {e}")
            return []


contents_db = SqliteDb(db_file="data/knowledge.db")

vector_db = LanceDb(
    table_name="rag_kb",
    uri="/data/lancedb/rag_kb",
    embedder=GeminiEmbedder(api_key=GEMINI_API_KEY, task_type="RETRIEVAL_QUESTION_ANSWERING"),
    search_type=SearchType.hybrid,
)

knowledge = Knowledge(vector_db=vector_db, contents_db=contents_db)



def on_knowledge_added(task: asyncio.Task):
    try:
        result = task.result()
        logger.info(f"Knowledge added: {result}")
        asyncio.create_task(NotificationService.send_default("External Knowledge Added", str(result)))
    except Exception as e:
        logger.error(f"Error adding knowledge: {e}")
        asyncio.create_task(NotificationService.send_default("Failed to Add External Knowledge", str(e)))

class KnowledgeManager:
    def __init__(self, kb: Knowledge) -> None:
        self.kb = kb

    def get_combined_knowledge(self) -> Knowledge:
        # Hook for future: merge multiple sources if needed
        return self.kb

    def get_filters(self) -> Dict[str, Any]:
        try:
            return self.kb.get_filters()  # type: ignore[no-any-return]
        except Exception:
            return {}

    def list_contents(
        self,
        limit: int = 20,
        page: int = 1,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        contents, total_count = self.kb.get_content(
            limit=limit,
            page=page,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        # Normalize to dicts (SDK may return model objects)
        data: List[Dict[str, Any]] = []
        for c in contents or []:
            try:
                data.append(c if isinstance(c, dict) else c.to_dict())  # type: ignore[attr-defined]
            except Exception:
                try:
                    data.append(
                        {k: getattr(c, k) for k in dir(c) if not k.startswith("_")}
                    )
                except Exception:
                    pass
        return data, int(total_count or 0)

    def get_content_by_id(self, content_id: str) -> Dict[str, Any]:
        c = self.kb.get_content_by_id(content_id)
        if c is None:
            raise FileNotFoundError("Content not found")
        try:
            return c if isinstance(c, dict) else c.to_dict()  # type: ignore[attr-defined]
        except Exception:
            try:
                return {k: getattr(c, k) for k in dir(c) if not k.startswith("_")}
            except Exception:
                return {"id": content_id}

    async def add_content(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tag: Optional[str] = None,
        path: Optional[str] = None,
        url: Optional[str] = None,
        text_content: Optional[str] = None,
        topics: Optional[List[str]] = None,
        reader: Optional[Reader] = None,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        upsert: bool = True,
        skip_if_exists: bool = True,
        chunking_strategy: Literal["semantic", "document"] = "semantic",
    ) -> Optional[Dict[str, Any]]:
        
        if reader is None:
            if chunking_strategy == "semantic":
                chunker = SemanticChunking(
                    embedder=GeminiEmbedder(api_key=GEMINI_API_KEY, task_type="RETRIEVAL_DOCUMENT")
                )
            else:
                chunker = DocumentChunking()
            reader = MarkItDownReader(chunking_strategy=chunker)

        if path:
            # Use asyncio.to_thread for file system operations
            path_obj = await asyncio.to_thread(Path, path)
            if not await asyncio.to_thread(path_obj.exists):
                raise FileNotFoundError(f"Could not find file: {path}")

        if all(argument is None for argument in [path, url, text_content, topics]):
            raise ValueError(
                "At least one of 'path', 'url', 'text_content', or 'topics' must be provided."
            )

        if not skip_if_exists:
            logger.warning("skip_if_exists is disabled, disabling upsert")
            upsert = False

        content = None
        file_data = None
        if text_content:
            file_data = FileData(content=text_content, type="Text")

        # Get file size asynchronously if path exists
        file_size = 0
        if path and path_obj:
            try:
                file_size = await asyncio.to_thread(lambda: path_obj.stat().st_size)
                if file_size >= 2 * 1024 * 1024:  # 2 MB
                    await NotificationService.send_default(
                        "External Knowledge",
                        "Adding large files may take longer to process.",
                    )
            except (OSError, IOError):
                file_size = 0

        await NotificationService.send_default("External Knowledge", "Processing content...")

        content = Content(
            name=name,
            description=description,
            path=str(path) if path else None,
            url=url,
            file_data=file_data if file_data else None,
            metadata={"user_tag": tag} if tag else None,
            topics=topics,
            reader=reader,
            size=file_size if path else (len(text_content) if text_content else 0),
            file_type=path_obj.suffix.lstrip(".").upper()
            if path
            else ("TEXT" if text_content else None),
        )
        
        # Run content hash generation in thread pool to avoid blocking
        content.content_hash = await asyncio.to_thread(self.kb._build_content_hash, content)
        content.id = generate_id(content.content_hash)

        logger.info("Content to add: " + str(content))

        # For MarkItDownReader, we need to handle the blocking operations differently
        if isinstance(reader, MarkItDownReader):
            # Create an async task that properly isolates blocking operations
            task = asyncio.create_task(self._process_content_async(content, upsert, skip_if_exists, include, exclude))
        else:
            # For other readers, use the original approach
            task = asyncio.create_task(self.kb._load_content(content, upsert, skip_if_exists, include, exclude))
        
        task.add_done_callback(on_knowledge_added)

        # Return immediately without waiting for the background task
        return {
            "id": content.id,
            "name": content.name,
            "status": "processing",
            "message": "Content is being processed in the background"
        }

    def delete_content(self, content_id: str) -> Dict[str, Any]:
        existing = None
        try:
            existing = self.get_content_by_id(content_id)
        except Exception:
            pass
        self.kb.remove_content_by_id(content_id)
        return existing or {"id": content_id, "deleted": True}

    async def _process_content_async(
        self,
        content: Content,
        upsert: bool,
        skip_if_exists: bool,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> None:
        """
        Process content asynchronously, running blocking operations in thread pools
        """
        try:
            # The main issue is that the reader's convert operation is blocking
            # We need to run the entire _load_content in a separate thread
            # but in a way that doesn't block the event loop
            
            def run_load_content():
                # Create a new event loop for this thread
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.kb._load_content(content, upsert, skip_if_exists, include, exclude)
                    )
                finally:
                    loop.close()
            
            # Run the blocking operation in a thread pool
            await asyncio.to_thread(run_load_content)
            
        except Exception as e:
            logger.error(f"Error processing content async: {e}")
            # Update content status to failed using the proper enum
            try:
                from agno.knowledge.content import ContentStatus
                content.status = ContentStatus.FAILED
                content.status_message = str(e)
                await asyncio.to_thread(self.kb._update_content, content)
            except Exception as update_error:
                logger.error(f"Error updating content status: {update_error}")
            raise

    def delete_all(self) -> int:
        # No return from SDK; return count of deleted before cleanup
        contents, total = self.list_contents(limit=1000, page=1)
        self.kb.remove_all_content()
        return len(contents) if contents else int(total)

    def update_content(
        self,
        content_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tag: Optional[str] = None,
    ):
        try:
            # Try the normal patch_content first
            return self.kb.patch_content(
                Content(
                    id=content_id,
                    name=name,
                    description=description,
                    metadata={"tag": tag} if tag else None,
                )
            )
        except Exception as e:
            if "Operator ->> is not supported" in str(e):
                logger.warning(f"Vector DB metadata update failed, updating content DB only: {e}")
                # Temporarily disable vector DB for this update
                original_vector_db = self.kb.vector_db
                self.kb.vector_db = None
                try:
                    result = self.kb.patch_content(
                        Content(
                            id=content_id,
                            name=name,
                            description=description,
                            metadata={"tag": tag} if tag else None,
                        )
                    )
                    return result
                finally:
                    # Restore vector DB
                    self.kb.vector_db = original_vector_db
            else:
                raise e


# Singleton for use across app
knowledge_manager = KnowledgeManager(knowledge)

if __name__ == "__main__":
    # Example usage
    km = KnowledgeManager(knowledge)
    asyncio.run(
        km.add_content(
            path=r"C:/Users/Naitik/Downloads/1754276888.pdf",
            name="School Exam Syllabus",
            tag="docs",
        )
    )
    # all_contents, total = km.list_contents()
    # print(f"Total contents: {total}")
    # for content in all_contents:
    #     print(content)
