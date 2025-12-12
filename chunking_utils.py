#!/usr/bin/env python3
"""
Smart Chunking Utilities
Extracted from vector_librarian.py for shared use across the system.
"""

import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class DocumentChunk:
    """Represents a chunk of a document for vector indexing"""
    chunk_id: str
    file_path: str
    chunk_index: int
    content: str
    chunk_type: str  # 'header', 'body', 'conclusion', 'metadata'
    metadata: Dict[str, Any]

class SmartChunker:
    """
    Intelligent document chunking for your specific file types
    Understands entertainment contracts, scripts, business docs
    """
    
    def __init__(self):
        # Contract section patterns
        self.contract_patterns = {
            'header': [r'agreement', r'contract', r'parties', r'whereas'],
            'compensation': [r'payment', r'salary', r'fee', r'compensation', r'royalty'],
            'terms': [r'term', r'duration', r'period', r'expiry', r'termination'],
            'exclusivity': [r'exclusiv', r'non-compete', r'restriction', r'limitation'],
            'rights': [r'rights', r'license', r'permission', r'usage', r'territory'],
            'obligations': [r'shall', r'must', r'required', r'responsible', r'duty']
        }
        
        # Creative content patterns
        self.creative_patterns = {
            'scene': [r'scene \d+', r'act \d+', r'chapter \d+'],
            'dialogue': [r':', r'said', r'spoke', r'replied'],
            'action': [r'fade in', r'cut to', r'sound', r'music'],
            'character': [r'character', r'protagonist', r'narrator']
        }
        
        # Business document patterns
        self.business_patterns = {
            'financial': [r'revenue', r'profit', r'loss', r'tax', r'expense'],
            'legal': [r'liability', r'indemnify', r'breach', r'default'],
            'operational': [r'procedure', r'process', r'workflow', r'responsibility']
        }
        
        # Email patterns
        self.email_patterns = {
            'meeting': [r'meeting', r'schedule', r'calendar', r'appointment'],
            'business': [r'contract', r'deal', r'agreement', r'negotiation'],
            'personal': [r'thank you', r'thanks', r'regards', r'best'],
            'urgent': [r'urgent', r'asap', r'immediate', r'deadline'],
            'creative': [r'script', r'project', r'creative', r'production']
        }
    
    def chunk_document(self, content: str, file_path: str, max_chunk_size: int = 200) -> List[DocumentChunk]:
        """Smart chunking based on document type and content structure"""
        chunks = []
        file_type = self._detect_file_type(content, file_path)
        
        if file_type == 'contract':
            chunks = self._chunk_contract(content, file_path, max_chunk_size)
        elif file_type == 'script':
            chunks = self._chunk_script(content, file_path, max_chunk_size)
        elif file_type == 'business':
            chunks = self._chunk_business_doc(content, file_path, max_chunk_size)
        elif file_type == 'email':
            chunks = self._chunk_email(content, file_path, max_chunk_size)
        else:
            chunks = self._chunk_generic(content, file_path, max_chunk_size)
        
        return chunks
    
    def _detect_file_type(self, content: str, file_path: str) -> str:
        """Detect document type for appropriate chunking strategy"""
        content_lower = content.lower()
        filename = Path(file_path).name.lower()
        
        # Check for contract indicators
        contract_indicators = ['agreement', 'contract', 'whereas', 'party', 'consideration']
        if any(indicator in content_lower for indicator in contract_indicators):
            return 'contract'
        
        # Check for script indicators
        script_indicators = ['scene', 'fade in', 'cut to', 'dialogue', 'character']
        if any(indicator in content_lower for indicator in script_indicators):
            return 'script'
        
        # Check for business document indicators
        business_indicators = ['revenue', 'financial', 'invoice', 'payment', 'commission']
        if any(indicator in content_lower for indicator in business_indicators):
            return 'business'
        
        # Check for email indicators
        if 'from:' in content_lower and 'to:' in content_lower:
            return 'email'
        
        return 'generic'
    
    def _chunk_contract(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Chunk entertainment contracts by logical sections"""
        chunks = []
        
        # Split into paragraphs first
        paragraphs = content.split('\n\n')
        current_chunk = ""
        current_type = "body"
        chunk_index = 0
        
        for para in paragraphs:
            para_lower = para.lower()
            
            # Determine chunk type based on content
            chunk_type = "body"  # default
            for section, patterns in self.contract_patterns.items():
                if any(pattern in para_lower for pattern in patterns):
                    chunk_type = section
                    break
            
            # If adding this paragraph would exceed size, create chunk
            if len(current_chunk.split()) + len(para.split()) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                        file_path=file_path,
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        chunk_type=current_type,
                        metadata={'section': current_type, 'doc_type': 'contract'}
                    ))
                    chunk_index += 1
                
                current_chunk = para
                current_type = chunk_type
            else:
                current_chunk += "\n\n" + para
                if chunk_type != "body":  # Priority to more specific types
                    current_type = chunk_type
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                file_path=file_path,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                chunk_type=current_type,
                metadata={'section': current_type, 'doc_type': 'contract'}
            ))
        
        return chunks
    
    def _chunk_script(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Chunk scripts by scenes/sections"""
        chunks = []
        
        # Try to split by scene markers
        scene_splits = re.split(r'(SCENE \d+|ACT \d+|FADE IN|CUT TO)', content, flags=re.IGNORECASE)
        
        current_chunk = ""
        chunk_index = 0
        
        for i, section in enumerate(scene_splits):
            if len(current_chunk.split()) + len(section.split()) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                        file_path=file_path,
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        chunk_type="scene",
                        metadata={'doc_type': 'script', 'scene_number': chunk_index}
                    ))
                    chunk_index += 1
                current_chunk = section
            else:
                current_chunk += section
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                file_path=file_path,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                chunk_type="scene",
                metadata={'doc_type': 'script', 'scene_number': chunk_index}
            ))
        
        return chunks
    
    def _chunk_business_doc(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Chunk business documents by topics"""
        chunks = []
        
        # Split by sections/headers
        lines = content.split('\n')
        current_chunk = ""
        current_type = "general"
        chunk_index = 0
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect section type
            section_type = "general"
            for section, patterns in self.business_patterns.items():
                if any(pattern in line_lower for pattern in patterns):
                    section_type = section
                    break
            
            # Check if we need to create a new chunk
            if len(current_chunk.split()) + len(line.split()) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                        file_path=file_path,
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        chunk_type=current_type,
                        metadata={'section': current_type, 'doc_type': 'business'}
                    ))
                    chunk_index += 1
                current_chunk = line
                current_type = section_type
            else:
                current_chunk += "\n" + line
                if section_type != "general":
                    current_type = section_type
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                file_path=file_path,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                chunk_type=current_type,
                metadata={'section': current_type, 'doc_type': 'business'}
            ))
        
        return chunks
    
    def _chunk_email(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Chunk emails by headers and content sections"""
        chunks = []
        
        # Split email into header and body sections
        lines = content.split('\n')
        header_section = ""
        body_section = ""
        in_body = False
        
        for line in lines:
            if not in_body and (line.startswith('From:') or line.startswith('To:') or line.startswith('Subject:')):
                header_section += line + '\n'
            elif line.strip() == "" and not in_body:
                in_body = True
            elif in_body:
                body_section += line + '\n'
        
        chunk_index = 0
        
        # Create header chunk
        if header_section.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                file_path=file_path,
                chunk_index=chunk_index,
                content=header_section.strip(),
                chunk_type="header",
                metadata={'section': 'header', 'doc_type': 'email'}
            ))
            chunk_index += 1
        
        # Chunk body by email patterns
        if body_section.strip():
            body_lower = body_section.lower()
            
            # Determine email type
            email_type = "general"
            for section, patterns in self.email_patterns.items():
                if any(pattern in body_lower for pattern in patterns):
                    email_type = section
                    break
            
            # Split body into chunks
            words = body_section.split()
            for i in range(0, len(words), max_chunk_size):
                chunk_words = words[i:i + max_chunk_size]
                chunk_content = ' '.join(chunk_words)
                
                chunks.append(DocumentChunk(
                    chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                    file_path=file_path,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    chunk_type=email_type,
                    metadata={'section': email_type, 'doc_type': 'email'}
                ))
                chunk_index += 1
        
        return chunks
    
    def _chunk_generic(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Generic chunking for other document types"""
        chunks = []
        words = content.split()
        
        for i in range(0, len(words), max_chunk_size):
            chunk_words = words[i:i + max_chunk_size]
            chunk_content = ' '.join(chunk_words)
            
            chunk = DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{i // max_chunk_size}",
                file_path=file_path,
                chunk_index=i // max_chunk_size,
                content=chunk_content,
                chunk_type="content",
                metadata={'doc_type': 'generic', 'word_offset': i}
            )
            chunks.append(chunk)
        
        return chunks
