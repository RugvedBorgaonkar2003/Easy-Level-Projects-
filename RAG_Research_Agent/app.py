import streamlit as st

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

#Display uploaded files
if uploaded_files:
    st.success(f"✅Uploaded {len(uploaded_files)} file(s) successfully!")
    for file in uploaded_files:
        if file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            icon = "🖼️"
        else:
            icon = "📄"
        st.write(f"{icon} {file.name}") 

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

    #assistant response (placeholder)
    response = f"You asked: '{user_question}'. Once we connect the RAG backend, I'll answer from your papers!"

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
    