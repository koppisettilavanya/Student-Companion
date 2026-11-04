"""
API URL routes for AI Student Companion application.
"""

from django.urls import path
from . import views

urlpatterns = [
    # System and settings
    path('status/', views.system_status_view, name='api_status'),
    path('validate-key/', views.validate_key_view, name='api_validate_key'),

    # Feature 1: Authentication
    path('auth/status/', views.auth_status_view, name='api_auth_status'),
    path('auth/signup/', views.signup_view, name='api_auth_signup'),
    path('auth/login/', views.login_view, name='api_auth_login'),
    path('auth/logout/', views.logout_view, name='api_auth_logout'),

    # Feature 2: Dashboard
    path('dashboard/', views.dashboard_data_view, name='api_dashboard'),

    # Feature 3: AI Topic Explainer
    path('tools/explain/', views.explain_topic_view, name='api_explain_topic'),
    path('tools/save-explanation/', views.save_explanation_view, name='api_save_explanation'),
    path('tools/explanations/', views.explanations_list_view, name='api_explanations_list'),
    path('tools/explanations/<str:explanation_id>/', views.explanation_detail_delete_view, name='api_explanation_detail_delete'),

    # Feature 4: Interview Preparation
    path('tools/interview-prep/', views.interview_prep_view, name='api_interview_prep'),
    path('tools/interview-sessions/', views.interview_sessions_list_view, name='api_interview_sessions'),
    path('tools/interview-sessions/<str:session_id>/', views.interview_session_detail_delete_view, name='api_interview_session_detail_delete'),

    # Feature 5: MCQ Quiz Generator
    path('quiz/generate/', views.quiz_generate_view, name='api_quiz_generate'),
    path('quiz/submit/', views.quiz_submit_view, name='api_quiz_submit'),
    path('quiz/history/', views.quiz_history_view, name='api_quiz_history'),
    path('quiz/<str:quiz_id>/', views.quiz_detail_delete_view, name='api_quiz_detail_delete'),

    # Feature 6: AI Chat & Conversation management
    path('chat/', views.chat_view, name='api_chat'),
    path('chat/regenerate/', views.regenerate_chat_view, name='api_chat_regenerate'),
    path('conversations/', views.conversations_list_create_view, name='api_conversations'),
    path('conversations/<str:conversation_id>/', views.conversation_detail_view, name='api_conversation_detail'),
    path('conversations/<str:conversation_id>/clear/', views.conversation_clear_view, name='api_conversation_clear'),

    # Feature 7: File Upload & Actions inside Chat
    path('chat/upload/', views.upload_file_view, name='api_chat_upload'),
    path('chat/file-action/', views.file_action_view, name='api_chat_file_action'),
    path('chat/files/<str:file_id>/', views.delete_file_view, name='api_chat_delete_file'),

    # Feature 8: Learning History
    path('history/', views.learning_history_view, name='api_learning_history'),
]
