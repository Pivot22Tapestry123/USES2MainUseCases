import traceback
import streamlit as st
import os
import json
import warnings
import io
from datetime import datetime
from crewai import Agent, Task, Crew
from langchain.chat_models import AzureChatOpenAI
from docx import Document
from docx.shared import Pt

# Suppress warnings
warnings.filterwarnings('ignore')

# Helper function to load and save configurations
def load_config():
    try:
        with open("agent_task_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(config):
    with open("agent_task_config.json", "w") as f:
        json.dump(config, f)

# Function to read content from a Word document
def read_docx(file):
    doc = Document(file)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

# Load persisted configurations at startup
config = load_config()

# Streamlit UI
st.title("Research Article Generator")

# Azure OpenAI Configuration Inputs
azure_api_key = st.sidebar.text_input("Enter Azure API Key", type="password")
azure_api_base = "https://<your-resource-name>.openai.azure.com/"  # Update with your Azure endpoint
azure_api_version = "2024-02-15-preview"
deployment_name = "gpt-4"

# Validate Azure API configuration
if azure_api_key:
    try:
        llm = AzureChatOpenAI(
            openai_api_key=azure_api_key,
            openai_api_base=azure_api_base,
            openai_api_version=azure_api_version,
            deployment_name=deployment_name,
            openai_api_type="azure",
            temperature=0.7  # Default value; can be adjusted below
        )
        st.success("Azure OpenAI API connection successful!")
    except Exception as e:
        st.error(f"Error connecting to Azure OpenAI: {str(e)}")
else:
    st.warning("Please enter your Azure OpenAI API Key in the sidebar.")

# File uploader to accept both .txt and .docx files
uploaded_files = st.file_uploader("Upload one or more transcript files (TXT or Word)", type=["txt", "docx"], accept_multiple_files=True)

# Process uploaded files
if uploaded_files and azure_api_key:
    combined_content = ""
    for uploaded_file in uploaded_files:
        # Read content based on file type
        if uploaded_file.type == "text/plain":
            file_content = uploaded_file.read().decode("utf-8")
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            file_content = read_docx(uploaded_file)
        
        # Append content to combined_content
        combined_content += f"--- Beginning of content from file {uploaded_file.name} ---\n"
        combined_content += file_content + "\n"
        combined_content += f"--- End of content from file {uploaded_file.name} ---\n\n"
    
    # Define Content Planner Agent
    planner = Agent(
        role="Content Planner",
        goal="Analyze the transcripts to extract key themes and structure a research article.",
        backstory="You are tasked with analyzing and structuring a comprehensive research article.",
        llm=llm,
        allow_delegation=False,
        verbose=True
    )

    # Task for planning content
    plan_task = Task(
        description="Plan content structure and key insights based on provided transcripts.",
        agent=planner,
        inputs=[combined_content],
        expected_output="A structured plan with key themes and sections for the research article."
    )

    # Define Content Writer Agent
    writer = Agent(
        role="Content Writer",
        goal="Write a cohesive and insightful research article based on the planner's output.",
        backstory="You are tasked with writing a polished and professional research article.",
        llm=llm,
        allow_delegation=False,
        verbose=True
    )

    # Task for writing content
    write_task = Task(
        description="Write a comprehensive research article based on the planner's structured content.",
        agent=writer,
        expected_output="A finalized research article ready for review."
    )

    # Create Crew for the workflow
    crew = Crew(
        agents=[planner, writer],
        tasks=[plan_task, write_task],
        verbose=True
    )

    # Generate Research Article
    if st.button("Generate Research Article"):
        try:
            with st.spinner("Generating research article... This may take a few minutes."):
                result = crew.kickoff()
            st.success("Research article generated successfully!")
            st.markdown(result)

            # Provide download button for the article
            doc = Document()
            doc.add_paragraph("Generated Research Article", style='Heading 1')
            for line in result.split('\n'):
                p = doc.add_paragraph(line)
                p.style.font.name = 'Times New Roman'
                p.style.font.size = Pt(11)

            # Save document to buffer
            word_buffer = io.BytesIO()
            doc.save(word_buffer)
            word_buffer.seek(0)

            st.download_button(
                label="Download Research Article",
                data=word_buffer.getvalue(),
                file_name="research_article.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error generating article: {str(e)}")
            st.error(traceback.format_exc())
else:
    st.info("Upload files and ensure Azure OpenAI API Key is provided to start.")

st.markdown("---")
st.markdown("Tapestry Networks")