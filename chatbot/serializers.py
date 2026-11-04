"""
Serializers and validation helpers for Chatbot API requests and responses.
"""

import uuid
from typing import Dict, Any, Tuple, Optional


def validate_chat_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validates payload for POST /api/chat/.
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON payload. Expected a JSON object.", {}

    message = data.get('message')
    if not message or not isinstance(message, str) or not message.strip():
        return False, "The 'message' field is required and cannot be empty.", {}

    clean_message = message.strip()
    if len(clean_message) > 32000:
        return False, "Message is too long. Maximum allowed length is 32,000 characters.", {}

    conversation_id = data.get('conversation_id')
    valid_uuid = None
    if conversation_id:
        try:
            valid_uuid = uuid.UUID(str(conversation_id))
        except (ValueError, AttributeError, TypeError):
            return False, "Invalid conversation_id format. Must be a valid UUID.", {}

    file_id = data.get('file_id')
    valid_file_uuid = None
    if file_id:
        try:
            valid_file_uuid = uuid.UUID(str(file_id))
        except (ValueError, AttributeError, TypeError):
            valid_file_uuid = None

    return True, None, {
        'message': clean_message,
        'conversation_id': valid_uuid,
        'file_id': valid_file_uuid,
        'model': data.get('model'),
        'api_key': data.get('api_key'),
    }


def validate_regenerate_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validates payload for POST /api/chat/regenerate/.
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON payload. Expected a JSON object.", {}

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return False, "The 'conversation_id' field is required to regenerate an AI response.", {}

    try:
        valid_uuid = uuid.UUID(str(conversation_id))
    except (ValueError, AttributeError, TypeError):
        return False, "Invalid conversation_id format. Must be a valid UUID.", {}

    return True, None, {
        'conversation_id': valid_uuid,
        'model': data.get('model'),
        'api_key': data.get('api_key'),
    }


def validate_rename_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
    """
    Validates payload for renaming a conversation.
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON payload.", ""

    title = data.get('title')
    if not title or not isinstance(title, str) or not title.strip():
        return False, "The 'title' field is required and cannot be empty.", ""

    clean_title = ' '.join(title.strip().split())
    if len(clean_title) > 255:
        clean_title = clean_title[:255]

    return True, None, clean_title


def validate_signup_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validates user registration payload.
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON payload.", {}

    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', ''))
    confirm_password = str(data.get('confirm_password', ''))
    full_name = str(data.get('full_name', '')).strip()

    if not username:
        return False, "Username is required.", {}
    if len(username) < 3:
        return False, "Username must be at least 3 characters long.", {}
    if not username.replace('_', '').isalnum():
        return False, "Username must contain only letters, numbers, and underscores.", {}

    if not email:
        return False, "Email address is required.", {}
    if '@' not in email or '.' not in email:
        return False, "Please enter a valid email address.", {}

    if not password:
        return False, "Password is required.", {}
    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", {}
    if password != confirm_password:
        return False, "Passwords do not match.", {}

    return True, None, {
        'username': username,
        'email': email,
        'password': password,
        'full_name': full_name,
    }


def validate_login_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validates user login payload.
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON payload.", {}

    username_or_email = str(data.get('username', '') or data.get('email', '')).strip()
    password = str(data.get('password', ''))

    if not username_or_email:
        return False, "Username or email is required.", {}
    if not password:
        return False, "Password is required.", {}

    return True, None, {
        'username': username_or_email,
        'password': password,
    }


def validate_topic_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validates topic explainer payload.
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON payload.", {}

    topic = str(data.get('topic', '')).strip()
    if not topic:
        return False, "Topic is required.", {}
    if len(topic) > 255:
        return False, "Topic name cannot exceed 255 characters.", {}

    subject = str(data.get('subject', 'General')).strip()[:100] or 'General'
    level = str(data.get('level', 'Intermediate')).strip()[:50] or 'Intermediate'

    return True, None, {
        'topic': topic,
        'subject': subject,
        'level': level,
    }


def validate_interview_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validates interview preparation payload.
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON payload.", {}

    subject = str(data.get('subject', '')).strip()
    role = str(data.get('role', '')).strip()
    difficulty = str(data.get('difficulty', 'Intermediate')).strip()
    count = data.get('count', 5)

    if not subject:
        return False, "Subject or technology is required.", {}
    if not role:
        return False, "Role is required (e.g. Frontend Developer, Backend Engineer).", {}

    try:
        count = int(count)
        count = max(3, min(10, count))
    except (ValueError, TypeError):
        count = 5

    return True, None, {
        'subject': subject[:150],
        'role': role[:150],
        'difficulty': difficulty[:50],
        'count': count,
    }


def validate_quiz_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validates MCQ quiz generation payload.
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON payload.", {}

    topic = str(data.get('topic', '')).strip()
    if not topic:
        return False, "Quiz topic or subject is required.", {}

    try:
        num_questions = int(data.get('num_questions', 5))
        num_questions = max(3, min(10, num_questions))
    except (ValueError, TypeError):
        num_questions = 5

    difficulty = str(data.get('difficulty', 'Medium')).strip()[:50] or 'Medium'
    file_id = data.get('file_id')

    return True, None, {
        'topic': topic[:255],
        'num_questions': num_questions,
        'difficulty': difficulty,
        'file_id': file_id,
    }
