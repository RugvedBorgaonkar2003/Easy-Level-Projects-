"""
RAG Agent -> It is the core logic through which we connect everything.
1. Takes user question
2. searches vector store
3. Generate answer using LLM
4. Handles multiple requests
"""

import ollama
from typing import List, Dict, Optional
from utils.vector_store import VectorStore

class RAGAgent:
    """
    RAG Agent that:
    - Searches relevant chunks
    - Generates answers with LLM
    - Provides source citations
    - Routes different request types
    """

    def __init__(
            self, 
            vector_store: VectorStore,
            llm_model: str = "llama3.2:3b",
            temperature: float = 0.7,
    ):
        """
        Initialize RAG Agent
        
        Args:
            vector_store: VectorStore instance
            llm_model: Ollama model name
            temperature: LLM creativity (0=focused, 1=creative)
        """
        self.vector_store = vector_store
        self.llm_model = llm_model
        self.temperature = temperature

        #verify ollama is available
        try:
            ollama.list()
            print(f"✅ RAG Agent initialized with model: {llm_model}")
        except Exception as e:
            print(f"⚠️ Warning: Ollama might not be running: {e}")
    

    #Main function for answering questions
    def answer_question(
            self, 
            question: str,
            n_chunks: int = 3,
            filters: Optional[Dict] = None) -> Dict:
        """
        Answer a question based on stored documents
        
        Args:
            question: User's question
            n_chunks: How many chunks to retrieve
            filters: Metadata filters (section, filename, etc.)
            
        Returns:
            {
                'answer': 'Generated answer text',
                'sources': [list of source chunks],
                'query': 'original question'
            }
        """

        #step 1: search for relevant chunks
        print(f"🔍 Searching for the {question}")

        relevant_chunks = self.vector_store.search(
            query=question,
            n_results=n_chunks,
            filters=filters)
        
        if not relevant_chunks:
            return {
                'answer': "I couldn't find any relevant information in the uploaded documents. Please make sure you've uploaded PDFs first.",
                'sources': [],
                'query': question
            }
        
        #step 2: build context from chunks
        context = self._build_context(relevant_chunks)

        #step3: Create prompt for LLM
        prompt = self._create_prompt(question, context)

        #step 4: Generate answer using LLM
        print("🤖 Generating answer with LLM...")
        answer  = self._generate_answer(prompt)

        #step 5: return answers with sources
        return {
            'answer': answer,
            'sources': relevant_chunks,
            'query': question
        }
    
    #First helper function
    def _build_context(self, chunks: List[Dict]) -> str:
        """
        Build context string from relevant chunks
        
        Args:
            chunks: List of relevant chunks with metadata
            
        Returns:
            Combined context string
        """
        context_parts = []
        for i , chunk in enumerate(chunks,start=1):
            
            text = chunk["text"]
            metadata = chunk["metadata"]

            #format [Source 1- Page 2 , Section: Introduction]

            source_info = f"[Source{i} - "

            if "page" in metadata:
                source_info += f"Page {metadata['page']}"
            
            if "section" in metadata:
                source_info += f", Section: {metadata['section']}"

            source_info += "]"

            context_parts.append(f"{source_info}\n{text}\n")
            
            return "\n---------------\n".join(context_parts)
        
    #helper function 2 _create_prompt
    def _create_prompt(self, question: str, context: str) -> str:
        """
        Create prompt for LLM
        
        Args:
            question: User's question
            context: Combined context from chunks
            
        Returns:
            Formatted prompt
        """

        prompt = f"""
        **Role** : You are Nick the AI teacher , helping user to answer the question based on the document/documents provided.
        Qualities:
        - You are friendly and honest teacher that gives answer to every answer polietly. 
        - You help user to completely understand document(s) he/she uploaded. 
        - You always provide source citation for every answer you give.
        - If you don't know the answer, you honestly say that you don't know.

        context: {context}
        Question: {question}
        Answer:

        **Instructions**:
        - Use the provided context to answer the question.
        - Ask the user for more information if the context is insufficient.
        - Always ask the user at the end if he/she has understood the answer or needs more clarification.
        - If the question is unrelated to the document(s), politely inform the user that you can only answer questions related to the provided document(s).
        - As a teacher , ask user a follow-up question to ensure understanding.
        - Give concise and clear answers.
        
        **Sessoin Flow**:
        - Introduce yourself as Nick the AI teacher when you answer only *first* question. Strictly Don't reintroduce yourself again.
        - Also inform user about the web search option in sidebar. Tell them as " If you want to get information beyond the document(s) you uploaded, please use the web search option in the sidebar."
        - If the user went through every content of document(s), give user list of topics he/she studied in the document(s).
        
        **Quiz taking instructions**:
        - If user wants to take quiz , create a 10 question quiz based on the document(s) he/she uploaded.
        - Divide the easy/medium/hard questions in ratio of 4:4:2.
        - Provide the quiz in a format where question is followed by four options (A, B, C, D).
        - Don't ask all the quiz question at once. Ask 1 question at a time and wait for user's answer.
        - At the end of the quiz, provide the score.
        - After giving the score, ask the user that you should answer user's wrong answer or not.
        - If user wants to understand his/her wrong answers, provide detailed explanation for each wrong answer.
        - End the quiz session by appreciating the user for taking the quiz.

        **Flashcards Generating  instructions**:
        - When user wants to generate flashcards, create flashcards based on the questions user asked during the session.
        - Each flashcard should have a question on one side and the answer on the other side.
        - Provide the flashcards in a clear format.
        - Make concise and precise flashcards that are easy to remember.

        **Case Study Generating  instructions**:
        - When user wants to generate case study, create a detailed case study based on the document(s) he/she uploaded.
        - The case study should include real-world applications, challenges, and solutions related to the topics covered in the document(s).
        - Include no jargon and make it easy to understand.
        - Provide the case study in a structured format with headings and subheadings.

        **Questions Generating instructions**:
        - When user wants to generate questions, create a list oof max 10 questions based on the document(s) he/she uploaded.
        - Follow the ratio of easy/medium/hard questions as 4:4:2.
        - Questions should be based on QA pairs of user and yourself during the session.
        - Questions should be clear and concise.

        **Notes Generating instructions**:
        - When user wants to generate notes, create detailed notes based on the document(s) he/she uploaded.
        - Notes should cover all the important points from the document(s).
        - Provide the notes in a structured format with headings and bullet points.
        - Notes should be easy to understand and remember.

        **End of session**:
        - End session by thanking the user for using You, Nick the AI teacher.
        """
        return prompt
    
    #helper function 3 _generate_answer
    def _generate_answer(self, prompt:str) -> str:
        """
        Generate answer using Ollama LLM
        
        Args:
            prompt: Complete prompt with context and question
            
        Returns:
            Generated answer text
        """
        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': self.temperature,
                }
            )

            answer = response["message"]["content"]
            return answer.strip()

        except Exception as e:
            return f"Error generating answer: {str(e)}. Please make sure Ollama is running."

    #helper function 4 to format search results

    def _format_sources(self, sources:List[Dict]) -> str:
        """
        Format source citations for display
        
        Args:
            sources: List of source chunks
            
        Returns:
            Formatted string with sources
        """

        if not sources:
            return "No sources found."
        
        formatted = "**Sources:**\n\n"

        for i, source in enumerate(sources, start=1):
            metadata = source["metadata"]
             # Build source line
            source_line = f"{i}. "
            
            if 'filename' in metadata:
                source_line += f"📄 {metadata['filename']}"
            
            if 'page' in metadata:
                source_line += f" (Page {metadata['page']})"
            
            if 'section' in metadata:
                source_line += f" - {metadata['section'].title()}"
            
            if 'similarity' in source:
                similarity_percent = int(source['similarity'] * 100)
                source_line += f" - Relevance: {similarity_percent}%"
            
            formatted += source_line + "\n"
        
        return formatted

                
        