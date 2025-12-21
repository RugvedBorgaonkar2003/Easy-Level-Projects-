import streamlit as st
from utils.vector_store import VectorStore
from utils.pdf_processor import PDFProcessor
from rag_agent import RAGAgent


#page config
st.set_page_config(
    page_title = "Research Buddy",
    page_icon = "📚",
    layout = "centered")

#custom css (Chat Bubbles)
st.markdown(
    """
    <style>
    /*Chat-Container*/
    .chat-container{
    padding:10px;
    margin:10px;
    }
    /* User message (right side, green) */
    .user-message {
        background-color: #DCF8C6;
        color: #000;
        padding: 12px 16px;
        border-radius: 18px;
        margin: 8px 0;
        max-width: 70%;
        float: right;
        clear: both;
        word-wrap: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    /* AI message (left side, gray) */
    .ai-message {
        background-color: #F0F0F0;
        color: #000;
        padding: 12px 16px;
        border-radius: 18px;
        margin: 8px 0;
        max-width: 70%;
        float: left;
        clear: both;
        word-wrap: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    /* Avatar styling */
    .avatar {
        font-size: 24px;
        margin: 0 8px;
    }
    
    /* Clear floats */
    .clearfix::after {
        content: "";
        display: table;
        clear: both;
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .ai-message {
            background-color: #2D2D2D;
            color: #E5E5E5;
        }
        .user-message {
            background-color: #056162;
            color: #E5E5E5;
        }
    }
}
    </style>
    """,
    unsafe_allow_html=True
)

#initialize componenets(only once per session)
@st.cache_resource
def initialize_components():
    """Initialize PDF processor, vector store, and RAG agent"""
    print("🔧 Initializing components...")

    #initialize pdf processor
    pdf_processor = PDFProcessor(chunk_size=500)

    #initialize vector store
    vector_store = VectorStore(
        persist_directory="./data/vectordb",
        collection_name="research_papers",
        embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    )

    rag_agent = RAGAgent(
        vector_store=vector_store,
        llm_model="llama3.2:3b",
        temperature = 0.7
    )

    print("✅ All components initialized!")
    return pdf_processor, vector_store, rag_agent
#load components
pdf_processor, vector_store, rag_agent = initialize_components()


def get_active_filters():
    """Get active filters from sidebar checkboxes"""
    filters = {}
    
    # Collect selected sections
    selected_sections = []
    
    # You'll need to store these in session state from sidebar
    # For now, return None (no filters)
    # We'll enhance this after basic version works
    
    return None  # No filters for now, add later

#document processing function
def process_documents(files):
    """Process uploaded documents and add to vector store"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_files = len(files)
    for idx, file in enumerate(files):
        #udate progress

        progress = (idx + 1) / total_files
        progress_bar.progress(progress)
        status_text.text(f"Processing file {idx + 1} of {total_files}: {file.name}")

        try:
            #only process pdf for now
            
            if not file.name.lower().endswith('.pdf'):
                st.warning(f"⚠️ Skipping {file.name} - Only PDFs supported in v1")
                continue
            #process pdf

            with st.spinner(f"📖 Extracting content from {file.name}..."):
                result = pdf_processor.process_pdf(file)
            
            #Add chunks to vector store
            with st.spinner(f"💾 Storing {file.name} in database..."):
                num_chunks = vector_store.add_chunks(
                    chunks = result['chunks'],
                    file_name = file.name)
                
            #mark as processed
            st.session_state.processed_files.add(file.name) 

            #show success
            st.success(f"✅ {file.name}: Processed {num_chunks} chunks, {len(result['images'])} images, {len(result['tables'])} tables")

        except Exception as e:
            st.error(f"❌ Error processing {file.name}: {str(e)}")
            continue

#session state for tracking processed files
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role" : "assistant",
            'content': 'Hello! 👋 Upload your research papers and ask me anything!'
        }
    ]

#Intialize Chat history with welcome message and tools menu session state
if "show_tools_menu" not in st.session_state:
    st.session_state.show_tools_menu = False    
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role" : "assistant",
            "content" : "Hello! 👋 Upload your research papers and I'll help you understand them."
        }
    ]

#Display chat messages function
def display_message(role, content):
    if role == "user":
        st.markdown(f"""
        <div class="user-container">
            <div class="user-message">
                {content}
            </div>
            <span class="avatar">👤</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="ai-container">
            <span class="avatar">🤖</span>
            <div class="ai-message">
                {content}
            </div>
        </div>
        """, unsafe_allow_html=True)

#learning tools handling function
def handle_learning_tools(tool_type):
    """Handles the learning tools button clicks """
    #add message to chat
    tool_message = {
        "quiz": "🎯 Generating quiz from your papers...",
        "flashcards": "🗂️ Creating flashcards...",
        "case_study": "📄 Generating case study...",
        "questions": "❓ Extracting important questions...",
        "notes": "📓 Creating study notes..."
    }
    st.session_state.messages.append({
        "role" : "assistant",
        "content" : tool_message.get(tool_type, "Processing...")
    })

#Centered title
st.markdown(
    """
    <h1 style="text-align: center;">Research Buddy 📚</h1>
    """,
    unsafe_allow_html=True
)

#Welcome message
st.markdown(
    """
    <p1 style="text-align: center; font-size: 18px;">
    Welcome to Research Buddy! 
    Upload your documents and let assistant help you with research 
    </p1>
    """,
    unsafe_allow_html=True
)

#upload section in main page
st.subheader("Upload your document 📄")
uploaded_files = st.file_uploader (
    "Upload you documents or images here",
    type = ["pdf", "docx", "txt", "png", "jpg", "jpeg"],
    accept_multiple_files = True
)
files_to_process = []
#Display uploaded files
if uploaded_files:
    st.success(f"✅Uploaded {len(uploaded_files)} file(s) successfully!")
    for file in uploaded_files:
        if file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            icon = "🖼️"
        else:
            icon = "📄"
        st.write(f"{icon} {file.name}") 

        #check if file already processed
        if file.name in st.session_state.processed_files:
            st.write(f"{icon} {file.name} ✅ *Processed*")
        else:
            st.write(f"{icon} {file.name} ⏳ *Ready to process*")
            files_to_process.append(file)
        
        #process new files
        if files_to_process:
            if st.button("Process New Files", type = "primary"):
                process_documents(files_to_process)
         

st.divider()

st.subheader("💬Chat Here")

#display chat history
for message in st.session_state.messages:
    display_message(message["role"], message["content"])

#user_input
user_question = st.chat_input("Ask question about your document here")

if user_question:
    st.session_state.messages.append({
        "role" : "user",
        "content" : user_question
    })

#check if documents are processed
    if not  st.session_state.processed_files:
        response = "⚠️ Please upload and process some documents first before asking questions!"
    else:
        #get answer from RAG agent

        with st.spinner("🤔 Thinking..."):
            
            filters = get_active_filters()
            result = rag_agent.answer_question(
                question = user_question,
                n_chunks =3,
                filters = filters)
            
            #format response
            response = result['answer']

            #add sources if any
            if result['sources']:
                response += "\n\n" + rag_agent._format_sources(result['sources'])
        
    #append assistant response to chat history
    st.session_state.messages.append({
        "role" : "assistant",
        "content" : response
    })
    #rerun to show new messages
    st.rerun()


#sidebar desing(filterings and google search option)
with st.sidebar:
    st.header("Filters 📊")
    
    #section filters
    with st.expander("Filters by section 📃", expanded=False):
        filters_abstract = st.checkbox("Abstract", value=False)
        filters_introduction = st.checkbox("Introduction", value=False)
        filters_methods = st.checkbox("Methods/Methodology", value=False)
        filters_results = st.checkbox("Results", value=False)
        filters_discussion = st.checkbox("Discussion", value=False)
        filters_conclusion = st.checkbox("Conclusion", value=False)
    
    #Content Filter
    with st.expander("Filters by content type 📑",expanded=False):
        filters_figures = st.checkbox("Figures", value=False)
        filters_tables = st.checkbox("Tables", value=False)
        filters_references = st.checkbox("References", value=False)

    #Heading/topic dropdown
    with st.expander("Filter by Heading/Topic 🏷️", expanded=False):
        extracted_headings = ["All Headings"]  
        selected_heading = st.selectbox("Select specific headings", extracted_headings,index=0) 
        st.caption("Upload document to see headings")      
    st.divider()

    #Google search option
    st.subheader("Need More Info?🌐")
    search_query = st.text_input("Do Web Search Here",placeholder="Enter Your Search")

    if st.button("Search",use_container_width=True):
        if search_query:
            import webbrowser
            webbrowser.open(f"https://www.google.com/search?q={search_query}")

#tools menu in sidebar
with st.sidebar:
    st.divider()
    st.subheader("🎓 Learning Tools")
    if st.button("Generate Quiz", use_container_width=True):
        handle_learning_tools("quiz")
        st.rerun()
    
    if st.button("Create Flashcards", use_container_width=True):
        handle_learning_tools("flashcards")
        st.rerun()
    
    if st.button("Generate Case Study", use_container_width=True):
        handle_learning_tools("case_study")
        st.rerun()
    
    if st.button("Extract Important Questions", use_container_width=True):
        handle_learning_tools("questions")
        st.rerun()
    
    if st.button("Create Study Notes", use_container_width=True):
        handle_learning_tools("notes")
        st.rerun()  
    