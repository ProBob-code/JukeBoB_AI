"""
Track Session - AI-powered study tracker from uploaded documents
Parses PDFs and images to extract study topics and create trackers
"""

import io
import json
import base64
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import os

# In-memory storage for trackers (would use database in production)
trackers = {}


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF content using PyPDF2"""
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except ImportError:
        # Fallback if PyPDF2 not installed
        return ""
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""


def parse_content_to_items(text: str) -> List[Dict]:
    """
    Parse text content into tracker items
    Uses simple line-based parsing to extract topics
    """
    items = []
    lines = text.strip().split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        # Skip empty lines and very short lines
        if not line or len(line) < 2:
            continue
        
        # Skip common headers/footers
        lower = line.lower()
        if any(skip in lower for skip in ['page', 'table of contents', 'index', 'copyright', 'isbn']):
            continue
        
        # Clean up the line
        # Remove common prefixes like numbers, bullets, etc.
        clean_line = line
        for prefix in ['•', '-', '*', '→', '>', '●', '○']:
            if clean_line.startswith(prefix):
                clean_line = clean_line[1:].strip()
        
        # Remove leading numbers like "1.", "1)", "(1)"
        if clean_line and clean_line[0].isdigit():
            parts = clean_line.split('.', 1)
            if len(parts) > 1 and parts[0].strip().isdigit():
                clean_line = parts[1].strip()
            else:
                parts = clean_line.split(')', 1)
                if len(parts) > 1 and parts[0].strip('(').isdigit():
                    clean_line = parts[1].strip()
        
        if clean_line and len(clean_line) >= 2:
            items.append({
                "id": str(uuid.uuid4())[:8],
                "name": clean_line[:100],  # Limit length
                "completed": False
            })
    
    # Remove duplicates while preserving order
    seen = set()
    unique_items = []
    for item in items:
        if item['name'].lower() not in seen:
            seen.add(item['name'].lower())
            unique_items.append(item)
    
    return unique_items[:50]  # Limit to 50 items max


def create_tracker_from_text(text: str, filename: str) -> Dict:
    """Create a tracker from extracted text"""
    items = parse_content_to_items(text)
    
    if not items:
        # If no items extracted, create a default structure
        items = [{"id": str(uuid.uuid4())[:8], "name": "No items could be extracted", "completed": False}]
    
    tracker_id = str(uuid.uuid4())
    tracker = {
        "id": tracker_id,
        "name": filename.rsplit('.', 1)[0] if '.' in filename else filename,
        "created_at": datetime.now().isoformat(),
        "items": items,
        "total_items": len(items),
        "completed_items": 0,
        "progress_percent": 0
    }
    
    trackers[tracker_id] = tracker
    return tracker


def create_tracker(file_content: bytes, filename: str, content_type: str) -> Dict:
    """Create a tracker from uploaded file content"""
    text = ""
    
    if content_type == 'application/pdf' or filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(file_content)
    elif content_type.startswith('image/') or any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
        # For images, we'll use a simple approach for now
        # In production, this would use OCR or Gemini Vision
        text = "Image uploaded - manual parsing required"
    else:
        # Try to decode as text
        try:
            text = file_content.decode('utf-8')
        except:
            text = "Could not parse file content"
    
    return create_tracker_from_text(text, filename)


def get_all_trackers() -> List[Dict]:
    """Get all trackers"""
    return list(trackers.values())


def get_tracker(tracker_id: str) -> Optional[Dict]:
    """Get a specific tracker"""
    return trackers.get(tracker_id)


def update_tracker_item(tracker_id: str, item_id: str, completed: bool) -> Optional[Dict]:
    """Update a tracker item's completion status"""
    tracker = trackers.get(tracker_id)
    if not tracker:
        return None
    
    for item in tracker['items']:
        if item['id'] == item_id:
            item['completed'] = completed
            break
    
    # Recalculate progress
    completed_count = sum(1 for item in tracker['items'] if item['completed'])
    tracker['completed_items'] = completed_count
    tracker['progress_percent'] = round((completed_count / tracker['total_items']) * 100) if tracker['total_items'] > 0 else 0
    
    return tracker


def delete_tracker(tracker_id: str) -> bool:
    """Delete a tracker"""
    if tracker_id in trackers:
        del trackers[tracker_id]
        return True
    return False


# Demo tracker for testing
def create_demo_tracker():
    """Create a demo tracker with psychology theorists"""
    demo_items = [
        {"id": "demo1", "name": "Freud - Psychoanalytic Theory", "completed": False},
        {"id": "demo2", "name": "Jung - Analytical Psychology", "completed": False},
        {"id": "demo3", "name": "Adler - Individual Psychology", "completed": False},
        {"id": "demo4", "name": "Horney - Feminist Psychology", "completed": False},
        {"id": "demo5", "name": "Erikson - Psychosocial Development", "completed": False},
        {"id": "demo6", "name": "Dollard & Miller - Learning Theory", "completed": False},
        {"id": "demo7", "name": "Kelly - Personal Construct Theory", "completed": False},
        {"id": "demo8", "name": "Rogers - Person-Centered Therapy", "completed": False},
        {"id": "demo9", "name": "Maslow - Hierarchy of Needs", "completed": False},
        {"id": "demo10", "name": "Frankl - Logotherapy", "completed": False},
        {"id": "demo11", "name": "Rollo May - Existential Psychology", "completed": False},
        {"id": "demo12", "name": "Kohut - Self Psychology", "completed": False},
        {"id": "demo13", "name": "Fairbairn - Object Relations", "completed": False},
        {"id": "demo14", "name": "Winnicott - Transitional Objects", "completed": False},
        {"id": "demo15", "name": "Adlerian Theory - Applications", "completed": False},
    ]
    
    tracker_id = "demo_tracker"
    tracker = {
        "id": tracker_id,
        "name": "Psychology Theorists Study Guide",
        "created_at": datetime.now().isoformat(),
        "items": demo_items,
        "total_items": len(demo_items),
        "completed_items": 0,
        "progress_percent": 0
    }
    
    trackers[tracker_id] = tracker
    return tracker
