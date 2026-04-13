import shutil
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.models import AttendanceSession, Class, ClassMember, CustomUser, Post

TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class DocumentAndAttendanceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creator = CustomUser.objects.create_user(username='teacher', password='pass123')
        cls.student = CustomUser.objects.create_user(username='student', password='pass123')
        cls.class_room = Class.objects.create(class_name='DACN', creator=cls.creator)
        cls.member = ClassMember.objects.create(
            user=cls.student,
            class_room=cls.class_room,
            face_registered=True
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def test_uploaded_document_returns_file_url_and_post_contains_documents(self):
        self.client.force_authenticate(self.creator)
        post = Post.objects.create(
            class_room=self.class_room,
            author=self.creator,
            content='Thong bao co file'
        )

        upload = SimpleUploadedFile(
            'notice.txt',
            b'hello class',
            content_type='text/plain'
        )
        upload_response = self.client.post(
            reverse('upload_document', args=[self.class_room.id, post.id]),
            {'file_name': 'notice.txt', 'file': upload},
            format='multipart'
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        self.assertIn('file_url', upload_response.data)
        self.assertTrue(upload_response.data['file_url'].endswith('/media/documents/notice.txt'))

        list_response = self.client.get(reverse('class_posts', args=[self.class_room.id]))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data[0]['documents']), 1)
        self.assertEqual(list_response.data[0]['documents'][0]['file_name'], 'notice.txt')

    def test_checkin_is_rejected_when_attendee_is_outside_creator_network(self):
        self.client.force_authenticate(self.creator)
        now = timezone.now()
        create_response = self.client.post(
            reverse('create_attendance_session', args=[self.class_room.id]),
            {'start_time': (now - timedelta(minutes=5)).isoformat(), 'end_time': (now + timedelta(minutes=30)).isoformat()},
            REMOTE_ADDR='192.168.1.20'
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        session = AttendanceSession.objects.get(id=create_response.data['id'])
        self.assertEqual(session.creator_ip, '192.168.1.20')
        self.assertEqual(session.creator_network, '192.168.1.0/24')

        self.client.force_authenticate(self.student)
        checkin_response = self.client.post(
            reverse('attendance_checkin', args=[self.class_room.id, session.id]),
            {'checkin_image': SimpleUploadedFile('face.jpg', b'fake', content_type='image/jpeg')},
            format='multipart',
            REMOTE_ADDR='192.168.2.30'
        )

        self.assertEqual(checkin_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('cùng mạng nội bộ', checkin_response.data['error'])
