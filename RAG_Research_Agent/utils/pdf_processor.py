"""
PDF Processor: Extract text, charts , images from PDF files with metadata
"""

import pymupdf
import pdfplumber
from typing import List, Dict, Any
from PIL import Image
import re
import io

class PDFProcessor:
    """
    Process PDF to extract:
    text chunks, images and figures, tables and charts , section headings
    """

    def __init__(self, chunk_size: int = 500):
        """
        Initialize PDF Processor
        ARGS: Chunk Size : Number of words per text chunk(500)
        """
        self.chunk_size = chunk_size
        
        #common patterns in research papers
        self.section_patterns = [
            r'^\d+\.\s+Abstract',
            r'^\d+\.\s+Introduction',
            r'^\d+\.\s+Related Work',
            r'^\d+\.\s+Methodology',
            r'^\d+\.\s+Experiments',
            r'^\d+\.\s+Results',
            r'^\d+\.\s+Discussion',
            r'^\d+\.\s+Conclusion',
            r'^\d+\.\s+References'
        ]

    #Main Processing Function
    #This function will give output as dictionary having key as string but values can be any 
    def process_pdf(self, pdf_file) -> Dict[str,Any]:
        """
        Main function : Process Entire PDF
        ARGS: pdf_file : Uploaded PDF file(from Streamlit)
        returns: Dictionary with text chunks, images, tables, sections
        """
        #Read PDF bytes
        pdf_bytes = pdf_file.read()

        #extract text and structure
        text_data = self._extract_text_with_structure(pdf_bytes)

        #extract images
        images = self._extract_images(pdf_bytes)

        #extract tables
        tables = self._extract_tables(pdf_bytes)

        #create chunks with metadata
        chunks = self._create_chunks_with_metadata(text_data)

        #extract all headings for dropdown
        headings = self._extract_headings(text_data)

        return {
            "chunks": chunks,
            "images": images,
            "tables": tables,
            "headings": headings,
            "file_name": pdf_file.name
        }
