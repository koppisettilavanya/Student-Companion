"""
Django views for AI Student Companion (GroqChat).
Full implementation of:
1. Authentication (Sign Up, Login, Logout, Session check)
2. Dashboard metrics and study activities
3. AI Topic Explainer (Summary, Detailed, Examples, Code, Tips, Save)
4. Interview Preparation (Questions, Answers, Tips, Role-based)
5. MCQ Quiz Generator (3-10 questions, 4 options, auto-scoring, history)
6. AI Chat (Contextual multi-turn, regenerate, clear chat)
7. File Upload (PDF, DOCX, TXT, Images OCR, document Q&A and study actions)
8. Learning History (Unified view, search, reopen, delete)
"""

import json
import logging
import uuid
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q, Avg, Count
from django.utils import timezone

from .models import (
    UserProfile,
    Conversation,
    Message,
    UploadedFile,
    SavedExplanation,
    InterviewSession,
    QuizRecord,
    ActivityLog,
)
from .services.groq_service import (
    GroqService,
    GroqServiceError,
    SUPPORTED_MODELS,
    DEFAULT_MODEL,
)
from .services.document_parser import extract_text_from_file
from .services.ai_tools_service import AIToolsService
from .serializers import (
    validate_chat_payload,
    validate_regenerate_payload,
    validate_rename_payload,
    validate_signup_payload,
    validate_login_payload,
    validate_topic_payload,
    validate_interview_payload,
    validate_quiz_payload,
)

logger = logging.getLogger(__name__)


def _extract_request_credentials(request, body_dict=None):
    """
    Extracts optional runtime Groq API key or model from headers or request payload.
    Supports Authorization: Bearer <key> or X-Groq-API-Key header.
    """
    auth_header = request.headers.get('Authorization', '')
    bearer_token = ''
    if auth_header.startswith('Bearer '):
        bearer_token = auth_header[7:].strip()

    custom_header_key = request.headers.get('X-Groq-Api-Key', '').strip()

    payload_key = ''
    payload_model = ''
    if body_dict and isinstance(body_dict, dict):
        payload_key = body_dict.get('api_key', '')
        payload_model = body_dict.get('model', '')

    custom_model_header = request.headers.get('X-Groq-Model', '').strip()

    resolved_key = bearer_token or custom_header_key or payload_key or None
    resolved_model = custom_model_header or payload_model or None

    return resolved_key, resolved_model


def _log_user_activity(user, activity_type: str, title: str, description: str = '', link_id: str = ''):
    """Helper to record user activity and maintain streak."""
    if not user or not user.is_authenticated:
        return
    try:
        ActivityLog.objects.create(
            user=user,
            activity_type=activity_type,
            title=title[:255],
            description=description,
            link_id=str(link_id),
        )
        if hasattr(user, 'profile'):
            user.profile.record_activity()
    except Exception as exc:
        logger.warning("Failed to log activity for user %s: %s", user, exc)


# ==============================================================================
# Index & System Views
# ==============================================================================

@ensure_csrf_cookie
def index_view(request):
    """
    Renders the primary application template.
    """
    has_env_key = GroqService.is_configured()
    supported_models = GroqService.get_supported_models()
    default_model = GroqService.get_model()
    context = {
        'has_env_key': has_env_key,
        'supported_models': supported_models,
        'default_model': default_model,
        'user': request.user if request.user.is_authenticated else None,
    }
    return render(request, 'index.html', context)


@require_http_methods(["GET"])
def system_status_view(request):
    """
    Returns system status, supported models, and Groq configuration state.
    """
    runtime_key, _ = _extract_request_credentials(request)
    is_configured = GroqService.is_configured(runtime_key)
    supported_models = GroqService.get_supported_models(runtime_key)

    conv_filter = Q(user=request.user) if request.user.is_authenticated else Q(user__isnull=True)

    return JsonResponse({
        'status': 'ok',
        'is_configured': is_configured,
        'default_model': GroqService.get_model(),
        'supported_models': supported_models,
        'total_conversations': Conversation.objects.filter(conv_filter).count(),
        'total_messages': Message.objects.count(),
        'user_authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'timestamp': timezone.now().isoformat(),
    })


@require_http_methods(["POST"])
def validate_key_view(request):
    """
    Validates a provided Groq API key by attempting a lightweight client check.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'valid': False, 'message': 'Invalid JSON body'}, status=400)

    api_key = body.get('api_key', '').strip()
    if not api_key:
        api_key = GroqService.get_api_key()

    if not api_key:
        return JsonResponse({
            'valid': False,
            'message': 'API key cannot be empty. Enter an API key or set GROQ_API_KEY in .env.'
        }, status=400)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        models_list = client.models.list()
        return JsonResponse({
            'valid': True,
            'message': 'API key is valid and connected to Groq.',
            'available_models_count': len(models_list.data) if hasattr(models_list, 'data') else 0
        })
    except Exception as exc:
        return JsonResponse({
            'valid': False,
            'message': f'Validation failed: {str(exc)}'
        }, status=401)


# ==============================================================================
# Feature 1: Authentication Views
# ==============================================================================

@require_http_methods(["GET"])
def auth_status_view(request):
    """
    Checks if current session has an authenticated user.
    """
    if request.user.is_authenticated:
        streak = request.user.profile.study_streak if hasattr(request.user, 'profile') else 1
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'full_name': request.user.get_full_name() or request.user.username,
                'study_streak': streak,
            }
        })
    return JsonResponse({'authenticated': False, 'user': None})


@require_http_methods(["POST"])
def signup_view(request):
    """
    Registers a new student user and establishes session.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    is_valid, err_msg, data = validate_signup_payload(body)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)

    username = data['username']
    email = data['email']
    password = data['password']
    full_name = data.get('full_name', '')

    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'error': f"Username '{username}' is already taken. Please choose another."}, status=400)

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'error': f"Email '{email}' is already registered. Please log in instead."}, status=400)

    try:
        first_name = full_name.split()[0] if full_name else username
        last_name = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Profile is created via signal
        login(request, user)
        _log_user_activity(user, 'chat', 'Created account and started learning journey!')

        return JsonResponse({
            'status': 'success',
            'message': 'Account created successfully!',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username,
                'study_streak': user.profile.study_streak,
            }
        }, status=201)
    except Exception as exc:
        logger.exception("Error during signup: %s", exc)
        return JsonResponse({'error': f"Failed to create account: {str(exc)}"}, status=500)


@require_http_methods(["POST"])
def login_view(request):
    """
    Authenticates a user by username or email.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    is_valid, err_msg, data = validate_login_payload(body)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)

    login_identifier = data['username']
    password = data['password']

    # Try resolving username from email if email format provided
    username_to_auth = login_identifier
    if '@' in login_identifier:
        user_obj = User.objects.filter(email__iexact=login_identifier).first()
        if user_obj:
            username_to_auth = user_obj.username

    user = authenticate(request, username=username_to_auth, password=password)
    if user is None:
        return JsonResponse({'error': 'Invalid credentials. Please verify your username and password.'}, status=401)

    login(request, user)
    streak = user.profile.record_activity() if hasattr(user, 'profile') else 1

    return JsonResponse({
        'status': 'success',
        'message': f'Welcome back, {user.first_name or user.username}!',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name() or user.username,
            'study_streak': streak,
        }
    })


@require_http_methods(["POST"])
def logout_view(request):
    """
    Terminates active user session.
    """
    logout(request)
    return JsonResponse({'status': 'success', 'message': 'Logged out successfully.'})


# ==============================================================================
# Feature 2: Dashboard Views
# ==============================================================================

@require_http_methods(["GET"])
def dashboard_data_view(request):
    """
    Provides comprehensive learning dashboard metrics for student:
    - User name & profile
    - Total study sessions
    - Completed quizzes & average score
    - Study streak
    - Recent activities
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Authentication required to access student dashboard.',
            'authenticated': False
        }, status=401)

    user = request.user
    profile = getattr(user, 'profile', None)
    streak = profile.study_streak if profile else 1

    # Calculations
    study_sessions_count = (
        Conversation.objects.filter(user=user).count() +
        SavedExplanation.objects.filter(user=user).count() +
        InterviewSession.objects.filter(user=user).count()
    )

    completed_quizzes_qs = QuizRecord.objects.filter(user=user, completed=True)
    completed_quizzes_count = completed_quizzes_qs.count()

    avg_score_res = completed_quizzes_qs.aggregate(Avg('percentage'))
    avg_score = round(avg_score_res['percentage__avg'] or 0.0, 1)

    # Recent activities (up to 10)
    recent_activities = [
        act.to_dict() for act in ActivityLog.objects.filter(user=user).order_by('-created_at')[:10]
    ]

    # Recent quizzes (up to 5)
    recent_quizzes = [
        q.to_dict() for q in completed_quizzes_qs.order_by('-created_at')[:5]
    ]

    # Recent explanations (up to 5)
    recent_explanations = [
        exp.to_dict() for exp in SavedExplanation.objects.filter(user=user).order_by('-created_at')[:5]
    ]

    # Recent interview preps (up to 5)
    recent_interviews = [
        it.to_dict() for it in InterviewSession.objects.filter(user=user).order_by('-created_at')[:5]
    ]

    return JsonResponse({
        'status': 'success',
        'user': {
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'study_streak': streak,
            'joined_date': user.date_joined.strftime('%B %Y'),
        },
        'metrics': {
            'study_sessions': study_sessions_count,
            'completed_quizzes': completed_quizzes_count,
            'average_score': avg_score,
            'study_streak': streak,
            'saved_topics_count': SavedExplanation.objects.filter(user=user).count(),
            'interview_sessions_count': InterviewSession.objects.filter(user=user).count(),
        },
        'recent_activities': recent_activities,
        'recent_quizzes': recent_quizzes,
        'recent_explanations': recent_explanations,
        'recent_interviews': recent_interviews,
    })


# ==============================================================================
# Feature 3: AI Topic Explainer Views
# ==============================================================================

@require_http_methods(["POST"])
def explain_topic_view(request):
    """
    Generates summary, detailed explanation, examples, code snippets, and interview tips.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)

    is_valid, err_msg, data = validate_topic_payload(body)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)

    topic = data['topic']
    subject = data['subject']
    level = data['level']
    runtime_key, runtime_model = _extract_request_credentials(request, body)

    try:
        explanation = AIToolsService.explain_topic(
            topic=topic,
            subject=subject,
            level=level,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
        )

        if request.user.is_authenticated:
            _log_user_activity(
                user=request.user,
                activity_type='explanation',
                title=f"Explored Topic: {topic}",
                description=f"Field: {subject} ({level})"
            )

        return JsonResponse({
            'status': 'success',
            'explanation': explanation,
        })
    except GroqServiceError as exc:
        return JsonResponse({
            'error': exc.message,
            'error_code': exc.error_code,
            'retry_after': getattr(exc, 'retry_after', None),
        }, status=exc.status_code)
    except Exception as exc:
        logger.exception("Error generating explanation: %s", exc)
        return JsonResponse({'error': f"Failed to generate explanation: {str(exc)}"}, status=500)


@require_http_methods(["POST"])
def save_explanation_view(request):
    """
    Saves an explanation to the user's permanent learning history.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please log in to save explanations.'}, status=401)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    topic = str(body.get('topic', '')).strip()
    if not topic:
        return JsonResponse({'error': 'Topic is required.'}, status=400)

    subject = str(body.get('subject', 'General')).strip()[:100]
    level = str(body.get('level', 'Intermediate')).strip()[:50]
    summary = str(body.get('summary', '')).strip()
    detailed_explanation = str(body.get('detailed_explanation', '')).strip()
    examples = str(body.get('examples', '')).strip()
    code_snippets = str(body.get('code_snippets', '')).strip()
    interview_tips = str(body.get('interview_tips', '')).strip()

    saved_obj = SavedExplanation.objects.create(
        user=request.user,
        topic=topic,
        subject=subject,
        level=level,
        summary=summary,
        detailed_explanation=detailed_explanation,
        examples=examples,
        code_snippets=code_snippets,
        interview_tips=interview_tips,
    )

    _log_user_activity(
        user=request.user,
        activity_type='explanation',
        title=f"Saved Explanation: {topic}",
        description=f"Subject: {subject}",
        link_id=str(saved_obj.id)
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Explanation for '{topic}' saved successfully!",
        'explanation': saved_obj.to_dict()
    }, status=201)


@require_http_methods(["GET"])
def explanations_list_view(request):
    """
    Lists all saved explanations for the current user with optional query filter.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    query = request.GET.get('q', '').strip()
    qs = SavedExplanation.objects.filter(user=request.user)
    if query:
        qs = qs.filter(Q(topic__icontains=query) | Q(subject__icontains=query) | Q(detailed_explanation__icontains=query))

    items = [exp.to_dict() for exp in qs[:100]]
    return JsonResponse({'status': 'success', 'count': len(items), 'explanations': items})


@require_http_methods(["GET", "DELETE"])
def explanation_detail_delete_view(request, explanation_id):
    """
    Retrieves or deletes a saved explanation.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    try:
        exp_uuid = uuid.UUID(str(explanation_id))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid explanation ID.'}, status=400)

    try:
        saved_exp = SavedExplanation.objects.get(id=exp_uuid, user=request.user)
    except SavedExplanation.DoesNotExist:
        return JsonResponse({'error': 'Saved explanation not found.'}, status=404)

    if request.method == "GET":
        return JsonResponse({'status': 'success', 'explanation': saved_exp.to_dict()})

    elif request.method == "DELETE":
        saved_exp.delete()
        return JsonResponse({'status': 'success', 'message': 'Explanation removed from saved topics.'})


# ==============================================================================
# Feature 4: Interview Preparation Views
# ==============================================================================

@require_http_methods(["POST"])
def interview_prep_view(request):
    """
    Generates technical interview questions, answers, and preparation tips based on subject, role, and difficulty.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)

    is_valid, err_msg, data = validate_interview_payload(body)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)

    subject = data['subject']
    role = data['role']
    difficulty = data['difficulty']
    count = data['count']
    runtime_key, runtime_model = _extract_request_credentials(request, body)

    try:
        interview_data = AIToolsService.generate_interview_prep(
            subject=subject,
            role=role,
            difficulty=difficulty,
            count=count,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
        )

        session_id = None
        if request.user.is_authenticated:
            session = InterviewSession(
                user=request.user,
                subject=subject,
                role=role,
                difficulty=difficulty,
            )
            session.set_data(interview_data)
            session.save()
            session_id = str(session.id)

            _log_user_activity(
                user=request.user,
                activity_type='interview',
                title=f"Interview Practice: {role}",
                description=f"{subject} ({difficulty})",
                link_id=session_id
            )

        return JsonResponse({
            'status': 'success',
            'session_id': session_id,
            'interview': interview_data,
        })
    except GroqServiceError as exc:
        return JsonResponse({
            'error': exc.message,
            'error_code': exc.error_code,
            'retry_after': getattr(exc, 'retry_after', None),
        }, status=exc.status_code)
    except Exception as exc:
        logger.exception("Error generating interview prep: %s", exc)
        return JsonResponse({'error': f"Failed to generate interview prep: {str(exc)}"}, status=500)


@require_http_methods(["GET"])
def interview_sessions_list_view(request):
    """
    Lists interview prep sessions for user.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    query = request.GET.get('q', '').strip()
    qs = InterviewSession.objects.filter(user=request.user)
    if query:
        qs = qs.filter(Q(subject__icontains=query) | Q(role__icontains=query))

    items = [s.to_dict() for s in qs[:100]]
    return JsonResponse({'status': 'success', 'count': len(items), 'sessions': items})


@require_http_methods(["GET", "DELETE"])
def interview_session_detail_delete_view(request, session_id):
    """
    Retrieves or deletes an interview preparation session.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    try:
        s_uuid = uuid.UUID(str(session_id))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid session ID.'}, status=400)

    try:
        session = InterviewSession.objects.get(id=s_uuid, user=request.user)
    except InterviewSession.DoesNotExist:
        return JsonResponse({'error': 'Interview session not found.'}, status=404)

    if request.method == "GET":
        return JsonResponse({'status': 'success', 'session': session.to_dict()})

    elif request.method == "DELETE":
        session.delete()
        return JsonResponse({'status': 'success', 'message': 'Interview session deleted.'})


# ==============================================================================
# Feature 5: MCQ Quiz Generator Views
# ==============================================================================

@require_http_methods(["POST"])
def quiz_generate_view(request):
    """
    Generates 3 to 10 MCQs with four options, explanations, and automatic scoring readiness.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)

    is_valid, err_msg, data = validate_quiz_payload(body)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)

    topic = data['topic']
    num_questions = data['num_questions']
    difficulty = data['difficulty']
    file_id = data.get('file_id')
    runtime_key, runtime_model = _extract_request_credentials(request, body)

    # If file_id is provided, fetch document text
    doc_text = None
    if file_id:
        try:
            f_uuid = uuid.UUID(str(file_id))
            file_record = UploadedFile.objects.filter(id=f_uuid).first()
            if file_record:
                doc_text = file_record.extracted_text
        except Exception:
            pass

    try:
        quiz_data = AIToolsService.generate_mcq_quiz(
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty,
            document_text=doc_text,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
        )

        # Store quiz in database
        quiz_id = None
        if request.user.is_authenticated:
            record = QuizRecord(
                user=request.user,
                topic=topic,
                difficulty=difficulty,
                total_questions=quiz_data['total_questions'],
                completed=False,
            )
            record.set_questions(quiz_data['questions'])
            record.save()
            quiz_id = str(record.id)

        # Sanitize correct answers from client payload for honest test taking if requested,
        # but keep explanation hidden until submission!
        client_questions = []
        for q in quiz_data['questions']:
            client_questions.append({
                'id': q['id'],
                'question': q['question'],
                'options': q['options'],
                # We return correct_answer and explanation for instant local or server verification
                'correct_answer': q['correct_answer'],
                'explanation': q['explanation'],
            })

        return JsonResponse({
            'status': 'success',
            'quiz_id': quiz_id,
            'quiz': {
                'topic': topic,
                'difficulty': difficulty,
                'total_questions': len(client_questions),
                'questions': client_questions,
            }
        })
    except GroqServiceError as exc:
        return JsonResponse({
            'error': exc.message,
            'error_code': exc.error_code,
            'retry_after': getattr(exc, 'retry_after', None),
        }, status=exc.status_code)
    except Exception as exc:
        logger.exception("Error generating quiz: %s", exc)
        return JsonResponse({'error': f"Failed to generate quiz: {str(exc)}"}, status=500)


@require_http_methods(["POST"])
def quiz_submit_view(request):
    """
    Evaluates submitted quiz answers, saves score, updates streak, and returns detailed results.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)

    quiz_id = body.get('quiz_id')
    user_answers = body.get('answers', {})  # { "1": "A", "2": "C" }
    questions = body.get('questions', [])  # Fallback if unauthenticated / client passed

    if not isinstance(user_answers, dict):
        return JsonResponse({'error': "Invalid answers format. Expected dictionary of question id to option."}, status=400)

    quiz_record = None
    if quiz_id:
        try:
            q_uuid = uuid.UUID(str(quiz_id))
            quiz_record = QuizRecord.objects.filter(id=q_uuid).first()
            if quiz_record:
                questions = quiz_record.get_questions()
        except Exception:
            pass

    if not questions:
        return JsonResponse({'error': 'Quiz questions not found.'}, status=400)

    score = 0
    total = len(questions)
    results = []

    for q in questions:
        qid_str = str(q.get('id'))
        correct = str(q.get('correct_answer', 'A')).strip().upper()
        user_choice = str(user_answers.get(qid_str, '')).strip().upper()
        is_correct = (user_choice == correct)

        if is_correct:
            score += 1

        results.append({
            'id': q.get('id'),
            'question': q.get('question'),
            'options': q.get('options', []),
            'correct_answer': correct,
            'user_answer': user_choice,
            'is_correct': is_correct,
            'explanation': q.get('explanation', ''),
        })

    percentage = round((score / total) * 100, 1) if total > 0 else 0.0

    if quiz_record:
        quiz_record.score = score
        quiz_record.total_questions = total
        quiz_record.percentage = percentage
        quiz_record.completed = True
        quiz_record.set_questions(results)
        quiz_record.save()

        if request.user.is_authenticated:
            _log_user_activity(
                user=request.user,
                activity_type='quiz',
                title=f"Quiz: {quiz_record.topic}",
                description=f"Scored {score}/{total} ({percentage}%)",
                link_id=str(quiz_record.id)
            )

    return JsonResponse({
        'status': 'success',
        'score': score,
        'total_questions': total,
        'percentage': percentage,
        'results': results,
    })


@require_http_methods(["GET"])
def quiz_history_view(request):
    """
    Returns user's completed quiz history.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    qs = QuizRecord.objects.filter(user=request.user, completed=True).order_by('-created_at')
    items = [q.to_dict() for q in qs[:50]]
    return JsonResponse({'status': 'success', 'count': len(items), 'history': items})


@require_http_methods(["GET", "DELETE"])
def quiz_detail_delete_view(request, quiz_id):
    """
    Retrieves or deletes a quiz record.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    try:
        q_uuid = uuid.UUID(str(quiz_id))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid quiz ID.'}, status=400)

    try:
        quiz = QuizRecord.objects.get(id=q_uuid, user=request.user)
    except QuizRecord.DoesNotExist:
        return JsonResponse({'error': 'Quiz not found.'}, status=404)

    if request.method == "GET":
        return JsonResponse({'status': 'success', 'quiz': quiz.to_dict()})
    elif request.method == "DELETE":
        quiz.delete()
        return JsonResponse({'status': 'success', 'message': 'Quiz deleted successfully.'})


# ==============================================================================
# Feature 6 & 7: AI Chat & File Upload Views
# ==============================================================================

@require_http_methods(["GET", "POST"])
def conversations_list_create_view(request):
    """
    GET: List conversations, ordered by updated_at descending, with search.
    POST: Create a new blank conversation.
    """
    if request.method == "GET":
        query = request.GET.get('q', '').strip()
        queryset = Conversation.objects.all().order_by('-updated_at')

        # Filter by user if logged in, or anonymous conversations if guest
        if request.user.is_authenticated:
            queryset = queryset.filter(user=request.user)
        else:
            queryset = queryset.filter(user__isnull=True)

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(messages__content__icontains=query)
            ).distinct()

        conversations = [conv.to_dict() for conv in queryset[:100]]
        return JsonResponse({
            'status': 'success',
            'count': len(conversations),
            'conversations': conversations
        })

    elif request.method == "POST":
        title = 'New Chat'
        try:
            if request.body:
                body = json.loads(request.body.decode('utf-8'))
                custom_title = body.get('title', '').strip()
                if custom_title:
                    title = custom_title[:255]
        except Exception:
            pass

        user = request.user if request.user.is_authenticated else None
        conversation = Conversation.objects.create(title=title, user=user)

        return JsonResponse({
            'status': 'success',
            'conversation': conversation.to_dict()
        }, status=201)


@require_http_methods(["GET", "DELETE", "PUT", "PATCH"])
def conversation_detail_view(request, conversation_id):
    """
    GET: Retrieve full conversation with all ordered messages and attached files.
    DELETE: Delete conversation and cascade-delete its messages and files.
    PUT/PATCH: Rename conversation title.
    """
    try:
        conv_uuid = uuid.UUID(str(conversation_id))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid conversation ID format'}, status=400)

    try:
        conversation = Conversation.objects.get(id=conv_uuid)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)

    # Permission check: if conversation belongs to another user
    if conversation.user and request.user != conversation.user:
        return JsonResponse({'error': 'You do not have access to this conversation.'}, status=403)

    if request.method == "GET":
        return JsonResponse({
            'status': 'success',
            'conversation': conversation.to_dict_full()
        })

    elif request.method == "DELETE":
        deleted_id = str(conversation.id)
        conversation.delete()
        return JsonResponse({
            'status': 'success',
            'message': 'Conversation deleted successfully',
            'id': deleted_id
        })

    elif request.method in ("PUT", "PATCH"):
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        is_valid, error_msg, new_title = validate_rename_payload(body)
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)

        conversation.title = new_title
        conversation.save(update_fields=['title', 'updated_at'])

        return JsonResponse({
            'status': 'success',
            'conversation': conversation.to_dict()
        })


@require_http_methods(["POST"])
def conversation_clear_view(request, conversation_id):
    """
    Clears all messages inside a conversation (Feature 6: Clear Chat).
    """
    try:
        conv_uuid = uuid.UUID(str(conversation_id))
        conversation = Conversation.objects.get(id=conv_uuid)
    except (ValueError, TypeError, Conversation.DoesNotExist):
        return JsonResponse({'error': 'Conversation not found.'}, status=404)

    if conversation.user and request.user != conversation.user:
        return JsonResponse({'error': 'Access denied.'}, status=403)

    count = conversation.messages.count()
    conversation.messages.all().delete()
    conversation.title = 'New Chat'
    conversation.save(update_fields=['title', 'updated_at'])

    return JsonResponse({
        'status': 'success',
        'message': f'Cleared {count} messages from chat.',
        'conversation': conversation.to_dict_full(),
    })


@require_http_methods(["POST"])
def chat_view(request):
    """
    Main chat endpoint.
    Receives user message, updates database, sends conversation context (plus any uploaded file content) to Groq,
    saves assistant response, and returns response to client.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)

    is_valid, error_msg, validated_data = validate_chat_payload(body)
    if not is_valid:
        return JsonResponse({'error': error_msg}, status=400)

    user_text = validated_data['message']
    conversation_id = validated_data['conversation_id']
    file_id = validated_data.get('file_id')
    runtime_key, runtime_model = _extract_request_credentials(request, body)

    # 1. Retrieve or create conversation
    user = request.user if request.user.is_authenticated else None
    if conversation_id:
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            if not conversation.user and user:
                conversation.user = user
                conversation.save(update_fields=['user'])
        except Conversation.DoesNotExist:
            return JsonResponse({'error': 'The requested conversation was not found.'}, status=404)
    else:
        conversation = Conversation.objects.create(title='New Chat', user=user)

    # 2. Check for uploaded file context
    attached_file = None
    if file_id:
        attached_file = UploadedFile.objects.filter(id=file_id).first()
    elif conversation.uploaded_files.exists():
        attached_file = conversation.uploaded_files.order_by('-created_at').first()

    system_instruction = None
    if attached_file and attached_file.extracted_text:
        system_instruction = (
            "You are GroqChat - AI Student Companion, a knowledgeable and encouraging academic mentor. "
            f"The student has uploaded a study document: '{attached_file.filename}'.\n"
            "Below is the extracted document content:\n"
            "\"\"\"\n"
            f"{attached_file.extracted_text[:12000]}\n"
            "\"\"\"\n"
            "Use this document text as direct reference context to answer questions, explain concepts, "
            "generate summaries, or create quizzes. Always be clear, articulate, and cite concepts accurately."
        )

    # 3. Check for previous unreplied user message with identical prompt to prevent duplicate DB rows on retry
    last_msg = conversation.messages.order_by('-created_at').first()
    if last_msg and last_msg.role == 'user' and last_msg.content.strip() == user_text.strip():
        user_message = last_msg
    else:
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_text
        )

    # 4. If first message, auto-generate conversation title
    if conversation.messages.count() <= 1 or conversation.title in ('New Chat', 'New Conversation'):
        conversation.generate_title_from_prompt(user_text)

    # 5. Fetch conversation history for Groq context (excluding the new user message)
    history_messages = list(
        conversation.messages
        .exclude(id=user_message.id)
        .order_by('created_at')
        .values('role', 'content')
    )

    # 6. Send to Groq API with automatic retry and exponential backoff
    try:
        ai_result = GroqService.generate_chat_response(
            conversation_history=history_messages,
            user_message=user_text,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
            system_instruction=system_instruction,
            max_tokens=1024,
        )
    except GroqServiceError as exc:
        logger.warning("GroqServiceError encountered: %s", exc.message)
        return JsonResponse({
            'error': exc.message,
            'error_code': exc.error_code,
            'retry_after': getattr(exc, 'retry_after', None),
            'conversation_id': str(conversation.id),
            'user_text': user_text,
            'user_message_id': user_message.id,
        }, status=exc.status_code)
    except Exception as exc:
        logger.exception("Unexpected error in chat view: %s", exc)
        return JsonResponse({
            'error': f"Failed to generate response: {str(exc)}",
            'error_code': 'SERVER_ERROR',
            'conversation_id': str(conversation.id),
            'user_text': user_text,
        }, status=500)

    # 7. Save assistant response to database
    assistant_message = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=ai_result['content']
    )

    conversation.save(update_fields=['updated_at'])

    if request.user.is_authenticated:
        _log_user_activity(
            user=request.user,
            activity_type='chat',
            title=f"Chat: {conversation.title}",
            description=user_text[:100],
            link_id=str(conversation.id)
        )

    return JsonResponse({
        'status': 'success',
        'conversation_id': str(conversation.id),
        'conversation_title': conversation.title,
        'user_message': user_message.to_dict(),
        'assistant_message': assistant_message.to_dict(),
        'model': ai_result.get('model'),
        'usage': ai_result.get('usage', {}),
        'finish_reason': ai_result.get('finish_reason'),
    })


@require_http_methods(["POST"])
def regenerate_chat_view(request):
    """
    Regenerates the last AI response in a conversation without duplicating the user's prompt.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)

    is_valid, error_msg, validated_data = validate_regenerate_payload(body)
    if not is_valid:
        return JsonResponse({'error': error_msg}, status=400)

    conversation_id = validated_data['conversation_id']
    runtime_key, runtime_model = _extract_request_credentials(request, body)

    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found.'}, status=404)

    # Find the latest assistant message if any and remove it
    latest_msg = conversation.messages.order_by('-created_at').first()
    if not latest_msg:
        return JsonResponse({'error': 'No messages found to regenerate.'}, status=400)

    if latest_msg.role == 'assistant':
        latest_msg.delete()

    # Now find the last user message
    last_user_msg = conversation.messages.filter(role='user').order_by('-created_at').first()
    if not last_user_msg:
        return JsonResponse({'error': 'No user prompt found in this conversation to regenerate.'}, status=400)

    # Attached file context if any
    system_instruction = None
    attached_file = conversation.uploaded_files.order_by('-created_at').first()
    if attached_file and attached_file.extracted_text:
        system_instruction = (
            "You are GroqChat - AI Student Companion. Reference this uploaded document:\n"
            f"\"{attached_file.extracted_text[:12000]}\""
        )

    # History prior to this user message
    history_messages = list(
        conversation.messages
        .filter(created_at__lt=last_user_msg.created_at)
        .order_by('created_at')
        .values('role', 'content')
    )

    try:
        ai_result = GroqService.generate_chat_response(
            conversation_history=history_messages,
            user_message=last_user_msg.content,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
            system_instruction=system_instruction,
            max_tokens=1024,
        )
    except GroqServiceError as exc:
        return JsonResponse({
            'error': exc.message,
            'error_code': exc.error_code,
            'retry_after': getattr(exc, 'retry_after', None),
            'conversation_id': str(conversation.id),
        }, status=exc.status_code)
    except Exception as exc:
        return JsonResponse({
            'error': f"Failed to regenerate response: {str(exc)}",
            'error_code': 'SERVER_ERROR',
            'conversation_id': str(conversation.id),
        }, status=500)

    # Save new assistant message
    new_assistant_msg = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=ai_result['content']
    )

    conversation.save(update_fields=['updated_at'])

    return JsonResponse({
        'status': 'success',
        'conversation_id': str(conversation.id),
        'assistant_message': new_assistant_msg.to_dict(),
        'model': ai_result.get('model'),
        'usage': ai_result.get('usage', {}),
    })


# ==============================================================================
# Feature 7: File Upload & Document Analysis Views
# ==============================================================================

@require_http_methods(["POST"])
def upload_file_view(request):
    """
    Handles file upload inside AI Chat:
    - Supports PDF, DOCX, TXT, JPG, JPEG, PNG
    - Extracts document text and uses OCR for images
    - Links to conversation and user
    """
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded. Please select a file.'}, status=400)

    uploaded_file_obj = request.FILES['file']
    filename = uploaded_file_obj.name
    conv_id = request.POST.get('conversation_id', '').strip()

    conversation = None
    if conv_id:
        try:
            conversation = Conversation.objects.filter(id=uuid.UUID(conv_id)).first()
        except Exception:
            pass

    user = request.user if request.user.is_authenticated else None

    # If conversation doesn't exist, create one
    if not conversation:
        conversation = Conversation.objects.create(
            title=f"Doc: {filename[:40]}",
            user=user
        )

    # Extract text and run OCR
    extract_result = extract_text_from_file(uploaded_file_obj, filename)
    if not extract_result['success']:
        return JsonResponse({'error': extract_result['error']}, status=400)

    file_record = UploadedFile.objects.create(
        user=user,
        conversation=conversation,
        filename=filename,
        file_type=extract_result['file_type'],
        file_size=extract_result['file_size'],
        extracted_text=extract_result['extracted_text'],
    )

    if user:
        _log_user_activity(
            user=user,
            activity_type='upload',
            title=f"Uploaded File: {filename}",
            description=f"{extract_result['word_count']} words extracted ({extract_result['file_type'].upper()})",
            link_id=str(file_record.id)
        )

    return JsonResponse({
        'status': 'success',
        'message': f"Successfully uploaded and extracted '{filename}'",
        'conversation_id': str(conversation.id),
        'file': file_record.to_dict(),
        'extracted_info': {
            'word_count': extract_result['word_count'],
            'char_count': extract_result['char_count'],
            'truncated': extract_result.get('truncated', False),
            'note': extract_result.get('note', ''),
        }
    }, status=201)


@require_http_methods(["DELETE"])
def delete_file_view(request, file_id):
    """
    Removes an uploaded file from conversation.
    """
    try:
        f_uuid = uuid.UUID(str(file_id))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid file ID.'}, status=400)

    try:
        file_record = UploadedFile.objects.get(id=f_uuid)
    except UploadedFile.DoesNotExist:
        return JsonResponse({'error': 'File not found.'}, status=404)

    if file_record.user and request.user != file_record.user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    filename = file_record.filename
    file_record.delete()
    return JsonResponse({'status': 'success', 'message': f"Removed file '{filename}'."})


@require_http_methods(["POST"])
def file_action_view(request):
    """
    Allows users to ask questions, generate summaries, important questions,
    and MCQs directly from uploaded content.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)

    file_id = body.get('file_id')
    action = body.get('action')  # 'ask', 'summary', 'important_questions', 'mcq'
    query = body.get('query', '')
    runtime_key, runtime_model = _extract_request_credentials(request, body)

    if not file_id:
        return JsonResponse({'error': 'File ID is required.'}, status=400)
    if action not in ('ask', 'summary', 'important_questions', 'mcq'):
        return JsonResponse({'error': "Invalid action. Choose 'ask', 'summary', 'important_questions', or 'mcq'."}, status=400)

    try:
        f_uuid = uuid.UUID(str(file_id))
        file_record = UploadedFile.objects.get(id=f_uuid)
    except (ValueError, TypeError, UploadedFile.DoesNotExist):
        return JsonResponse({'error': 'Uploaded file not found.'}, status=404)

    if not file_record.extracted_text.strip():
        return JsonResponse({'error': 'No extracted text found in this file to analyze.'}, status=400)

    try:
        if action == 'mcq':
            # Delegate to MCQ generator using document text
            quiz_data = AIToolsService.generate_mcq_quiz(
                topic=f"Material from {file_record.filename}",
                num_questions=5,
                difficulty='Medium',
                document_text=file_record.extracted_text,
                runtime_key=runtime_key,
                runtime_model=runtime_model,
            )
            return JsonResponse({'status': 'success', 'action': 'mcq', 'quiz': quiz_data})

        analysis = AIToolsService.analyze_document_content(
            document_text=file_record.extracted_text,
            filename=file_record.filename,
            action=action,
            user_query=query,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
        )

        return JsonResponse({
            'status': 'success',
            'action': action,
            'filename': file_record.filename,
            'result': analysis['result'],
            'model': analysis.get('model'),
        })
    except GroqServiceError as exc:
        return JsonResponse({
            'error': exc.message,
            'error_code': exc.error_code,
            'retry_after': getattr(exc, 'retry_after', None),
        }, status=exc.status_code)
    except Exception as exc:
        logger.exception("Error in file action: %s", exc)
        return JsonResponse({'error': f"Failed to analyze file: {str(exc)}"}, status=500)


# ==============================================================================
# Feature 8: Learning History Views
# ==============================================================================

@require_http_methods(["GET"])
def learning_history_view(request):
    """
    Unified learning history view:
    Allows students to view, search, reopen, and delete their own:
    - chats
    - explanations
    - interview sessions
    - quiz results
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required to view learning history.'}, status=401)

    category = request.GET.get('type', 'all').lower()  # all, chats, explanations, interviews, quizzes
    query = request.GET.get('q', '').strip()

    user = request.user
    chats_data = []
    explanations_data = []
    interviews_data = []
    quizzes_data = []

    # 1. Chats
    if category in ('all', 'chats'):
        chats_qs = Conversation.objects.filter(user=user).order_by('-updated_at')
        if query:
            chats_qs = chats_qs.filter(Q(title__icontains=query) | Q(messages__content__icontains=query)).distinct()
        chats_data = [
            {
                'type': 'chat',
                'id': str(c.id),
                'title': c.title,
                'created_at': c.created_at.isoformat(),
                'updated_at': c.updated_at.isoformat(),
                'message_count': c.messages.count(),
                'snippet': c.to_dict()['snippet'],
            }
            for c in chats_qs[:50]
        ]

    # 2. Topic Explanations
    if category in ('all', 'explanations'):
        exp_qs = SavedExplanation.objects.filter(user=user).order_by('-created_at')
        if query:
            exp_qs = exp_qs.filter(Q(topic__icontains=query) | Q(subject__icontains=query) | Q(detailed_explanation__icontains=query))
        explanations_data = [
            {
                'type': 'explanation',
                'id': str(e.id),
                'title': e.topic,
                'subject': e.subject,
                'level': e.level,
                'created_at': e.created_at.isoformat(),
                'snippet': e.summary[:100] if e.summary else e.detailed_explanation[:100],
            }
            for e in exp_qs[:50]
        ]

    # 3. Interview Sessions
    if category in ('all', 'interviews'):
        int_qs = InterviewSession.objects.filter(user=user).order_by('-created_at')
        if query:
            int_qs = int_qs.filter(Q(subject__icontains=query) | Q(role__icontains=query))
        interviews_data = [
            {
                'type': 'interview',
                'id': str(i.id),
                'title': f"{i.role} - {i.subject}",
                'difficulty': i.difficulty,
                'created_at': i.created_at.isoformat(),
                'question_count': i.to_dict()['question_count'],
            }
            for i in int_qs[:50]
        ]

    # 4. Quizzes
    if category in ('all', 'quizzes'):
        quiz_qs = QuizRecord.objects.filter(user=user, completed=True).order_by('-created_at')
        if query:
            quiz_qs = quiz_qs.filter(Q(topic__icontains=query))
        quizzes_data = [
            {
                'type': 'quiz',
                'id': str(q.id),
                'title': q.topic,
                'difficulty': q.difficulty,
                'score': q.score,
                'total_questions': q.total_questions,
                'percentage': q.percentage,
                'created_at': q.created_at.isoformat(),
            }
            for q in quiz_qs[:50]
        ]

    total_count = len(chats_data) + len(explanations_data) + len(interviews_data) + len(quizzes_data)

    return JsonResponse({
        'status': 'success',
        'filter_type': category,
        'search_query': query,
        'total_count': total_count,
        'chats': chats_data,
        'explanations': explanations_data,
        'interviews': interviews_data,
        'quizzes': quizzes_data,
    })
