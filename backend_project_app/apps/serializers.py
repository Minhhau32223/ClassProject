from rest_framework import serializers
from apps.models import CustomUser, Class, ClassMember

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer xử lý việc đăng ký tài khoản người dùng mới.
    Nhận dữ liệu (username, password, email, full_name) từ API trả về cho DB.
    """
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'email', 'full_name')

    def create(self, validated_data):
        # Sử dụng hàm create_user để tự động mã hóa mật khẩu (password hashing)
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            full_name=validated_data.get('full_name', '')
        )
        return user

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer hiển thị thông tin cơ bản của người dùng dạng đọc.
    """
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'full_name')

class ClassSerializer(serializers.ModelSerializer):
    """
    Serializer cho Lớp học (Class). Chứa thông tin bổ sung về người tạo lớp.
    """
    creator = UserSerializer(read_only=True)
    
    class Meta:
        model = Class
        fields = ('id', 'class_code', 'class_name', 'creator', 'created_at')

class ClassMemberSerializer(serializers.ModelSerializer):
    """
    Serializer cho Thành viên lớp học. Hiển thị thông tin người dùng, lớp và trạng thái khuôn mặt.
    """
    user = UserSerializer(read_only=True)
    class_room = ClassSerializer(read_only=True)
    
    class Meta:
        model = ClassMember
        fields = ('id', 'user', 'class_room', 'face_registered', 'joined_at')
from rest_framework import serializers
from apps.models import Post, Comment

class CommentSerializer(serializers.ModelSerializer):
    """ Serializer cho Bình luận """
    user_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = Comment
        fields = ('id', 'post', 'user', 'user_name', 'content', 'created_at')
        read_only_fields = ('user', 'post')

class PostSerializer(serializers.ModelSerializer):
    """ Serializer cho Bài viết và Kèm theo danh sách Bình luận """
    author_name = serializers.ReadOnlyField(source='author.full_name')
    comments = CommentSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = ('id', 'class_room', 'author', 'author_name', 'content', 'created_at', 'comments', 'comment_count')
        read_only_fields = ('author', 'class_room')
from rest_framework import serializers
from apps.models import Document

class DocumentSerializer(serializers.ModelSerializer):
    """ Serializer cho Tài liệu — trả về link download thật """
    file_url = serializers.SerializerMethodField()

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file_upload and request:
            return request.build_absolute_uri(obj.file_upload.url)
        return None

    class Meta:
        model = Document
        fields = ('id', 'post', 'file_name', 'file_path', 'uploaded_at')
        read_only_fields = ('post', )
from rest_framework import serializers
from apps.models import AttendanceSession, AttendanceRecord
from apps.serializers import UserSerializer

class AttendanceSessionSerializer(serializers.ModelSerializer):
    """ Serializer cho Phiên Điểm Danh """
    created_by_user = UserSerializer(source='created_by', read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ('id', 'class_room', 'created_by_user', 'session_token', 'start_time', 'end_time')
        read_only_fields = ('class_room', 'created_by')

class AttendanceRecordSerializer(serializers.ModelSerializer):
    """ Serializer cho Bản ghi Điểm danh của Học viên """
    student_name = serializers.ReadOnlyField(source='class_member.user.full_name')
    
    class Meta:
        model = AttendanceRecord
        fields = ('id', 'session', 'class_member', 'student_name', 'checkin_time', 'status')
        read_only_fields = ('session', 'class_member')
