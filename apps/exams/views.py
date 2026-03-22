"""
Edvora - Exams & Homework Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Count, Q
from core.permissions import RoleBasedPermission
from .models import Exam, ExamResult, Homework, HomeworkSubmission, LessonPlan
from .serializers import (
    ExamListSerializer, ExamSerializer, ExamCreateSerializer,
    ExamResultSerializer, ExamResultCreateSerializer, BulkExamResultSerializer,
    HomeworkListSerializer, HomeworkSerializer, HomeworkCreateSerializer,
    HomeworkSubmissionSerializer, HomeworkSubmissionCreateSerializer,
    HomeworkGradeSerializer,
    LessonPlanListSerializer, LessonPlanSerializer, LessonPlanCreateSerializer,
)


class ExamViewSet(viewsets.ModelViewSet):
    """Imtihonlar CRUD + natijalar"""
    queryset = Exam.objects.select_related('group', 'group__course').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['group', 'exam_type', 'status']
    search_fields = ['title']
    ordering_fields = ['exam_date', 'created_at']
    ordering = ['-exam_date']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher'],
        'retrieve': ['owner', 'admin', 'teacher'],
        'create': ['owner', 'admin', 'teacher'],
        'update': ['owner', 'admin', 'teacher'],
        'partial_update': ['owner', 'admin', 'teacher'],
        'destroy': ['owner', 'admin'],
        'results': ['owner', 'admin', 'teacher'],
        'bulk_grade': ['owner', 'admin', 'teacher'],
        'statistics': ['owner', 'admin', 'teacher'],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            qs = qs.filter(group__teacher=user.teacher_profile)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ExamListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ExamCreateSerializer
        return ExamSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Imtihon natijalari"""
        exam = self.get_object()
        results = exam.results.select_related('student').all()
        serializer = ExamResultSerializer(results, many=True)

        return Response({
            'success': True,
            'data': {
                'exam': ExamListSerializer(exam).data,
                'results': serializer.data,
                'statistics': {
                    'total': results.count(),
                    'graded': results.filter(status='graded').count(),
                    'absent': results.filter(status='absent').count(),
                    'average_score': exam.average_score,
                    'pass_rate': exam.pass_rate,
                }
            }
        })

    @action(detail=True, methods=['post'])
    def bulk_grade(self, request, pk=None):
        """
        Bir vaqtda ko'p o'quvchini baholash

        POST /api/v1/exams/{id}/bulk_grade/
        {
            "results": [
                {"student_id": "uuid", "score": 85, "status": "graded"},
                {"student_id": "uuid", "score": 0, "status": "absent"}
            ]
        }
        """
        exam = self.get_object()
        results_data = request.data.get('results', [])

        created = 0
        updated = 0

        for item in results_data:
            student_id = item.get('student_id')
            score = item.get('score', 0)
            result_status = item.get('status', 'graded')
            feedback = item.get('feedback', '')

            result, was_created = ExamResult.objects.update_or_create(
                exam=exam,
                student_id=student_id,
                defaults={
                    'score': score,
                    'status': result_status,
                    'feedback': feedback,
                    'graded_by': request.user,
                    'graded_at': timezone.now(),
                }
            )

            if was_created:
                created += 1
            else:
                updated += 1

        return Response({
            'success': True,
            'message': f"Natijalar saqlandi: {created} ta yangi, {updated} ta yangilandi",
            'data': {
                'created': created,
                'updated': updated,
                'average_score': exam.average_score,
                'pass_rate': exam.pass_rate,
            }
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Imtihon statistikasi

        GET /api/v1/exams/statistics/?group_id=uuid
        """
        group_id = request.query_params.get('group_id')

        queryset = Exam.objects.filter(status='completed')
        if group_id:
            queryset = queryset.filter(group_id=group_id)

        exams = queryset.prefetch_related('results')

        data = []
        for exam in exams[:20]:
            data.append({
                'id': str(exam.id),
                'title': exam.title,
                'exam_date': str(exam.exam_date),
                'exam_type': exam.exam_type,
                'average_score': exam.average_score,
                'pass_rate': exam.pass_rate,
                'total_students': exam.results.filter(status='graded').count(),
            })

        return Response({
            'success': True,
            'data': data
        })


class ExamResultViewSet(viewsets.ModelViewSet):
    """Imtihon natijalari CRUD"""
    queryset = ExamResult.objects.select_related('exam', 'student').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['exam', 'student', 'status']
    ordering = ['-score']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher'],
        'retrieve': ['owner', 'admin', 'teacher'],
        'create': ['owner', 'admin', 'teacher'],
        'update': ['owner', 'admin', 'teacher'],
        'partial_update': ['owner', 'admin', 'teacher'],
        'destroy': ['owner', 'admin'],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ExamResultCreateSerializer
        return ExamResultSerializer

    def perform_create(self, serializer):
        serializer.save(graded_by=self.request.user, graded_at=timezone.now())


class HomeworkViewSet(viewsets.ModelViewSet):
    """Uy vazifalari CRUD"""
    queryset = Homework.objects.select_related('group', 'group__course').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['group', 'status']
    search_fields = ['title']
    ordering = ['-due_date']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher'],
        'retrieve': ['owner', 'admin', 'teacher'],
        'create': ['owner', 'admin', 'teacher'],
        'update': ['owner', 'admin', 'teacher'],
        'partial_update': ['owner', 'admin', 'teacher'],
        'destroy': ['owner', 'admin'],
        'submissions': ['owner', 'admin', 'teacher'],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            qs = qs.filter(group__teacher=user.teacher_profile)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return HomeworkListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return HomeworkCreateSerializer
        return HomeworkSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """Vazifaga topshirishlar"""
        homework = self.get_object()
        submissions = homework.submissions.select_related('student').all()

        return Response({
            'success': True,
            'data': {
                'homework': HomeworkListSerializer(homework).data,
                'submissions': HomeworkSubmissionSerializer(submissions, many=True).data,
                'statistics': {
                    'total_students': homework.group.students.filter(is_active=True).count(),
                    'submitted': submissions.exclude(status='pending').count(),
                    'graded': submissions.filter(status='graded').count(),
                    'submission_rate': homework.submission_rate,
                }
            }
        })


class HomeworkSubmissionViewSet(viewsets.ModelViewSet):
    """Vazifa topshirishlar CRUD"""
    queryset = HomeworkSubmission.objects.select_related('homework', 'student').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['homework', 'student', 'status']
    ordering = ['-submitted_at']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher'],
        'retrieve': ['owner', 'admin', 'teacher'],
        'create': ['owner', 'admin', 'teacher', 'registrar'],
        'update': ['owner', 'admin', 'teacher'],
        'partial_update': ['owner', 'admin', 'teacher'],
        'destroy': ['owner', 'admin'],
        'grade': ['owner', 'admin', 'teacher'],
    }

    def get_serializer_class(self):
        if self.action in ['create']:
            return HomeworkSubmissionCreateSerializer
        return HomeworkSubmissionSerializer

    def perform_create(self, serializer):
        serializer.save(
            submitted_at=timezone.now(),
            status='submitted'
        )

    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        """
        Vazifani baholash

        POST /api/v1/homework-submissions/{id}/grade/
        {"score": 8.5, "feedback": "Yaxshi!", "status": "graded"}
        """
        submission = self.get_object()
        serializer = HomeworkGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission.score = serializer.validated_data['score']
        submission.feedback = serializer.validated_data.get('feedback', '')
        submission.status = serializer.validated_data.get('status', 'graded')
        submission.graded_by = request.user
        submission.save()

        return Response({
            'success': True,
            'message': "Vazifa baholandi",
            'data': HomeworkSubmissionSerializer(submission).data
        })


class LessonPlanViewSet(viewsets.ModelViewSet):
    """Dars rejalari CRUD"""
    queryset = LessonPlan.objects.select_related('group', 'group__course', 'created_by').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['group', 'status']
    search_fields = ['title']
    ordering_fields = ['lesson_number', 'date', 'created_at']
    ordering = ['group', 'lesson_number']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher'],
        'retrieve': ['owner', 'admin', 'teacher'],
        'create': ['owner', 'admin', 'teacher'],
        'update': ['owner', 'admin', 'teacher'],
        'partial_update': ['owner', 'admin', 'teacher'],
        'destroy': ['owner', 'admin', 'teacher'],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            qs = qs.filter(group__teacher=user.teacher_profile)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return LessonPlanListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return LessonPlanCreateSerializer
        return LessonPlanSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
