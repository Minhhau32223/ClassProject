import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. Users
class CustomUser(AbstractUser):
    """
    Bảng Users lưu trữ thông tin tài khoản người dùng.
    Mặc định AbstractUser đã cung cấp id (PK), username (varchar), email (varchar) 
    và password (đóng vai trò như password_hash).
    created_at có thể ánh xạ dựa trên date_joined của AbstractUser hoặc tạo mới dưới đây.
    """
    full_name = models.CharField(max_length=255, blank=True, verbose_name="Họ và tên")
    # Thay vì dùng date_joined, tạo riêng created_at theo đúng yêu cầu DB
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    def save(self, *args, **kwargs):
        # Tự động gán full_name nếu để trống
        if not self.full_name:
            self.full_name = f"{self.first_name} {self.last_name}".strip()
        if not self.full_name:
            self.full_name = self.username
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

# 2. Classes
class Class(models.Model):
    """ Bảng Classes lưu trữ thông tin các lớp học """
    class_code = models.CharField(max_length=6, unique=True, blank=True, verbose_name="Mã lớp học")
    class_name = models.CharField(max_length=255, verbose_name="Tên lớp học")
    creator = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_classes', verbose_name="Người tạo (creator_id)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    def save(self, *args, **kwargs):
        # Hệ thống tự động sinh mã lớp (Class Code) ngẫu nhiên 6 ký tự
        if not self.class_code:
            self.class_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            while Class.objects.filter(class_code=self.class_code).exists():
                self.class_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.class_name} ({self.class_code})"

# 3. ClassMembers (Thực Thể Trung Gian)
class ClassMember(models.Model):
    """ Bảng ClassMembers lưu trữ thông tin người tham gia lớp học """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='memberships', verbose_name="Người dùng (user_id)")
    class_room = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='members', verbose_name="Lớp học (class_id)")
    # Trạng thái đăng ký khuôn mặt mặc định là False
    face_registered = models.BooleanField(default=False, verbose_name="Trạng thái đăng ký khuôn mặt")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tham gia")

    class Meta:
        unique_together = ('user', 'class_room')

    def __str__(self):
        return f"{self.user.username} - {self.class_room.class_name}"

# 4. FaceRegistrations
class FaceRegistration(models.Model):
    """ 
    Bảng FaceRegistrations lưu dữ liệu nhận diện khuôn mặt đại diện.
    Không lưu ảnh gốc, chỉ lưu vector đặc trưng sau khi đăng ký đầy đủ các góc cạnh.
    """
    class_member = models.OneToOneField(ClassMember, on_delete=models.CASCADE, related_name='face_registration', verbose_name="Thành viên lớp (class_member_id)")
    embedding_vector = models.TextField(verbose_name="Vector đặc trưng") # Lưu trữ dưới dạng chuỗi text (JSON hoặc CSV)
    registered_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đăng ký")

    def __str__(self):
        return f"Face Vector cho {self.class_member.user.username}"

# 5. Posts
class Post(models.Model):
    """ Bảng Posts lưu bài viết, thông báo hiển thị trên timeline lớp học """
    class_room = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='posts', verbose_name="Lớp học (class_id)")
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts', verbose_name="Người đăng (author_id)")
    content = models.TextField(verbose_name="Nội dung bài viết")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đăng")

    def __str__(self):
        return f"Bài viết bởi {self.author.username} tại {self.class_room.class_name}"

# 6. Comments
class Comment(models.Model):
    """ Bảng Comments lưu bình luận của thành viên lớp trên các bài viết """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="Bài viết (post_id)")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments', verbose_name="Người bình luận (user_id)")
    content = models.TextField(verbose_name="Nội dung bình luận")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày bình luận")

    def __str__(self):
        return f"Bình luận của {self.user.username} trên Post {self.post.id}"

# 7. Documents
class Document(models.Model):
    """ Bảng Documents lưu thông tin file đính kèm bài viết (PDF, DOCX, PPTX) """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='documents', verbose_name="Bài viết (post_id)")
    file_name = models.CharField(max_length=255, verbose_name="Tên file")
    file_path = models.CharField(max_length=1024, verbose_name="Đường dẫn file")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tải lên")

    def __str__(self):
        return f"Tài liệu: {self.file_name}"

# 8. AttendanceSessions
class AttendanceSession(models.Model):
    """ Bảng AttendanceSessions quản lý phiên bản điểm danh được người tạo lớp mở """
    class_room = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendance_sessions', verbose_name="Lớp học (class_id)")
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_sessions', verbose_name="Người tạo (created_by)")
    session_token = models.CharField(max_length=255, unique=True, blank=True, verbose_name="Mã phiên/QR (session_token)")
    start_time = models.DateTimeField(verbose_name="Thời gian bắt đầu")
    end_time = models.DateTimeField(verbose_name="Thời gian kết thúc")

    def save(self, *args, **kwargs):
        # Tự động sinh session_token ngẫu nhiên để làm link hoặc QR nếu thiếu thiết lập
        if not self.session_token:
            self.session_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Phiên điểm danh {self.class_room.class_name} lúc {self.start_time}"

# 9. AttendanceRecords
class AttendanceRecord(models.Model):
    """ Bảng AttendanceRecords ghi nhận dữ liệu điểm danh thực tế của từ học viên """
    STATUS_CHOICES = (
        ('present', 'Có mặt (Present)'),
        ('late', 'Đi trễ (Late)'),
    )
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records', verbose_name="Phiên điểm danh (session_id)")
    class_member = models.ForeignKey(ClassMember, on_delete=models.CASCADE, related_name='attendance_records', verbose_name="Thành viên (class_member_id)")
    checkin_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian điểm danh")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Trạng thái (status)")

    class Meta:
        # Mỗi học viên chỉ có 1 bản ghi điểm danh thuộc về 1 phiên học duy nhất
        unique_together = ('session', 'class_member')

    def __str__(self):
        return f"Điểm danh {self.class_member.user.username} - {self.get_status_display()}"
