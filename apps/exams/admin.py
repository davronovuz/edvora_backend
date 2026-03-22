from django.contrib import admin
from .models import Exam, ExamResult, Homework, HomeworkSubmission


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'group', 'exam_type', 'exam_date', 'status']
    list_filter = ['exam_type', 'status']
    search_fields = ['title']


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ['exam', 'student', 'score', 'status', 'grade_letter']
    list_filter = ['status']


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ['title', 'group', 'assigned_date', 'due_date', 'status']
    list_filter = ['status']
    search_fields = ['title']


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = ['homework', 'student', 'score', 'status', 'submitted_at']
    list_filter = ['status']
