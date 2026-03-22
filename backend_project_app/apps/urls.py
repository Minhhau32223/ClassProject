from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.views import RegisterView, ClassCreateView, ClassJoinView, MyClassesView, ClassMembersView, ClassRegisterFaceView, PostListView, CommentCreateView, DocumentUploadView, DocumentListView, AttendanceSessionCreateView, AttendanceCheckInView, AttendanceStatsView, SessionDetailView, SessionListView

urlpatterns = [
    # Auth Endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Class Core Endpoints
    path('classes/create/', ClassCreateView.as_view(), name='class_create'),
    path('classes/join/', ClassJoinView.as_view(), name='class_join'),
    path('classes/my/', MyClassesView.as_view(), name='classes_my'),
    path('classes/<int:class_id>/members/', ClassMembersView.as_view(), name='class_members'),
    path('classes/<int:class_id>/register-face/', ClassRegisterFaceView.as_view(), name='class_register_face'),
    
    # Posts & Comments Endpoints
    path('classes/<int:class_id>/posts/', PostListView.as_view(), name='class_posts'),
    path('classes/<int:class_id>/posts/<int:post_id>/comments/', CommentCreateView.as_view(), name='post_comments'),
    
    # Documents Endpoints
    path('classes/<int:class_id>/posts/<int:post_id>/documents/', DocumentListView.as_view(), name='post_documents'),
    path('classes/<int:class_id>/posts/<int:post_id>/documents/upload/', DocumentUploadView.as_view(), name='upload_document'),
    
    # Attendance Endpoints
    path('classes/<int:class_id>/attendance/sessions/', AttendanceSessionCreateView.as_view(), name='create_attendance_session'),
    path('classes/<int:class_id>/attendance/sessions/<int:session_id>/checkin/', AttendanceCheckInView.as_view(), name='attendance_checkin'),
    path('classes/<int:class_id>/attendance/stats/', AttendanceStatsView.as_view(), name='attendance_stats'),
    path('attendance/session/<int:session_id>/',SessionDetailView.as_view(),name='attendance_session_detail'),
    path('attendance/sessions/class/<int:class_id>/',SessionListView.as_view(),name='attendance_sessions_list'),
]
