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
        self.section_patterns =[
            r'^abstract',
            r'^introduction',
            r'^related\s+work',
            r'^literature\s+review',
            r'^background',
            r'^method(s|ology)?',
            r'^experiment(s|al\s+setup)?',
            r'^implementation',
            r'^result(s)?',
            r'^discussion',
            r'^conclusion(s)?',
            r'^future\s+work',
            r'^reference(s)?',
            r'^acknowledgment(s)?'
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

    #this is the first function to extract text with structure
    def _extract_text_with_structure(self, pdf_bytes) -> List[Dict]:
        """
        Extract text from PDF with structure information
        Returns: List of blocks metadata
        [
            {
                text : "paragraph text",
                "page_num": 1,
                "section": "Introduction",
                "Heading": background,
                "font_size": 12}]
        """
        text_blocks = []
        current_section = "Unknown"
        #open pdf from bytes
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        
        #going page to page
        for page_num,page in enumerate(doc,start=1):
            #.get_text("dict") means storing the page etracts in dictionary format
            # and ["blocks"] is dictionery key name having type 0(text) and type1(images) as storage. It is list of dictionaries.
            blocks=page.get_text("dict")["blocks"]

            #loop through blocks
            for block in blocks:
                #Skip the image/non text blocks for now
                if block['type'] != 0:
                    continue
                #collect text here if type is 0
                block_text = ""

                """Here we have set max_font_size to 0 to track the largest font size in the block.
                specially headings. .get_text('dict")["blocks"] gives list of dictionaries having span in it means it is
                list of dictioneries and continuos piece of text with same font, color.
                """
                max_font_size = 0 

                #Extract text line by line
                for line in block.get("lines",[]):  
                    for span in line.get("spans",[]):
                        #extract text and font size
                        text=span.get("text","")
                        font_size = span.get("size",0)
        
                        #store text and max font size
                        if text:
                            block_text = text+" "
                            #keeping the track of max font size
                            max_font_size = max(max_font_size,font_size)

                block_text = block_text.strip()
                #skip the block with no text
                if not block_text:
                    continue

                #detect if this heading (larger font size)
                is_heading = max_font_size >12  #threshold for heading

                #Detect section based on headings
                if is_heading:
                    detected_section = self._detect_section(block_text)
                    if detected_section:
                        current_section = detected_section

                #store everyting in structured format
                text_blocks.append({
                    'text': block_text,
                    'page': page_num,
                    'section': current_section,
                    'heading': block_text if is_heading else None,
                    'font_size': max_font_size,
                    'is_heading': is_heading
                })
        
        doc.close()
        return text_blocks
                
    def _detect_section(self, text: str) -> str:
        """
        Detect which section headings belongs to
        Agrs: text: Heading text
        Returns: section name or None
        """                     
        text_lower = text.lower().strip()

        for pattern in self.section_patterns:
            if re.match(pattern, text_lower):
                #extract section name from pattern
                return text_lower.split()[0]
                        
            return None

    #Now lets build _extract_images function.
    def _extract_images(self,pdf_bytes)-> List[Dict]:
        """
        Extract images from pdf
        returns 
        List of images with metadata
        [
            {
            "image":<PILL image>,
            "Page" : 2,
            "Caption": "Figure 1: Sample Image",
            "Position": {"x":100,"y":200},
            "Size": {"width":300,"height":400}
            }]
        """
        #opening pdf
        doc = pymupdf.open(stream=pdf_bytes,file_type = "pdf")
        images = []

        for page_num,page in enumerate(doc, start=1):
            image_list=page.get_images()

            for img_index,img in enumerate(image_list):
                try:
                    xref=img[0] #extract xref number

                    base_image = doc.extract_image(xref)
                    image_bytes=base_image["image"]

                    #convert to PIL image
                    pil_image = Image.open(io.BytesIO(image_bytes))

                    img_rect = page.get_image_bbox(img) #complete image metadata

                    #return the caption
                    caption = self._find_image_caption(page,img_rect)
                    images.append({
                        'image_data': pil_image,
                        'page': page_num,
                        'caption': caption,
                        'image_index': img_index,
                        'position': {
                            'x': img_rect.x0,
                            'y': img_rect.y0
                        },
                        'size': {
                            'width': int(img_rect.width),
                            'height': int(img_rect.height)
                        }
                    })

                except Exception as e:
                    #Skip images that can't be extracted
                    print(f"Could not extract image on page {page_num}: {e}")
        doc.close()
        return images
    


    def _find_image_caption(self, page, img_rect) -> str:
        """
        Find caption for image based on its position
        ARGS: page: pymupdf page object
              img_rect: rectangle of image
        Returns: caption text or empty string
        """
        search_area = pymupdf.Rect(
            img_rect.x0,
            img_rect.xy,
            img_rect.x1,
            img_rect.y1 + 50  #50 pixels below image    

        )

        #get text from search area
        text_instance = page.get_text("text",clip=search_area)

        if text_instance:
            #clean the text
            caption = text_instance.strip()

            #Check if it looks like caption
            caption_patterns = [
                r'^figure\s+\d+',
                r'^fig\.\s+\d+',
                r'^table\s+\d+',
                r'^chart\s+\d+'
            ]

            for pattern in caption_patterns:
                if re.match(pattern, caption.lower()):
                    return caption
        return None
    
    #Now lets build function to extract tables
    def _extract_tables(self,pdf_bytes)-> List[Dict]:
        """
        Extract all tables from PDF
        Return list of tables with metadata
        [{
            'data': [[row1], [row2], ...],  # 2D list
                'page': 3,
                'caption': 'Table 1: Results comparison',
                'num_rows': 5,
                'num_cols': 3
        }]
        """
        tables=[]
        #use pdfplumber to extract tables. It is better that pymupdf
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num,page in enumerate(pdf.pages, start=1):
                #extract tables from the page
                page_tables = page.extract_tables()

                if not page_tables:
                        continue
                for table_index, table_data in enumerate(page_tables):
                    #skip empty or 1 row table
                    if not table_data or len(table_data)<2:
                        continue
                    #clean table data
                    cleaned_table = []
                    
                    for row in table_data:
                        cleaned_row = [cell.strip() if cell else "" for cell in row]
                        cleaned_table.append(cleaned_row)

                    #find caption for table
                    caption = self._find_table_caption(page, table_index)

                    #store table with metadata
                    tables.append({
                        'data': cleaned_table,
                        'page': page_num,
                        'caption': caption,
                        'table_index': table_index,
                        'num_rows': len(cleaned_table),
                        'num_cols': len(cleaned_table[0]) if cleaned_table else 0,
                        'headers': cleaned_table[0] if cleaned_table else []
                    })
        return tables
    

    #helper function for finding caption for table
    def _find_table_caption(self, page, table_index:int) -> str:
        """
        It finds the caption of the table

        ARGS: page: pdfplumber page object
              table_index: index of the table on the page
        Returns: caption text or empty string
        """

        #get all the text on page
        text = page.get_text()

        if not text:
            return None
        #split text into lines
        lines = text.split('\n')

        #look for the lines same as table patters
        table_patterns = [
            r'table\s+\d+',
            r'tab\.\s+\d+',
            r'tbl\s+\d+'
        ]

        for i , line in enumerate(lines):
            #clean te lines
            line_lower = line.lower().strip()

            for pattern in table_patterns:
                if re.search(pattern,line_lower):
                    #found the table caption
                    #Return this line or next line as caption

                    caption = line.strip()
                    #check if the next line has caption but it should not end with peroid

                    if i+1<len(lines) and not caption.endswith('.'):
                        next_line = lines[i+1].strip()

                        #if next line is short , it's part of caption
                        if len(next_line)<100 and not next_line.startwith("Table"):
                            caption += " "+next_line
                    return caption
        return None
    
    #Now lets create chunks 
    #It takes all the extracted texts and then divide them into 500 word chunks
    def _create_chunks(self, text_blocks:List[Dict])-> List[Dict]:
        """
        Split text into chunks using metadata

        ARGS: text_blocks: list of text from _extract_text_with_structure()
        
        Returns:
        List of text chunks with metadata
        [
                {
                    'text': 'chunk text...',
                    'metadata': {
                        'chunk_id': 0,
                        'section': 'introduction',
                        'page': 1,
                        'heading': 'Background',
                        'word_count': 487
                    }
                },
                ...
            ]


        """

        chunks = []
        current_chunk_text = []
        current_word_count = 0
        chunk_id = 0

        #track metadata for current chunk
        current_section = "unknown"
        current_page =1
        current_heading = None

        for block in text_blocks:
            #skip the headings themselves(we store them seperately)
            #We skipped heading because we don't want heading to be our main content. We need heading to keep it as track of 
            #particular section

            if block.get("is_heading",False):
                current_heading = block["text"]
                current_section = block["text"]
                current_page = block["page"]
                continue

            #get text and word count
            block_text = block["text"]
            block_word = len(block_text.split())

            #update tracking
            current_section = block["section"]
            current_page = block["page"]

            #check if chunk size exceeding 500 or not

            if current_word_count + block_word> self.chunks_size and current_chunk_text:
                #create chunk
                chunk_text = " ".join(current_chunk_text)

                chunks.append({
                    'text': chunk_text,
                    'metadata': {
                        'chunk_id': chunk_id,
                        'section': current_section,
                        'page': current_page,
                        'heading': current_heading,
                        'word_count': current_word_count
                    }
                })
            
                #reset for new chunk
                chunk_id +=1
                current_chunk_text = []
                current_word_count = 0
            
            #Add block to current chunk
            current_chunk_text.append(block_text)
            current_word_count += block_word

            #don't forget partially filled last chunk
        if current_chunk_text:
            chunk_text = " ".join(current_chunk_text)
            chunks.append({
            'text': chunk_text,
            'metadata': {
            'chunk_id': chunk_id,
            'section': current_section,
            'page': current_page,
            'heading': current_heading,
            'word_count': current_word_count
                    }
                })
        return chunks
    
    #Lets build extract headings function

    def _extract_headings(self, text_blocks:List[Dict])-> List[Dict]:

        """
        Extract all headings from text blocks
        ARGS : text_blocks: list of text blocks from _extract_text_with_structure()
        return :
        List of headings with metadata
        [
            {
                'heading': 'Introduction',
                'page': 1,
                'section': 'introduction'
            },
            ...
        ]
        """
        headings = []
        for block in text_blocks:
            if block.get("is_heading",False):
                headings.append({
                    'heading': block['text'],
                    'page': block['page'],
                    'section': block['section']
                })
        return headings
            

