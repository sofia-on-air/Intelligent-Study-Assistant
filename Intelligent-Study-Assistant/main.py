import uvicorn
import os
import requests
import base64
import json
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import io
import PyPDF2
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
from models.quiz import Quiz
from fastapi import UploadFile, File
from models.flashcards import Flashcard
from openai import OpenAI as OpenAIClient, APIConnectionError, APIError, RateLimitError
import time

from database import engine, Base
import models.external_provider
from routers.user import router as UserRouter
from routers.external_provider import router as ExternalProviderRouter
from routers.quiz import router as QuizRouter

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from azure.search.documents.indexes.models import SearchableField, SearchField, SearchFieldDataType, SimpleField

from fastapi_mcp import FastApiMCP
from google_drive_utils import get_oauth_url, exchange_code_for_tokens, get_drive_service_from_tokens, get_file_content_with_service
from models.provider_availability import ProviderAvaliability


load_dotenv()
AZURE_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

ai_setup = [
    ProviderAvaliability(
        name="OpenAI",
        client=OpenAIClient(api_key=OPENAI_KEY, timeout=10.0, max_retries=0),
        model="gpt-3.5-turbo",
    ),
    ProviderAvaliability(
        name="DeepSeek",
        client=OpenAIClient(
            api_key=DEEPSEEK_KEY,
            base_url="https://api.deepseek.com",
            timeout=10.0,
            max_retries=0
        ),
        model="deepseek-chat",
    ),
]

def ai_configuration(prompt: str) -> str:
    for ai in ai_setup:
        if ai.availity_check() == False:
            print(f"{ai.name} is currently unavaliable")
            continue
        try:
            current_ai_model = ai.client.chat.completions.create(
                model=ai.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            ai.no_connection_problem()
            return current_ai_model.choices[0].message.content
        except (APIConnectionError, APIError, RateLimitError):
            ai.connection_failed()
            continue
    raise RuntimeError("All providers are unavailable")

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_KEY)

fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SearchableField(name="content", type=SearchFieldDataType.String, searchable=True),
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="myHnswProfile",
    ),
    SearchableField(name="metadata", type=SearchFieldDataType.String, searchable=True),
    SimpleField(name="user_id", type=SearchFieldDataType.Int32, filterable=True),
]

vector_store = AzureSearch(
    azure_search_endpoint=AZURE_ENDPOINT,
    azure_search_key=AZURE_KEY,
    index_name="diploma-index-v3", 
    embedding_function=embeddings.embed_query,
    fields=fields,
)

Base.metadata.create_all(bind=engine)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(UserRouter, prefix="/user")
app.include_router(ExternalProviderRouter, prefix="/external_provider")
app.include_router(QuizRouter, prefix="/quiz")

class ChatRequest(BaseModel):
    query: str
    user_id: int

class QuizRequest(BaseModel):
    topic: str
    num_questions: int = 3
    user_id: int

class LinkGithubRequest(BaseModel):
    user_id: int
    access_token: str

class UploadGithubRequest(BaseModel):
    user_id: int
    repo_name: str
    file_path: str

class UploadDriveRequest(BaseModel):
    user_id: int
    file_id: str
    file_name: str

class GoogleCallbackRequest(BaseModel):
    code: str
    user_id: int
    state: str = None  

class UpdateScoreRequest(BaseModel):
    quiz_id: int
    score: int

class FlashcardGenerateRequest(BaseModel):
    topic: str
    name: str
    words: list[str]
    user_id: int

@app.post("/chat")
def chat_with_rag(request: ChatRequest):
    found_documents = vector_store.similarity_search(
        request.query, 
        k=5,
        filters=f"user_id eq {request.user_id}"
    )

    relatied_information = ""
    for document in found_documents:
        relatied_information += document.page_content + "\n\n-------------\n\n"

    if not relatied_information:
        return {
            "question": request.query,
            "answer": "No documents found for such a topic, please upload information related to the topic first!!"
        }
    prompt_for_ai = f"""You are AI assistant for studying. Answer ONLY based on the context below.
    If the answer cannot be found in the context, say exactly: "I don't have information about this in your documents. Please upload relevant materials first."
    Do NOT use your general knowledge. Do NOT make up information.

    Context: {relatied_information}
    User question: {request.query}
    """
    # prompt written with ai assistance
    answer = ai_configuration(prompt_for_ai)
    return {
        "question": request.query,
        "answer": answer
    }

@app.post("/generate-quiz")
def generate_quiz(request: QuizRequest, db: Session = Depends(get_db)):
    found_documents = vector_store.similarity_search(
        request.topic, 
        k=5, 
        filters=f"user_id eq {request.user_id}" 
    )
    
    related_information = ""
    for document in found_documents:
        related_information += document.page_content + "\n\n-------------\n\n"
    
    if not related_information:
        return {
            "quiz": None, 
            "error": "No documents found for such a topic, please upload information related to the topic first!!"
        }

    prompt_for_ai_to_validate_topic = f"""Does the following context contain information about "{request.topic}" or closely related concepts?
        Answer ONLY with "yes" or "no".
        Context: {related_information[:1000]}"""
    # prompt written with ai assistance
    
    check_response = ai_configuration(prompt_for_ai_to_validate_topic)
    if "no" in check_response.lower().strip():
        return {
            "quiz": None, 
            "error": "Topic not found in your documents, please upload information related to the topic first!!"
        }

    data_for_quiz = None
    attempts = 0
    
    while attempts < 3:
        quiz_generation_prompt_for_extra_check = f"""You are a quiz generator. Create exactly {request.num_questions} multiple choice questions about "{request.topic}" based ONLY on the context below.

    You MUST return ONLY a valid JSON array with exactly {request.num_questions} objects. No explanations, no markdown, no extra text.
    Each object must have:
    - "question": string
    - "options": array of exactly 4 strings
    - "correct_answer": string (must be one of the 4 options, copied exactly)
    - "explanation": string

    Context:
    {related_information}

    Return ONLY the JSON array with exactly {request.num_questions} questions, nothing else."""# prompt written with ai assistance

        try:
            ai_answer = ai_configuration(quiz_generation_prompt_for_extra_check)
            ai_answer = ai_answer.replace("```json", "")
            ai_answer = ai_answer.replace("```", "")
            clean_content = ai_answer.strip()
            data_for_quiz = json.loads(clean_content)

            questions_in_string_format = ""
            for quiz in data_for_quiz:
                questions_in_string_format += quiz["question"] + "\n"

            verify_prompt = f"""Are these quiz questions related to the topic "{request.topic}"?
            Questions: {questions_in_string_format}
            Answer ONLY with "yes" or "no"."""
            # prompt written with ai assistance
            
            verify_response = ai_configuration(verify_prompt)
            if "yes" in verify_response.lower().strip():
                break
                
        except Exception:
            pass
        
        attempts += 1

    if not data_for_quiz:
        return {
            "quiz": None, 
            "error": "Could not generate relevant quiz"
        }

    new_quiz = Quiz(
        user_id=request.user_id,
        quiz_data_json=json.dumps(data_for_quiz),
        score=0,
        topic=request.topic
    )
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    
    return {
        "quiz_id": new_quiz.quiz_id,
        "topic": request.topic, 
        "quiz": data_for_quiz
    }

@app.get("/my-quizzes/{user_id}")
def get_user_quizzes(user_id: int, db: Session = Depends(get_db)):
    quizzes_from_db = db.query(Quiz).filter(Quiz.user_id == user_id).all()
    quizzes_of_user = []
    for quizz in quizzes_from_db:
        quizzes_of_user.append({
            "quiz_id": quizz.quiz_id,
            "quiz_data": json.loads(quizz.quiz_data_json),
            "score": quizz.score,
            "topic": quizz.topic or f"quiz of id - #{quizz.quiz_id}"
        })
    return {
        "quizzes": quizzes_of_user
    }

@app.post("/update-quiz-score")
def update_quiz_score(request: UpdateScoreRequest, db: Session = Depends(get_db)):
    quiz_from_db = db.query(Quiz).filter(Quiz.quiz_id == request.quiz_id).first()
    if quiz_from_db:
        is_score_better = request.score > quiz_from_db.score
        if is_score_better:
            quiz_from_db.score = request.score
            db.commit()
    return {
        "status": "success"
    }

@app.post("/link-github")
def link_github(request: LinkGithubRequest, db: Session = Depends(get_db)):
    
    existing_github_provider = db.query(models.external_provider.ExternalProvider).filter(
        models.external_provider.ExternalProvider.user_id == request.user_id,
        models.external_provider.ExternalProvider.provider_name == "github"
    ).first()

    if existing_github_provider:
        existing_github_provider.access_token = request.access_token
    else:
        new_github_provider_connection = models.external_provider.ExternalProvider(
            user_id=request.user_id,
            provider_name="github",
            access_token=request.access_token
        )
        db.add(new_github_provider_connection)

    db.commit()
    return {
        "status": "success", 
        "message": "GitHub access token was updated successfully yey!!"
    }

@app.get('/github-file')
def get_github_file(user_id: int, repository_name: str, file_path: str, db: Session = Depends(get_db)):
    
    github_provider = db.query(models.external_provider.ExternalProvider).filter(
        models.external_provider.ExternalProvider.user_id == user_id,
        models.external_provider.ExternalProvider.provider_name == "github"
    ).first()

    github_url_for_request = f"https://api.github.com/repos/{repository_name}/contents/{file_path}"
    request_headers = {"Accept": "application/vnd.github.v3+json"}

    if github_provider and github_provider.access_token:
        token = github_provider.access_token.strip()
        request_headers["Authorization"] = f"Bearer {token}"
    else:
        return "Error: GitHub is not connected. Please connect GitHub first!!"

    github_response = requests.get(github_url_for_request, headers=request_headers)

    if github_response.status_code != 200:
        return f"Error {github_response.status_code}"

    file_in_base64 = github_response.json().get('content', '')
    file_bytes = base64.b64decode(file_in_base64)

    if file_path.lower().endswith('.pdf'):
        try:
            pdf_stream = io.BytesIO(file_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            extracted_text = ""
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() + "\n"
            return extracted_text
        except Exception as e:
            return f"Error occured while parsing pdf: {str(e)}"
        
    return file_bytes.decode('utf-8', errors='ignore')

@app.post("/upload-github")
def upload_github_to_rag(request: UploadGithubRequest, db: Session = Depends(get_db)):

    github_provider = db.query(models.external_provider.ExternalProvider).filter(
        models.external_provider.ExternalProvider.user_id == request.user_id,
        models.external_provider.ExternalProvider.provider_name == "github"
    ).first()

    if not github_provider or not github_provider.access_token:
        return {
            "status": "error", 
            "message": "Error: GitHub is not connected. Please connect GitHub first!!"
        }

    file_content_from_github = get_github_file(request.user_id, request.repo_name, request.file_path, db)

    if not file_content_from_github or file_content_from_github.startswith("Error"):
        return {
            "status": "error", 
            "message": "Error fetching file from GitHub: " + file_content_from_github
        }

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(file_content_from_github)

    documents_to_upload = []
    for chunk in chunks:
        document = Document(
            page_content=chunk,
            metadata={
                "user_id": int(request.user_id),
                "source": request.file_path
            }
        )
        documents_to_upload.append(document)

    try:
        vector_store.add_documents(documents_to_upload)
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error on azure side: {str(e)}"
        }

    return {
        "status": "success",
        "message": f"File uploaded successfully yey!! ({len(chunks)} chunks)"
    }

@app.get("/link-google")
def link_google(user_id: int):
    auth_url = get_oauth_url(user_id)
    return {"auth_url": auth_url}

@app.post("/google-callback")
def google_callback(request: GoogleCallbackRequest, db: Session = Depends(get_db)):
    try:
        google_tokens = exchange_code_for_tokens(
            request.code, 
            request.state or str(request.user_id)
        )
        token_json = json.dumps(google_tokens)

        is_connection_exist = db.query(models.external_provider.ExternalProvider).filter(
            models.external_provider.ExternalProvider.user_id == request.user_id,
            models.external_provider.ExternalProvider.provider_name == "google_drive"
        ).first()

        if is_connection_exist:
            is_connection_exist.access_token = token_json
            is_connection_exist.refresh_token = google_tokens.get("refresh_token")
            is_connection_exist.status = "connected"
        else:
            new_google_connection = models.external_provider.ExternalProvider(
                user_id=request.user_id,
                provider_name="google_drive",
                access_token=token_json,
                refresh_token=google_tokens.get("refresh_token"),
                status="connected"
            )
            db.add(new_google_connection)

        db.commit()
        return {
            "status": "success", 
            "message": "Google Drive connected successfully yey!!"
        }

    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error while connecting to Google Drive occured: {str(e)}"
        }

@app.post("/upload-file")
async def upload_local_file(user_id: int, file: UploadFile = File(...)):

    file_content = await file.read()
    extracted_text = ""

    if file.filename.lower().endswith(".pdf"):
        try:
            pdf_stream = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Error occured while parcing pdf: {str(e)}"
            }

    elif file.filename.lower().endswith(".txt"):
        extracted_text = file_content.decode("utf-8", errors="ignore")

    else:
        return {
            "status": "error", 
            "message": "Only pdf and txt files are supported for this website please upload files with the correct format!!"
        }

    if not extracted_text.strip():
        return {
            "status": "error", 
            "message": "Could not extract text from file:("
        }

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(extracted_text)

    documents_to_upload = []
    for chunk in chunks:
        document = Document(
            page_content=chunk,
            metadata={
                "user_id": int(user_id),
                "source": file.filename
            }
        )
        documents_to_upload.append(document)

    try:
        vector_store.add_documents(documents_to_upload)
        return {
            "status": "success",
            "message": f"File {file.filename} uploaded successfully yey!!"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error occured while uploading file to Azure: {str(e)}"
            }

def get_google_service_for_user(user_id: int, db):
    
    google_provider = db.query(models.external_provider.ExternalProvider).filter(
        models.external_provider.ExternalProvider.user_id == user_id,
        models.external_provider.ExternalProvider.provider_name == "google_drive"
    ).first()

    if not google_provider or not google_provider.access_token:
        return None, "not_connected"

    try:
        google_service, updated_tokens = get_drive_service_from_tokens(
            google_provider.access_token
        )

        if updated_tokens:
            google_provider.access_token = json.dumps(updated_tokens)
            google_provider.refresh_token = updated_tokens.get("refresh_token")
            db.commit()

        return google_service, None

    except Exception as e:
        return None, "token_invalid"

@app.get("/google-status")
def google_status(user_id: int, db: Session = Depends(get_db)):

    _, error = get_google_service_for_user(user_id, db)

    if error == "not_connected":
        return {
            "connected": False,
            "message": "Google Drive is not connected currently",
            "auth_url": get_oauth_url(user_id)
        }

    if error == "token_invalid":
        return {
            "connected": False,
            "message": "Google Drive token expired, please authorise again for usage",
            "auth_url": get_oauth_url(user_id)
        }

    return {
        "connected": True,
        "message": "Google Drive is connected yey!!"
    }

@app.post("/upload-drive")
def upload_drive_to_rag(request: UploadDriveRequest, db: Session = Depends(get_db)):
    
    google_service, error = get_google_service_for_user(request.user_id, db)
    if error:
        return {
            "status": "error",
            "message": f"Error occurred:( : {error}",
            "auth_url": get_oauth_url(request.user_id)
        }

    try:
        file_content = get_file_content_with_service(google_service, request.file_id)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unfortunatelly could not download file: {str(e)}"
        }

    if not file_content or not file_content.strip():
        return {
            "status": "error", 
            "message": "File is empty or text could not be extracted from it:("
        }

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(file_content)

    documents_to_upload = []
    for chunk in chunks:
        document = Document(
            page_content=chunk,
            metadata={
                "user_id": int(request.user_id),
                "source": request.file_name
            }
        )
        documents_to_upload.append(document)

    try:
        vector_store.add_documents(documents_to_upload)
        return {
            "status": "success",
            "message": f"File {request.file_name} was uploaded successfully!"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error happened while uploading file: {str(e)}"
        }
@app.post("/generate-flashcards")
def generate_flashcards(request: FlashcardGenerateRequest, db: Session = Depends(get_db)):
    found_documents = vector_store.similarity_search(
        request.topic,
        k=5,
        filters=f"user_id eq {request.user_id}"
    )
    if not found_documents:
        return {"status": "unknown_topic"}

    related_information = ""
    for document in found_documents:
        related_information += document.page_content + "\n\n-------------\n\n"

    if request.name == "__check__":
        check_prompt = f"""Does the following context contain information about "{request.topic}"?
        Answer ONLY with "yes" or "no". Be strict - if the topic is not directly discussed, answer "no".
        Context: {related_information[:1000]}"""
        # prompt written with ai assistance
        check_response = ai_configuration(check_prompt)
        if "no" in check_response.lower().strip():
            return {"status": "unknown_topic"}
        return {"status": "success"}

    all_documents = []
    for word in request.words:
        word_docs = vector_store.similarity_search(
            word,
            k=3,
            filters=f"user_id eq {request.user_id}"
        )
        all_documents.extend(word_docs)

    seen = set()
    unique_documents = []
    for doc in all_documents:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_documents.append(doc)

    related_information = ""
    for document in unique_documents:
        related_information += document.page_content + "\n\n-------------\n\n"

    words_as_text = ""
    for word in request.words:
        words_as_text += f"- {word}\n"

    flashcard_prompt = f"""You are a flashcard generator. Based ONLY on the context below, find and extract the definition for each phrase given by the user.
        STRICT RULES:
        - Search for each word/phrase case-insensitively
        - If a word or phrase (or its close variant) does NOT appear in the context, set "back" to exactly: "Not found in provided materials"
        - Do NOT use any outside knowledge
        - Do NOT invent or guess definitions
        - Copy the wording from the context as closely as possible
        Return ONLY a valid JSON array. No markdown, no extra text.
        Each object must have:
        - "front": the word or phrase exactly as given by a user
        - "back": the definition from context, or "Not found in provided materials"
        Words to define:
        {words_as_text}
        Context:
        {related_information}
        Return ONLY the JSON array."""
    # prompt written with ai assistance

    try:
        ai_answer = ai_configuration(flashcard_prompt)
        ai_answer = ai_answer.replace("```json", "")
        ai_answer = ai_answer.replace("```", "")
        generated_cards = json.loads(ai_answer.strip())

        found_cards = [c for c in generated_cards if c.get("back") != "Not found in provided materials"]
        not_found_words = [c["front"] for c in generated_cards if c.get("back") == "Not found in provided materials"]

        if not found_cards:
            return {
                "status": "error",
                "message": "None of the provided words were found in your materials."
            }

        new_flashcard_set = Flashcard(
            user_id=request.user_id,
            front_text=request.name,
            back_text=json.dumps(found_cards)
        )
        db.add(new_flashcard_set)
        db.commit()
        db.refresh(new_flashcard_set)

        return {
            "status": "success",
            "set_id": new_flashcard_set.card_id,
            "name": request.name,
            "cards": found_cards,
            "not_found": not_found_words
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error happened while generating flashcards:( : {str(e)}"
        }

@app.get("/my-flashcards/{user_id}")
def get_my_flashcards(user_id: int, db: Session = Depends(get_db)):

    all_flashcard_sets = db.query(Flashcard).filter(Flashcard.user_id == user_id).all()

    all_sets = []
    for flashcard_set in all_flashcard_sets:
        try:
            cards = json.loads(flashcard_set.back_text)
            all_sets.append({
                "set_id": flashcard_set.card_id,
                "name": flashcard_set.front_text,
                "cards": cards,
                "count": len(cards)
            })
        except Exception as e:
            print(f"Error occurred while processing flashcard set: {e}")
            pass

    return {"sets": all_sets}

mcp = FastApiMCP(app)
mcp.mount()

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=8080, reload=True)