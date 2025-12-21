import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional 
import os

class VectorStore:
    """
    Manage vector database for RAG
    - Store document chunks with embeddings
    - Search by semantic similarity
    - Filter by metadata
    """

    def __init__(
        self,
        persist_directory: str = "./data/vectordb",
        collection_name: str = "research_papers",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize Vector Store
        
        Args:
            persist_directory: Where to save database
            collection_name: Name of collection (like a table)
            embedding_model: Model to convert text to vectors
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Create directory if not exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        print("✅ Embedding model loaded!")
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

         #Get or create collection
        self.collection = self.client.get_or_create_collection(
            name = collection_name,
            metadata = {"description" : "Research paper chunks with metadata"}

        )
        print(f"✅ Vector store ready! Collection: {collection_name}")

    #Store the chunks from the pdf processor and add chunks to vector store
    def add_chunks(
            self,
            chunks : List[Dict],
            file_name : str
    ) -> int:
        """
        Add document chunks to vector store
        
        Args:
            chunks: List of chunks from PDFProcessor
                [
                    {
                        'text': 'chunk text...',
                        'metadata': {'section': 'intro', 'page': 1, ...}
                    },
                    ...
                ]
            filename: Name of source PDF file
            
        Returns:
            Number of chunks added
        """

        #Check if chunks are their or not
        if not chunks:
            print("No chunks to add.")
            return 0
        
        #prepare data for chromadb
        metadatas = []
        texts = []
        ids = []

        for i, chunk in enumerate(chunks):
            #Extract text
            chunk_text = chunk.get("text"," ")

            if not chunk_text.strip():  #it checsk if the chunk is empty or only have space becuase it build noise in embeddings
                continue
                
            #Extract metadata
            chunk_metadata = chunk.get("metadata",{})

            ##add file name to metadata
            chunk_metadata["filename"] = file_name

            #Create unique chunk id
            chunk_id = f"{file_name}_chunk_{i}"

            texts.append(chunk_text)
            metadatas.append(chunk_metadata)
            ids.append(chunk_id)

            #Generate embeddings and store
            print(f"Adding {len(texts)} chunks to vector store...")

            #Convert texts to embeddings

            embeddings = self.embedding_model.encode(
                texts, 
                show_progress_bar = True,
                convert_to_numpy= True
            )

            #Add to collection
            self.collection.add(
                documents=texts,
                embeddings=embeddings.tolist(), #tolist() because vector database always excepts in list.
                metadatas=metadatas, 
                ids=ids
            )

            print(f"✅ Added {len(texts)} chunks successfully!")
        return len(texts)
    
    # Search for similar chunks 
    def search(
            self,
            query: str,
            n_results :  int =3,
            filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for relevant chunks using semantic similarity
        
        Args:
            query: User's question
            n_results: How many chunks to return
            filters: Metadata filters
                {
                    'section': 'introduction',
                    'filename': 'paper1.pdf'
                }
                
        Returns:
            List of relevant chunks with metadata:
            [
                {
                    'text': 'chunk text...',
                    'metadata': {...},
                    'similarity': 0.85
                },
                ...
            ]  
        """
        #Check if collection is empty
        if self.collection.count() ==0:
            print("⚠️ Vector store is empty. Please add documents first.")
            return []

        #Generate embedding for query
        query_embedding = self.embedding_model.encode(
            query,
            convert_to_numpy=True
        ).tolist()

        #build metadata fillter for chromadb
        where_filters = None
        if filters:
            where_conditions = []

            #filters by section
            if filters.get("section"):
                where_conditions.append({
                    "section": {"$eq": filters["section"]}
                })
            #filters by filename

            if filters.get("filename"):
                where_conditions.append({
                    "filename": {"$eq": filters["filename"]}
                })
            
            #combine conditions with AND
            if where_conditions:
                if len(where_conditions)==1:
                    where_filters = where_conditions[0]
                else:
                    where_filters = {"$and" : where_conditions}

        #search in chromada
        results = self.collection.query(
            query_embeddings = [query_embedding],
            n_results = n_results,
            where = where_filters
        )

        """
        results = {
    'documents': [
        ['chunk text 1', 'chunk text 2', 'chunk text 3']
    ],
    'metadatas': [
        [
            {'filename': 'a.pdf', 'section': 'intro'},
            {'filename': 'a.pdf', 'section': 'method'},
            {'filename': 'b.pdf', 'section': 'results'}
        ]
    ],
    'distances': [
        [0.12, 0.27, 0.45]
    ],
    'ids': [
        ['a_chunk_1', 'a_chunk_4', 'b_chunk_2']
    ]
}
        """

        #format result
        formatted_result = []

        if results["documents"] and results["documents"][0]:
            for i , doc in enumerate(results["documents"][0]):
                formatted_result.append({
                    "text":doc,
                    "metadata": results["metadatas"][0][i],
                    "similarity": 1 - results["distances"][0][i],   #Convert distance to similarity
                    "chunk_id":results["ids"][0][i]
                })
        return formatted_result
    
    #Helper function to delete all the chunks from a specific document

    def delete_document(self, filename:str) -> bool:
        """delete all the chunks from specific documents"""

        try: 
            #get all the ids from the document
            result = self.collection.get(
                where = {"filename": {"$eq": filename}},
            )

            #find the ids
            if result["ids"]:
                self.collection.delete(ids = result["ids"])
                print(f"✅ Deleted {len(result['ids'])} chunks from {filename}")
                return True
            else:
                print(f"No chunks found for {filename}")
                return False
        except Exception as e:
            print(f"Error deleting chunks from {filename}: {e}")
            return False
    
    #clear the database completely
    def clear_all(self) -> bool:
        """Clear the entire vector store"""
        try:
            self.client.delete_collection(self.collection_name)
            
            self.collection = self.client.create_collection(
                name=self.collection_name)
            print("✅ Cleared the entire vector store.")
            return True
        except Exception as e:
            print(f"❌ Error clearing store: {e}")
            return False
        
    def get_stats(self) -> Dict:
        """Get the statistics of vector store"""

        count = self.collection.count()

        if count>0:
            results = self.collection.get()

            filenames = set(meta.get("filename","unknown") for meta in results["metadatas"]) 
        else:
            filenames = set()

        return {
            "total_chunks": count,
            "unique_documents": len(filenames),
            "documents": list(filenames)
        }