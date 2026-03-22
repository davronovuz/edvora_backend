"""
Edvora - Exam Tests
Imtihonlar, natijalar, uy vazifalari
"""

import pytest
from django.utils import timezone
from rest_framework import status
from apps.exams.models import Exam, ExamResult, Homework, HomeworkSubmission


pytestmark = pytest.mark.django_db


class TestExamCRUD:
    """Imtihon CRUD testlari"""

    def test_create_exam(self, authenticated_client, create_group):
        group = create_group()
        data = {
            'title': 'Unit 1 Quiz',
            'group': str(group.id),
            'exam_type': 'quiz',
            'max_score': 100,
            'passing_score': 60,
            'exam_date': timezone.now().date().isoformat(),
            'duration_minutes': 45,
            'status': 'scheduled',
        }
        response = authenticated_client.post('/api/v1/exams/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Unit 1 Quiz'

    def test_list_exams(self, authenticated_client, create_exam):
        create_exam()
        response = authenticated_client.get('/api/v1/exams/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_retrieve_exam(self, authenticated_client, create_exam):
        exam = create_exam()
        response = authenticated_client.get(f'/api/v1/exams/{exam.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Test Exam'

    def test_filter_by_exam_type(self, authenticated_client, create_exam):
        create_exam(exam_type='quiz')
        response = authenticated_client.get('/api/v1/exams/?exam_type=quiz')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_delete_exam(self, authenticated_client, create_exam):
        exam = create_exam()
        response = authenticated_client.delete(f'/api/v1/exams/{exam.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestExamResults:
    """Imtihon natijalari testlari"""

    def test_bulk_grade(self, authenticated_client, create_exam, create_student):
        exam = create_exam()
        student1 = create_student(phone='+998901111111')
        student2 = create_student(phone='+998902222222', first_name='Ali')

        data = {
            'results': [
                {'student_id': str(student1.id), 'score': 85, 'status': 'graded'},
                {'student_id': str(student2.id), 'score': 45, 'status': 'graded'},
            ]
        }
        response = authenticated_client.post(
            f'/api/v1/exams/{exam.id}/bulk_grade/', data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['created'] == 2

    def test_exam_results_endpoint(self, authenticated_client, create_exam, create_student):
        exam = create_exam()
        student = create_student()
        ExamResult.objects.create(
            exam=exam, student=student, score=90, status='graded'
        )

        response = authenticated_client.get(f'/api/v1/exams/{exam.id}/results/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['results']) == 1
        assert response.data['data']['statistics']['average_score'] == 90

    def test_exam_statistics(self, authenticated_client, create_exam):
        exam = create_exam(status='completed')
        response = authenticated_client.get('/api/v1/exams/statistics/')
        assert response.status_code == status.HTTP_200_OK


class TestExamResultModel:
    """ExamResult model testlari"""

    def test_grade_letter(self, create_exam, create_student):
        exam = create_exam(max_score=100)
        student = create_student()

        result = ExamResult.objects.create(
            exam=exam, student=student, score=95, status='graded'
        )
        assert result.grade_letter == 'A'
        assert result.percentage == 95.0
        assert result.is_passed is True

        result.score = 55
        result.save()
        assert result.grade_letter == 'F'
        assert result.is_passed is False

    def test_exam_average_and_pass_rate(self, create_exam, create_student):
        exam = create_exam(max_score=100, passing_score=60)
        s1 = create_student(phone='+998911111111')
        s2 = create_student(phone='+998912222222', first_name='Test2')

        ExamResult.objects.create(exam=exam, student=s1, score=80, status='graded')
        ExamResult.objects.create(exam=exam, student=s2, score=40, status='graded')

        assert exam.average_score == 60.0
        assert exam.pass_rate == 50.0


class TestHomework:
    """Uy vazifasi testlari"""

    def test_create_homework(self, authenticated_client, create_group):
        group = create_group()
        today = timezone.now().date()
        data = {
            'title': 'Unit 1 Exercise',
            'description': 'Complete exercises 1-10',
            'group': str(group.id),
            'max_score': 10,
            'assigned_date': today.isoformat(),
            'due_date': (today + timezone.timedelta(days=7)).isoformat(),
        }
        response = authenticated_client.post('/api/v1/homeworks/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_homeworks(self, authenticated_client, create_group):
        group = create_group()
        today = timezone.now().date()
        Homework.objects.create(
            group=group, title='HW1', description='desc',
            max_score=10, assigned_date=today,
            due_date=today + timezone.timedelta(days=7),
        )
        response = authenticated_client.get('/api/v1/homeworks/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_homework_submissions(self, authenticated_client, create_group, create_student):
        group = create_group()
        student = create_student()
        today = timezone.now().date()
        hw = Homework.objects.create(
            group=group, title='HW1', description='desc',
            max_score=10, assigned_date=today,
            due_date=today + timezone.timedelta(days=7),
        )

        response = authenticated_client.get(f'/api/v1/homeworks/{hw.id}/submissions/')
        assert response.status_code == status.HTTP_200_OK

    def test_grade_submission(self, authenticated_client, create_group, create_student):
        group = create_group()
        student = create_student()
        today = timezone.now().date()
        hw = Homework.objects.create(
            group=group, title='HW1', description='desc',
            max_score=10, assigned_date=today,
            due_date=today + timezone.timedelta(days=7),
        )
        submission = HomeworkSubmission.objects.create(
            homework=hw, student=student,
            status='submitted', submitted_at=timezone.now(),
        )

        data = {'score': 8.5, 'feedback': 'Yaxshi!', 'status': 'graded'}
        response = authenticated_client.post(
            f'/api/v1/homework-submissions/{submission.id}/grade/', data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['score'] == '8.50'
