import pytest
import bcrypt
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sys
import os
from models.provider_availability import ProviderAvaliability
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import ProviderAvaliability

def test_password_hashing():
    password = "test123"
    hashed = bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    )
    assert bcrypt.checkpw(password.encode('utf-8'), hashed)

def test_wrong_password_fails():
    password = "test123"
    wrong_password = "wrong456"
    hashed = bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    )
    assert not bcrypt.checkpw(wrong_password.encode('utf-8'), hashed)

def test_provider_available_by_default():
    provider = ProviderAvaliability("TestAI", None, "test-model")
    assert provider.availity_check() == True

def test_provider_unavailable_after_failures():
    provider = ProviderAvaliability("TestAI", None, "test-model")
    provider.connection_failures = 4
    provider.last_failure = float('inf')
    assert provider.availity_check() == False

def test_provider_recovers():
    provider = ProviderAvaliability("TestAI", None, "test-model")
    provider.connection_failures = 4
    provider.last_failure = 0
    provider.refresh = 90
    assert provider.availity_check() == True

def test_text_splitter_creates_chunks():
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50)
    text = "Hello world. " * 100
    chunks = splitter.split_text(text)
    assert len(chunks) > 1

def test_text_splitter_chunk_size():
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50)
    text = "Hello world. " * 100
    chunks = splitter.split_text(text)
    for chunk in chunks:
        assert len(chunk) <= 600

def test_quiz_json_format():
    quiz_data = [
        {
            "question": "What is Python?",
            "options": ["A language", "A snake", "A tool", "A library"],
            "correct_answer": "A language",
            "explanation": "Python is a programming language."
        }
    ]
    json_string = json.dumps(quiz_data)
    parsed = json.loads(json_string)
    assert len(parsed) == 1
    assert "question" in parsed[0]
    assert "options" in parsed[0]
    assert "correct_answer" in parsed[0]
    assert len(parsed[0]["options"]) == 4