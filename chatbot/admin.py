from django.contrib import admin
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


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'study_streak', 'last_active_date', 'created_at')
    search_fields = ('user__username', 'user__email')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('created_at',)


class UploadedFileInline(admin.TabularInline):
    model = UploadedFile
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'id', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'user__username')
    inlines = [MessageInline, UploadedFileInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'content_preview', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content',)

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = 'Content'


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'file_type', 'file_size', 'user', 'conversation', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('filename', 'extracted_text')


@admin.register(SavedExplanation)
class SavedExplanationAdmin(admin.ModelAdmin):
    list_display = ('topic', 'subject', 'level', 'user', 'created_at')
    list_filter = ('subject', 'level', 'created_at')
    search_fields = ('topic', 'summary', 'detailed_explanation')


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ('role', 'subject', 'difficulty', 'user', 'created_at')
    list_filter = ('difficulty', 'created_at')
    search_fields = ('role', 'subject')


@admin.register(QuizRecord)
class QuizRecordAdmin(admin.ModelAdmin):
    list_display = ('topic', 'difficulty', 'score', 'total_questions', 'percentage', 'completed', 'user', 'created_at')
    list_filter = ('difficulty', 'completed', 'created_at')
    search_fields = ('topic',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'title', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('title', 'description', 'user__username')
