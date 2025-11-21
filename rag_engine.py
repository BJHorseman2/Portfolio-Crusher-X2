"""
RAG (Retrieval Augmented Generation) Engine for Portfolio Crusher X2

This module provides context retrieval functionality using ChromaDB for storing
and querying investment-related content from multiple sources including YouTube
transcripts, The Economist articles, and custom user-provided sources.
"""

import chromadb
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
import requests
from bs4 import BeautifulSoup
import yaml
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import time
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _generate_id(content: str, source: str) -> str:
    """
    Generate a unique ID for a content chunk using SHA256 hash.

    Args:
        content: The text content to hash
        source: The source identifier

    Returns:
        A unique identifier string
    """
    combined = f"{source}:{content}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def _chunk_text(text: str, max_words: int = 500, overlap_words: int = 50) -> List[str]:
    """
    Chunk text into segments with optional overlap for context continuity.

    Args:
        text: The text to chunk
        max_words: Maximum words per chunk
        overlap_words: Number of overlapping words between chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    words = text.split()
    chunks = []

    if len(words) <= max_words:
        return [text]

    start = 0
    while start < len(words):
        end = start + max_words
        chunk_words = words[start:end]
        chunks.append(' '.join(chunk_words))

        if end >= len(words):
            break

        start = end - overlap_words

    return chunks


def _check_robots_txt(url: str) -> bool:
    """
    Check if scraping is allowed by robots.txt.

    Args:
        url: The URL to check

    Returns:
        True if scraping is allowed, False otherwise
    """
    try:
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        user_agent = "PortfolioCrusherBot/1.0"
        return rp.can_fetch(user_agent, url)
    except Exception as e:
        logger.warning(f"Could not check robots.txt for {url}: {e}")
        return True


def _extract_video_id(video_input: str) -> str:
    """
    Extract YouTube video ID from various input formats.

    Args:
        video_input: YouTube URL or video ID

    Returns:
        Extracted video ID
    """
    # If it's already just an ID (11 characters), return it
    if len(video_input) == 11 and not '/' in video_input and not '?' in video_input:
        return video_input

    # Extract from various YouTube URL formats
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, video_input)
        if match:
            return match.group(1)

    return video_input


def initialize_rag_db(db_path: str = './chroma_db') -> chromadb.Client:
    """
    Initialize ChromaDB client and create necessary collections.

    Creates three collections:
    - economist_articles: For storing Economist article content
    - youtube_transcripts: For storing YouTube video transcripts
    - custom_sources: For storing user-provided content

    Args:
        db_path: Path to store the ChromaDB database

    Returns:
        Initialized ChromaDB client
    """
    try:
        logger.info(f"Initializing ChromaDB at {db_path}")
        client = chromadb.PersistentClient(path=db_path)

        # Create or get economist articles collection
        client.get_or_create_collection(
            name="economist_articles",
            metadata={
                "description": "The Economist articles for investment context",
                "hnsw:space": "cosine"
            }
        )
        logger.info("Created/accessed 'economist_articles' collection")

        # Create or get YouTube transcripts collection
        client.get_or_create_collection(
            name="youtube_transcripts",
            metadata={
                "description": "YouTube video transcripts for investment context",
                "hnsw:space": "cosine"
            }
        )
        logger.info("Created/accessed 'youtube_transcripts' collection")

        # Create or get custom sources collection
        client.get_or_create_collection(
            name="custom_sources",
            metadata={
                "description": "User-provided custom content for investment context",
                "hnsw:space": "cosine"
            }
        )
        logger.info("Created/accessed 'custom_sources' collection")

        logger.info("ChromaDB initialization complete")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        raise


def ingest_youtube_video(video_id: str, db_client: chromadb.Client) -> bool:
    """
    Fetch YouTube transcript and store it in ChromaDB.

    Downloads the transcript, extracts metadata, chunks the content into
    manageable segments, and stores them in the youtube_transcripts collection.

    Args:
        video_id: YouTube video ID or URL
        db_client: Initialized ChromaDB client

    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract video ID if URL is provided
        video_id = _extract_video_id(video_id)
        logger.info(f"Ingesting YouTube video: {video_id}")

        # Get collection
        collection = db_client.get_collection(name="youtube_transcripts")

        # Check if video already exists
        existing = collection.get(where={"video_id": video_id})
        if existing and existing['ids']:
            logger.info(f"Video {video_id} already exists in database. Skipping.")
            return True

        # Fetch transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        except TranscriptsDisabled:
            logger.error(f"Transcripts are disabled for video {video_id}")
            return False
        except NoTranscriptFound:
            logger.error(f"No transcript found for video {video_id}")
            return False
        except VideoUnavailable:
            logger.error(f"Video {video_id} is unavailable")
            return False
        except Exception as e:
            logger.error(f"Error fetching transcript for {video_id}: {e}")
            return False

        # Combine transcript segments into full text
        full_transcript = ' '.join([entry['text'] for entry in transcript_list])

        # Get video metadata
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_title = f"YouTube Video {video_id}"

        try:
            response = requests.get(video_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    video_title = title_tag.text.replace(' - YouTube', '').strip()
        except Exception as e:
            logger.warning(f"Could not fetch video title for {video_id}: {e}")

        # Chunk the transcript
        chunks = _chunk_text(full_transcript, max_words=500, overlap_words=50)

        if not chunks:
            logger.warning(f"No content to ingest for video {video_id}")
            return False

        # Prepare data for ingestion
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = _generate_id(chunk, f"youtube_{video_id}_{i}")
            documents.append(chunk)
            metadatas.append({
                "source": "youtube",
                "video_id": video_id,
                "video_url": video_url,
                "title": video_title,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "ingested_at": datetime.utcnow().isoformat()
            })
            ids.append(chunk_id)

        # Add to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Successfully ingested video {video_id} ({len(chunks)} chunks)")
        return True

    except Exception as e:
        logger.error(f"Failed to ingest YouTube video {video_id}: {e}")
        return False


def ingest_economist_article(url: str, db_client: chromadb.Client) -> bool:
    """
    Scrape an Economist article and store it in ChromaDB.

    Respects robots.txt, extracts article content, chunks it appropriately,
    and stores it in the economist_articles collection.

    Args:
        url: URL of the Economist article
        db_client: Initialized ChromaDB client

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Ingesting Economist article: {url}")

        # Check robots.txt
        if not _check_robots_txt(url):
            logger.error(f"Scraping blocked by robots.txt for {url}")
            return False

        # Get collection
        collection = db_client.get_collection(name="economist_articles")

        # Check if article already exists
        existing = collection.get(where={"url": url})
        if existing and existing['ids']:
            logger.info(f"Article {url} already exists in database. Skipping.")
            return True

        # Fetch article
        headers = {
            'User-Agent': 'PortfolioCrusherBot/1.0 (Investment Research Tool)'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch article from {url}: {e}")
            return False

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title
        title = "Untitled Article"
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
        else:
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.text.strip()

        # Extract date
        date = None
        date_patterns = [
            {'name': 'time', 'attrs': {'datetime': True}},
            {'name': 'meta', 'attrs': {'property': 'article:published_time'}},
            {'name': 'meta', 'attrs': {'name': 'date'}},
        ]

        for pattern in date_patterns:
            date_tag = soup.find(**pattern)
            if date_tag:
                date = date_tag.get('datetime') or date_tag.get('content')
                break

        # Extract article content
        article_text = ""

        # Try common article content selectors
        content_selectors = [
            {'name': 'article'},
            {'name': 'div', 'class': 'article-body'},
            {'name': 'div', 'class': 'article-content'},
            {'name': 'div', 'class': 'content'},
            {'name': 'main'},
        ]

        for selector in content_selectors:
            content = soup.find(**selector)
            if content:
                paragraphs = content.find_all('p')
                if paragraphs:
                    article_text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                    break

        # Fallback: get all paragraphs
        if not article_text:
            paragraphs = soup.find_all('p')
            article_text = ' '.join([p.get_text(strip=True) for p in paragraphs])

        if not article_text or len(article_text.strip()) < 100:
            logger.error(f"Could not extract meaningful content from {url}")
            return False

        # Chunk the article
        chunks = _chunk_text(article_text, max_words=500, overlap_words=50)

        if not chunks:
            logger.warning(f"No content to ingest from {url}")
            return False

        # Prepare data for ingestion
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = _generate_id(chunk, f"economist_{url}_{i}")
            documents.append(chunk)
            metadatas.append({
                "source": "economist",
                "url": url,
                "title": title,
                "date": date if date else "unknown",
                "chunk_index": i,
                "total_chunks": len(chunks),
                "ingested_at": datetime.utcnow().isoformat()
            })
            ids.append(chunk_id)

        # Add to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Successfully ingested article from {url} ({len(chunks)} chunks)")
        return True

    except Exception as e:
        logger.error(f"Failed to ingest Economist article from {url}: {e}")
        return False


def ingest_custom_text(
    text: str,
    source_name: str,
    metadata: Dict[str, Any],
    db_client: chromadb.Client
) -> bool:
    """
    Ingest user-provided custom text into ChromaDB.

    Args:
        text: The text content to ingest
        source_name: Identifier for the source
        metadata: Additional metadata to store with the content
        db_client: Initialized ChromaDB client

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Ingesting custom text from source: {source_name}")

        if not text or not text.strip():
            logger.error("Empty text provided")
            return False

        # Get collection
        collection = db_client.get_collection(name="custom_sources")

        # Check if content already exists
        content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        existing = collection.get(where={"content_hash": content_hash})
        if existing and existing['ids']:
            logger.info(f"Content from {source_name} already exists. Skipping.")
            return True

        # Chunk the text
        chunks = _chunk_text(text, max_words=500, overlap_words=50)

        if not chunks:
            logger.warning(f"No content to ingest from {source_name}")
            return False

        # Prepare data for ingestion
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = _generate_id(chunk, f"custom_{source_name}_{i}")
            documents.append(chunk)

            chunk_metadata = {
                "source": "custom",
                "source_name": source_name,
                "content_hash": content_hash,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "ingested_at": datetime.utcnow().isoformat()
            }
            chunk_metadata.update(metadata)

            metadatas.append(chunk_metadata)
            ids.append(chunk_id)

        # Add to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Successfully ingested custom text from {source_name} ({len(chunks)} chunks)")
        return True

    except Exception as e:
        logger.error(f"Failed to ingest custom text from {source_name}: {e}")
        return False


def query_context(
    query: str,
    theme: Optional[str] = None,
    top_k: int = 5,
    db_client: Optional[chromadb.Client] = None
) -> List[Dict[str, Any]]:
    """
    Query all collections for relevant context.

    Args:
        query: The search query
        theme: Optional theme filter (e.g., 'ai', 'clean_energy')
        top_k: Number of top results to return
        db_client: Initialized ChromaDB client

    Returns:
        List of relevant content chunks with metadata and relevance scores
    """
    try:
        if db_client is None:
            logger.error("Database client not provided")
            return []

        logger.info(f"Querying context for: '{query}' (theme: {theme}, top_k: {top_k})")

        all_results = []

        # Query each collection
        collections = ['economist_articles', 'youtube_transcripts', 'custom_sources']

        for collection_name in collections:
            try:
                collection = db_client.get_collection(name=collection_name)

                # Build where filter if theme is provided
                where_filter = None
                if theme:
                    where_filter = {
                        "$or": [
                            {"theme": theme},
                            {"category": theme},
                            {"topic": theme}
                        ]
                    }

                # Query collection
                results = collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where_filter
                )

                # Process results
                if results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        distance = results['distances'][0][i] if results.get('distances') else 1.0
                        relevance_score = 1.0 - distance

                        result = {
                            'content': doc,
                            'source': collection_name,
                            'relevance_score': relevance_score,
                            'metadata': results['metadatas'][0][i] if results.get('metadatas') else {}
                        }
                        all_results.append(result)

            except Exception as e:
                logger.warning(f"Error querying collection {collection_name}: {e}")
                continue

        # Sort by relevance score and return top_k
        all_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        final_results = all_results[:top_k]

        logger.info(f"Found {len(final_results)} relevant context chunks")
        return final_results

    except Exception as e:
        logger.error(f"Failed to query context: {e}")
        return []


def get_theme_context(
    theme: str,
    db_client: Optional[chromadb.Client] = None
) -> Dict[str, Any]:
    """
    Get aggregated context for a specific investment theme.

    Retrieves and organizes relevant content from all sources for a given theme.
    Useful for spoke analysis in the hub-and-spoke strategy.

    Args:
        theme: The theme category (e.g., 'ai', 'clean_energy', 'genomics')
        db_client: Initialized ChromaDB client

    Returns:
        Dictionary containing aggregated context from all sources
    """
    try:
        if db_client is None:
            logger.error("Database client not provided")
            return {}

        logger.info(f"Getting context for theme: {theme}")

        theme_context = {
            'theme': theme,
            'youtube_content': [],
            'economist_content': [],
            'custom_content': [],
            'summary': {
                'total_sources': 0,
                'youtube_count': 0,
                'economist_count': 0,
                'custom_count': 0
            }
        }

        # Query YouTube transcripts
        try:
            youtube_collection = db_client.get_collection(name="youtube_transcripts")
            youtube_results = youtube_collection.query(
                query_texts=[theme],
                n_results=10
            )

            if youtube_results['documents'] and youtube_results['documents'][0]:
                for i, doc in enumerate(youtube_results['documents'][0]):
                    theme_context['youtube_content'].append({
                        'content': doc,
                        'metadata': youtube_results['metadatas'][0][i] if youtube_results.get('metadatas') else {}
                    })
                theme_context['summary']['youtube_count'] = len(youtube_results['documents'][0])
        except Exception as e:
            logger.warning(f"Error querying YouTube content for theme {theme}: {e}")

        # Query Economist articles
        try:
            economist_collection = db_client.get_collection(name="economist_articles")
            economist_results = economist_collection.query(
                query_texts=[theme],
                n_results=10
            )

            if economist_results['documents'] and economist_results['documents'][0]:
                for i, doc in enumerate(economist_results['documents'][0]):
                    theme_context['economist_content'].append({
                        'content': doc,
                        'metadata': economist_results['metadatas'][0][i] if economist_results.get('metadatas') else {}
                    })
                theme_context['summary']['economist_count'] = len(economist_results['documents'][0])
        except Exception as e:
            logger.warning(f"Error querying Economist content for theme {theme}: {e}")

        # Query custom sources
        try:
            custom_collection = db_client.get_collection(name="custom_sources")
            custom_results = custom_collection.query(
                query_texts=[theme],
                n_results=10
            )

            if custom_results['documents'] and custom_results['documents'][0]:
                for i, doc in enumerate(custom_results['documents'][0]):
                    theme_context['custom_content'].append({
                        'content': doc,
                        'metadata': custom_results['metadatas'][0][i] if custom_results.get('metadatas') else {}
                    })
                theme_context['summary']['custom_count'] = len(custom_results['documents'][0])
        except Exception as e:
            logger.warning(f"Error querying custom content for theme {theme}: {e}")

        # Calculate totals
        theme_context['summary']['total_sources'] = (
            theme_context['summary']['youtube_count'] +
            theme_context['summary']['economist_count'] +
            theme_context['summary']['custom_count']
        )

        logger.info(f"Retrieved {theme_context['summary']['total_sources']} sources for theme {theme}")
        return theme_context

    except Exception as e:
        logger.error(f"Failed to get theme context for {theme}: {e}")
        return {}


def batch_ingest_sources(config: Dict[str, Any], db_client: chromadb.Client) -> Dict[str, Any]:
    """
    Batch ingest all sources from configuration.

    Processes YouTube videos, Economist topics, and custom URLs specified
    in the configuration file.

    Args:
        config: Configuration dictionary (typically loaded from config.yaml)
        db_client: Initialized ChromaDB client

    Returns:
        Dictionary containing ingestion statistics
    """
    try:
        logger.info("Starting batch ingestion from configuration")

        stats = {
            'youtube': {
                'attempted': 0,
                'successful': 0,
                'failed': 0
            },
            'economist': {
                'attempted': 0,
                'successful': 0,
                'failed': 0
            },
            'custom': {
                'attempted': 0,
                'successful': 0,
                'failed': 0
            },
            'total_attempted': 0,
            'total_successful': 0,
            'total_failed': 0
        }

        # Extract data sources from config
        data_sources = config.get('data_sources', {})
        content_sources = data_sources.get('content_sources', {})

        # Ingest YouTube videos
        youtube_config = content_sources.get('youtube', {})
        if youtube_config.get('enabled', False):
            videos = youtube_config.get('videos', [])
            logger.info(f"Processing {len(videos)} YouTube videos")

            for video in videos:
                stats['youtube']['attempted'] += 1
                stats['total_attempted'] += 1

                # Handle both string IDs and dict with video_id key
                video_id = video if isinstance(video, str) else video.get('video_id', '')

                if not video_id:
                    logger.warning("Skipping empty video ID")
                    stats['youtube']['failed'] += 1
                    stats['total_failed'] += 1
                    continue

                if ingest_youtube_video(video_id, db_client):
                    stats['youtube']['successful'] += 1
                    stats['total_successful'] += 1
                else:
                    stats['youtube']['failed'] += 1
                    stats['total_failed'] += 1

                # Rate limiting
                time.sleep(1)

        # Ingest Economist articles
        economist_config = content_sources.get('economist', {})
        if economist_config.get('enabled', False):
            topics = economist_config.get('topics', [])
            logger.info(f"Processing Economist topics: {topics}")

            # Note: The config has topics but not specific URLs
            # This would need to be implemented with a search/discovery mechanism
            # or the config should be updated to include specific article URLs
            logger.info("Economist topic ingestion requires specific URLs in config")

        # Ingest custom sources
        custom_config = content_sources.get('custom_sources', {})
        urls = custom_config.get('urls', [])
        logger.info(f"Processing {len(urls)} custom URLs")

        for url in urls:
            stats['custom']['attempted'] += 1
            stats['total_attempted'] += 1

            if not url:
                logger.warning("Skipping empty URL")
                stats['custom']['failed'] += 1
                stats['total_failed'] += 1
                continue

            # Determine if it's an Economist URL or other
            if 'economist.com' in url:
                if ingest_economist_article(url, db_client):
                    stats['economist']['successful'] += 1
                    stats['total_successful'] += 1
                else:
                    stats['economist']['failed'] += 1
                    stats['total_failed'] += 1
            else:
                # For other URLs, fetch and ingest as custom content
                try:
                    response = requests.get(url, timeout=15)
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Extract text
                    paragraphs = soup.find_all('p')
                    text = ' '.join([p.get_text(strip=True) for p in paragraphs])

                    # Extract title
                    title = soup.find('title')
                    title_text = title.text if title else url

                    if ingest_custom_text(text, url, {'url': url, 'title': title_text}, db_client):
                        stats['custom']['successful'] += 1
                        stats['total_successful'] += 1
                    else:
                        stats['custom']['failed'] += 1
                        stats['total_failed'] += 1
                except Exception as e:
                    logger.error(f"Failed to ingest custom URL {url}: {e}")
                    stats['custom']['failed'] += 1
                    stats['total_failed'] += 1

            # Rate limiting
            time.sleep(1)

        logger.info(f"Batch ingestion complete. Success: {stats['total_successful']}, Failed: {stats['total_failed']}")
        return stats

    except Exception as e:
        logger.error(f"Failed to complete batch ingestion: {e}")
        return stats


if __name__ == "__main__":
    # Example usage
    print("RAG Engine for Portfolio Crusher X2")
    print("=" * 50)

    # Initialize database
    client = initialize_rag_db()

    # Load config
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Batch ingest sources from config
        stats = batch_ingest_sources(config, client)
        print(f"\nIngestion Statistics:")
        print(f"Total Attempted: {stats['total_attempted']}")
        print(f"Total Successful: {stats['total_successful']}")
        print(f"Total Failed: {stats['total_failed']}")

    except FileNotFoundError:
        print("config.yaml not found. Skipping batch ingestion.")
    except Exception as e:
        print(f"Error during batch ingestion: {e}")
