"""
Unit and integration tests for AI Student Companion.
Covers all 8 key features:
1. Authentication
2. Dashboard
3. AI Topic Explainer
4. Interview Preparation
5. MCQ Quiz Generator
6. AI Chat & Context
7. File Upload & Document Analysis
8. Learning History
"""

import io
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

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
from .services.groq_service import GroqService, GroqServiceError, parse_reset_time
from .services.document_parser import extract_text_from_file


class AuthenticationTests(TestCase):
    """Feature 1: Tests for User Registration, Login, and Session management."""

    def setUp(self):
        self.client = Client()

    def test_signup_success(self):
        response = self.client.post(
            '/api/auth/signup/',
            content_type='application/json',
            data=json.dumps({
                'username': 'student_jane',
                'email': 'jane@example.com',
                'password': 'password123',
                'confirm_password': 'password123',
                'full_name': 'Jane Student'
            })
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['user']['username'], 'student_jane')
        self.assertTrue(User.objects.filter(username='student_jane').exists())
        self.assertTrue(UserProfile.objects.filter(user__username='student_jane').exists())

    def test_signup_validation_mismatched_password(self):
        response = self.client.post(
            '/api/auth/signup/',
            content_type='application/json',
            data=json.dumps({
                'username': 'student_bob',
                'email': 'bob@example.com',
                'password': 'password123',
                'confirm_password': 'password999',
            })
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('match', response.json()['error'])

    def test_login_and_logout(self):
        user = User.objects.create_user(username='alice', email='alice@example.com', password='secretpassword')

        # Login with username
        response = self.client.post(
            '/api/auth/login/',
            content_type='application/json',
            data=json.dumps({
                'username': 'alice',
                'password': 'secretpassword'
            })
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['username'], 'alice')

        # Check auth status
        status_res = self.client.get('/api/auth/status/')
        self.assertTrue(status_res.json()['authenticated'])

        # Logout
        logout_res = self.client.post('/api/auth/logout/')
        self.assertEqual(logout_res.status_code, 200)

        # Check auth status after logout
        status_after = self.client.get('/api/auth/status/')
        self.assertFalse(status_after.json()['authenticated'])


class DashboardTests(TestCase):
    """Feature 2: Tests for student dashboard metrics and activities."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='student_dash', password='password123', first_name='Alex')
        self.client.force_login(self.user)

    def test_dashboard_unauthenticated(self):
        anon_client = Client()
        response = anon_client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 401)

    def test_dashboard_authenticated(self):
        # Create some test data
        conv = Conversation.objects.create(user=self.user, title="Python algorithms")
        QuizRecord.objects.create(
            user=self.user,
            topic="Data Structures",
            score=4,
            total_questions=5,
            percentage=80.0,
            completed=True
        )
        ActivityLog.objects.create(
            user=self.user,
            activity_type='chat',
            title='Chat: Python algorithms'
        )

        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user']['username'], 'student_dash')
        self.assertEqual(data['metrics']['completed_quizzes'], 1)
        self.assertEqual(data['metrics']['average_score'], 80.0)
        self.assertEqual(len(data['recent_activities']), 1)


class TopicExplainerTests(TestCase):
    """Feature 3: Tests for AI Topic Explainer."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='scholar', password='password123')
        self.client.force_login(self.user)

    @patch.object(GroqService, 'generate_chat_response')
    def test_explain_topic(self, mock_generate):
        mock_generate.return_value = {
            'content': json.dumps({
                'summary': 'Binary search is an O(log N) search algorithm.',
                'detailed_explanation': 'Works on sorted arrays by repeatedly dividing search interval.',
                'examples': 'Finding a word in a physical dictionary.',
                'code_snippets': '```python\ndef binary_search(arr, x): ...\n```',
                'interview_tips': 'Watch out for integer overflow: mid = low + (high - low) // 2'
            }),
            'model': 'qwen/qwen3.8-27b'
        }

        response = self.client.post(
            '/api/tools/explain/',
            content_type='application/json',
            data=json.dumps({
                'topic': 'Binary Search',
                'subject': 'Algorithms',
                'level': 'Beginner'
            })
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['explanation']['topic'], 'Binary Search')
        self.assertIn('O(log N)', data['explanation']['summary'])

    def test_save_and_delete_explanation(self):
        save_res = self.client.post(
            '/api/tools/save-explanation/',
            content_type='application/json',
            data=json.dumps({
                'topic': 'Recursion',
                'subject': 'Computer Science',
                'summary': 'A function calling itself.',
                'detailed_explanation': 'Base cases and recursive steps.',
                'examples': 'Factorial calculation.',
                'code_snippets': 'def fact(n): return 1 if n<=1 else n*fact(n-1)',
                'interview_tips': 'Mention call stack and recursion depth limits.'
            })
        )
        self.assertEqual(save_res.status_code, 201)
        exp_id = save_res.json()['explanation']['id']

        list_res = self.client.get('/api/tools/explanations/')
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.json()['explanations']), 1)

        del_res = self.client.delete(f'/api/tools/explanations/{exp_id}/')
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(SavedExplanation.objects.count(), 0)


class InterviewPreparationTests(TestCase):
    """Feature 4: Tests for Technical Interview Preparation."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='jobseeker', password='password123')
        self.client.force_login(self.user)

    @patch.object(GroqService, 'generate_chat_response')
    def test_generate_interview_prep(self, mock_generate):
        mock_generate.return_value = {
            'content': json.dumps({
                'role': 'Backend Developer',
                'subject': 'Django',
                'difficulty': 'Intermediate',
                'preparation_tips': ['Review ORM optimizations', 'Understand middleware cycle'],
                'questions': [
                    {
                        'id': 1,
                        'question': 'How does select_related differ from prefetch_related?',
                        'answer': 'select_related uses SQL JOIN for single-valued relationships...',
                        'key_talking_points': ['SQL JOIN vs separate queries', 'FK vs M2M'],
                        'follow_up_questions': ['What happens with reverse foreign keys?']
                    }
                ]
            }),
            'model': 'qwen/qwen3.8-27b'
        }

        response = self.client.post(
            '/api/tools/interview-prep/',
            content_type='application/json',
            data=json.dumps({
                'role': 'Backend Developer',
                'subject': 'Django',
                'difficulty': 'Intermediate',
                'count': 3
            })
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['interview']['questions']), 1)
        self.assertIsNotNone(data['session_id'])


class MCQQuizGeneratorTests(TestCase):
    """Feature 5: Tests for MCQ Quiz Generation, scoring, and history."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='quiztaker', password='password123')
        self.client.force_login(self.user)

    @patch.object(GroqService, 'generate_chat_response')
    def test_quiz_lifecycle(self, mock_generate):
        mock_generate.return_value = {
            'content': json.dumps({
                'topic': 'Operating Systems',
                'difficulty': 'Medium',
                'questions': [
                    {
                        'id': 1,
                        'question': 'What is a deadlock condition in OS?',
                        'options': ['Mutual Exclusion', 'Hold and Wait', 'No Preemption', 'All of the above'],
                        'correct_answer': 'D',
                        'explanation': 'All four Coffman conditions must hold simultaneously for a deadlock.'
                    },
                    {
                        'id': 2,
                        'question': 'Which scheduling algorithm is non-preemptive?',
                        'options': ['First Come First Served (FCFS)', 'Round Robin', 'Shortest Remaining Time First', 'Priority Preemptive'],
                        'correct_answer': 'A',
                        'explanation': 'FCFS processes requests strictly in arrival order without preemption.'
                    }
                ]
            }),
            'model': 'qwen/qwen3.8-27b'
        }

        # 1. Generate Quiz
        gen_res = self.client.post(
            '/api/quiz/generate/',
            content_type='application/json',
            data=json.dumps({
                'topic': 'Operating Systems',
                'num_questions': 3,
                'difficulty': 'Medium'
            })
        )
        self.assertEqual(gen_res.status_code, 200)
        quiz_id = gen_res.json()['quiz_id']
        self.assertIsNotNone(quiz_id)

        # 2. Submit Answers
        sub_res = self.client.post(
            '/api/quiz/submit/',
            content_type='application/json',
            data=json.dumps({
                'quiz_id': quiz_id,
                'answers': {
                    '1': 'D',  # Correct
                    '2': 'B',  # Incorrect (correct is A)
                }
            })
        )
        self.assertEqual(sub_res.status_code, 200)
        sub_data = sub_res.json()
        self.assertEqual(sub_data['score'], 1)
        self.assertEqual(sub_data['total_questions'], 2)
        self.assertEqual(sub_data['percentage'], 50.0)

        # 3. Check Quiz History
        hist_res = self.client.get('/api/quiz/history/')
        self.assertEqual(hist_res.status_code, 200)
        self.assertEqual(len(hist_res.json()['history']), 1)


class AIChatAndFileUploadTests(TestCase):
    """Features 6 & 7: Tests for AI Chat, Clear Chat, and File Upload inside Chat."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='chatuser', password='password123')
        self.client.force_login(self.user)

    @patch.object(GroqService, 'generate_chat_response')
    def test_chat_interaction(self, mock_generate):
        mock_generate.return_value = {
            'content': 'Polymorphism allows objects of different classes to be treated as objects of a common superclass.',
            'model': 'qwen/qwen3.8-27b'
        }

        response = self.client.post(
            '/api/chat/',
            content_type='application/json',
            data=json.dumps({
                'message': 'Explain polymorphism in OOP'
            })
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Polymorphism', data['assistant_message']['content'])
        conv_id = data['conversation_id']

        # Clear chat test (Feature 6)
        clear_res = self.client.post(f'/api/conversations/{conv_id}/clear/')
        self.assertEqual(clear_res.status_code, 200)
        conv = Conversation.objects.get(id=conv_id)
        self.assertEqual(conv.messages.count(), 0)

    def test_file_upload_text_file(self):
        txt_content = b"Artificial intelligence is transforming education by enabling personalized learning paths."
        file_obj = io.BytesIO(txt_content)
        file_obj.name = 'lecture_notes.txt'

        response = self.client.post(
            '/api/chat/upload/',
            data={'file': file_obj}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['file']['filename'], 'lecture_notes.txt')
        self.assertTrue(UploadedFile.objects.filter(filename='lecture_notes.txt').exists())

    @patch.object(GroqService, 'generate_chat_response')
    def test_chat_rate_limit_error_handling(self, mock_generate):
        """Verifies that 429 rate limit errors return structured info and user message is preserved."""
        mock_generate.side_effect = GroqServiceError(
            "Groq API rate limit reached (Free Tier limit: 1,000 output tokens/min). Please wait 3 seconds and click Retry.",
            status_code=429,
            error_code='RATE_LIMITED',
            retry_after=3.0
        )

        response = self.client.post(
            '/api/chat/',
            content_type='application/json',
            data=json.dumps({
                'message': 'Explain merge sort in detail'
            })
        )
        self.assertEqual(response.status_code, 429)
        data = response.json()
        self.assertEqual(data['error_code'], 'RATE_LIMITED')
        self.assertEqual(data['retry_after'], 3.0)
        self.assertEqual(data['user_text'], 'Explain merge sort in detail')
        # Check that user message was recorded in DB and not lost
        conv = Conversation.objects.get(id=data['conversation_id'])
        self.assertEqual(conv.messages.count(), 1)
        self.assertEqual(conv.messages.first().content, 'Explain merge sort in detail')

    @patch.object(GroqService, 'generate_chat_response')
    def test_chat_retry_duplicate_prevention(self, mock_generate):
        """Verifies that consecutive retries of the same prompt reuse the unreplied message rather than duplicating."""
        # First call fails with 429
        mock_generate.side_effect = GroqServiceError("Rate limited", status_code=429, error_code='RATE_LIMITED', retry_after=2.0)
        res1 = self.client.post(
            '/api/chat/',
            content_type='application/json',
            data=json.dumps({'message': 'Explain Dijkstra algorithm'})
        )
        self.assertEqual(res1.status_code, 429)
        conv_id = res1.json()['conversation_id']
        conv = Conversation.objects.get(id=conv_id)
        self.assertEqual(conv.messages.count(), 1)

        # User clicks Retry (or resends identical text in same conversation)
        mock_generate.side_effect = None
        mock_generate.return_value = {
            'content': 'Dijkstra finds the shortest paths from a single source node.',
            'model': 'qwen/qwen3.8-27b'
        }
        res2 = self.client.post(
            '/api/chat/',
            content_type='application/json',
            data=json.dumps({
                'conversation_id': conv_id,
                'message': 'Explain Dijkstra algorithm'
            })
        )
        self.assertEqual(res2.status_code, 200)
        # Should now have exactly 2 messages (1 user, 1 assistant) - NO duplicate user messages!
        conv.refresh_from_db()
        self.assertEqual(conv.messages.count(), 2)
        self.assertEqual(conv.messages.filter(role='user').count(), 1)
        self.assertEqual(conv.messages.filter(role='assistant').count(), 1)

    def test_parse_reset_time_utility(self):
        """Tests parsing of various Groq rate limit reset header formats."""
        self.assertEqual(parse_reset_time('480ms'), 0.48)
        self.assertEqual(parse_reset_time('1.38s'), 1.38)
        self.assertEqual(parse_reset_time('2s'), 2.0)
        self.assertEqual(parse_reset_time('1m26.4s'), 86.4)
        self.assertEqual(parse_reset_time('5'), 5.0)
        self.assertIsNone(parse_reset_time(None))
        self.assertIsNone(parse_reset_time(''))


class LearningHistoryTests(TestCase):
    """Feature 8: Tests for unified student learning history."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='historystudent', password='password123')
        self.client.force_login(self.user)

        # Seed data
        Conversation.objects.create(user=self.user, title="Deep Learning Basics")
        SavedExplanation.objects.create(
            user=self.user,
            topic="Transformers Architecture",
            subject="NLP",
            detailed_explanation="Self-attention mechanism and multi-head attention."
        )
        QuizRecord.objects.create(
            user=self.user,
            topic="Neural Networks",
            score=5,
            total_questions=5,
            percentage=100.0,
            completed=True
        )

    def test_learning_history_all(self):
        response = self.client.get('/api/history/?type=all')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['chats']), 1)
        self.assertEqual(len(data['explanations']), 1)
        self.assertEqual(len(data['quizzes']), 1)

    def test_learning_history_search(self):
        response = self.client.get('/api/history/?type=all&q=Transformers')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['explanations']), 1)
        self.assertEqual(len(data['chats']), 0)


class OriginalChatbotTests(TestCase):
    """Preserve all baseline model and API checks."""

    def setUp(self):
        self.client = Client()

    def test_conversation_creation(self):
        conv = Conversation.objects.create(title="Baseline Chat")
        self.assertEqual(conv.title, "Baseline Chat")
        self.assertIsNotNone(conv.id)

    def test_title_generation_from_prompt(self):
        conv = Conversation.objects.create()
        prompt = "How do I implement a binary search tree in Python?"
        conv.generate_title_from_prompt(prompt)
        self.assertTrue(len(conv.title) <= 50)
        self.assertIn("binary search", conv.title)

    def test_message_cascade_delete(self):
        conv = Conversation.objects.create(title="Cascade Chat")
        Message.objects.create(conversation=conv, role="user", content="Hello!")
        Message.objects.create(conversation=conv, role="assistant", content="Hi!")
        self.assertEqual(conv.messages.count(), 2)
        conv.delete()
        self.assertEqual(Message.objects.filter(conversation_id=conv.id).count(), 0)

    def test_index_view(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', response.cookies)

    def test_status_endpoint(self):
        response = self.client.get('/api/status/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertIn('supported_models', data)


class DocumentExtractionTests(TestCase):
    """Deep test suite for document text extraction and OCR handling."""

    def test_extract_txt(self):
        content = b"Data Structures and Algorithms in Python"
        res = extract_text_from_file(io.BytesIO(content), "notes.txt")
        self.assertTrue(res['success'])
        self.assertEqual(res['file_type'], 'txt')
        self.assertEqual(res['extracted_text'], "Data Structures and Algorithms in Python")
        self.assertEqual(res['word_count'], 6)

    def test_extract_docx(self):
        import docx
        doc = docx.Document()
        doc.add_heading('Operating Systems Notes', 0)
        doc.add_paragraph('Virtual memory maps virtual addresses to physical pages.')
        bio = io.BytesIO()
        doc.save(bio)
        bio.seek(0)

        res = extract_text_from_file(bio, "lecture.docx")
        self.assertTrue(res['success'])
        self.assertEqual(res['file_type'], 'docx')
        self.assertIn("Virtual memory", res['extracted_text'])

    def test_extract_image_metadata(self):
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)

        res = extract_text_from_file(bio, "diagram.png")
        self.assertTrue(res['success'])
        self.assertEqual(res['file_type'], 'png')
        self.assertTrue(len(res['extracted_text']) > 0)

    def test_unsupported_file_type(self):
        res = extract_text_from_file(io.BytesIO(b"fake data"), "program.exe")
        self.assertFalse(res['success'])
        self.assertIn("Unsupported file type", res['error'])
