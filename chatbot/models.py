import uuid
import json
import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Extends Django User model with student metrics such as study streak.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    study_streak = models.PositiveIntegerField(default=1)
    last_active_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile (Streak: {self.study_streak})"

    def record_activity(self):
        """
        Updates the study streak based on activity date.
        - If active today: streak unchanged.
        - If active yesterday: streak increments by 1.
        - If gap > 1 day: streak resets to 1.
        """
        today = timezone.now().date()
        last_date = self.last_active_date
        if hasattr(last_date, 'date'):
            last_date = last_date.date()

        if last_date == today:
            return self.study_streak

        if last_date:
            delta_days = (today - last_date).days
            if delta_days == 1:
                self.study_streak += 1
            elif delta_days > 1:
                self.study_streak = 1
        else:
            self.study_streak = 1

        self.last_active_date = today
        self.save(update_fields=['study_streak', 'last_active_date'])
        return self.study_streak

    def to_dict(self):
        return {
            'username': self.user.username,
            'email': self.user.email,
            'full_name': self.user.get_full_name() or self.user.username,
            'study_streak': self.study_streak,
            'last_active_date': self.last_active_date.isoformat(),
        }


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()


class Conversation(models.Model):
    """
    Represents an isolated chat session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
            models.Index(fields=['user', '-updated_at']),
        ]

    def __str__(self):
        return self.title

    def generate_title_from_prompt(self, prompt: str):
        """
        Derives a concise, meaningful title from the initial user prompt.
        """
        clean_text = ' '.join(prompt.strip().split())
        if len(clean_text) > 48:
            truncated = clean_text[:45].rsplit(' ', 1)[0]
            self.title = truncated + '...' if truncated else clean_text[:45] + '...'
        else:
            self.title = clean_text or 'New Chat'
        self.save(update_fields=['title', 'updated_at'])

    def to_dict(self):
        """
        Summary dictionary representation for conversation lists.
        """
        first_msg = self.messages.order_by('created_at').first()
        last_msg = self.messages.order_by('-created_at').first()
        return {
            'id': str(self.id),
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'message_count': self.messages.count(),
            'snippet': last_msg.content[:80] if last_msg else (first_msg.content[:80] if first_msg else ''),
            'file_count': self.uploaded_files.count(),
        }

    def to_dict_full(self):
        """
        Full conversation representation with all ordered messages and files.
        """
        messages_qs = self.messages.order_by('created_at')
        files_qs = self.uploaded_files.order_by('created_at')
        return {
            'id': str(self.id),
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'messages': [m.to_dict() for m in messages_qs],
            'files': [f.to_dict() for f in files_qs],
        }


class Message(models.Model):
    """
    Represents an individual message exchanged in a conversation.
    """
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f"{self.role.capitalize()}: {self.content[:40]}"

    def to_dict(self):
        return {
            'id': str(self.id),
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
        }


class UploadedFile(models.Model):
    """
    Stores metadata and extracted text for files uploaded during AI chat sessions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_files',
        null=True,
        blank=True
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='uploaded_files',
        null=True,
        blank=True
    )
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.IntegerField(default=0)  # bytes
    extracted_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.file_type})"

    def to_dict(self):
        return {
            'id': str(self.id),
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'char_count': len(self.extracted_text),
            'snippet': self.extracted_text[:120] if self.extracted_text else '',
            'created_at': self.created_at.isoformat(),
        }


class SavedExplanation(models.Model):
    """
    Topic explanations generated by AI and saved by students.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_explanations'
    )
    topic = models.CharField(max_length=255)
    subject = models.CharField(max_length=100, default='General')
    level = models.CharField(max_length=50, default='Intermediate')
    summary = models.TextField(blank=True)
    detailed_explanation = models.TextField()
    examples = models.TextField(blank=True)
    code_snippets = models.TextField(blank=True)
    interview_tips = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.topic} ({self.subject})"

    def to_dict(self):
        return {
            'id': str(self.id),
            'topic': self.topic,
            'subject': self.subject,
            'level': self.level,
            'summary': self.summary,
            'detailed_explanation': self.detailed_explanation,
            'examples': self.examples,
            'code_snippets': self.code_snippets,
            'interview_tips': self.interview_tips,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class InterviewSession(models.Model):
    """
    Saved technical interview preparation sessions.
    Stores data as JSON-encoded string for broad SQLite compatibility.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='interview_sessions'
    )
    subject = models.CharField(max_length=150)
    role = models.CharField(max_length=150)
    difficulty = models.CharField(max_length=50, default='Intermediate')
    raw_data = models.TextField(default='{}')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.role} - {self.subject} ({self.difficulty})"

    def get_data(self):
        try:
            return json.loads(self.raw_data)
        except Exception:
            return {}

    def set_data(self, val):
        self.raw_data = json.dumps(val)

    def to_dict(self):
        parsed = self.get_data()
        return {
            'id': str(self.id),
            'subject': self.subject,
            'role': self.role,
            'difficulty': self.difficulty,
            'data': parsed,
            'question_count': len(parsed.get('questions', [])) if isinstance(parsed, dict) else 0,
            'created_at': self.created_at.isoformat(),
        }


class QuizRecord(models.Model):
    """
    MCQ Quiz sessions and results.
    Stores questions_data as JSON-encoded string for broad SQLite compatibility.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quizzes'
    )
    topic = models.CharField(max_length=255)
    difficulty = models.CharField(max_length=50, default='Medium')
    total_questions = models.IntegerField(default=5)
    score = models.IntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)
    raw_questions = models.TextField(default='[]')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.topic} ({self.score}/{self.total_questions})"

    def get_questions(self):
        try:
            return json.loads(self.raw_questions)
        except Exception:
            return []

    def set_questions(self, val):
        self.raw_questions = json.dumps(val)

    def to_dict(self):
        return {
            'id': str(self.id),
            'topic': self.topic,
            'difficulty': self.difficulty,
            'total_questions': self.total_questions,
            'score': self.score,
            'percentage': self.percentage,
            'completed': self.completed,
            'questions_data': self.get_questions(),
            'created_at': self.created_at.isoformat(),
        }


class ActivityLog(models.Model):
    """
    Audit log of student learning activities for the dashboard feed.
    """
    ACTIVITY_TYPES = (
        ('chat', 'Chat Session'),
        ('quiz', 'Completed Quiz'),
        ('explanation', 'Explored Topic'),
        ('interview', 'Interview Practice'),
        ('upload', 'Uploaded Document'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    link_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.activity_type}: {self.title}"

    def to_dict(self):
        return {
            'id': str(self.id),
            'activity_type': self.activity_type,
            'title': self.title,
            'description': self.description,
            'link_id': self.link_id,
            'created_at': self.created_at.isoformat(),
        }
