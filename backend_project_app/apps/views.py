from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404

from apps.models import Class, ClassMember
from apps.serializers import RegisterSerializer, ClassSerializer, ClassMemberSerializer

# 1. API Đăng ký người dùng
class RegisterView(APIView):
    """ API mở cho tất cả mọi người đăng ký tài khoản mới """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Đăng ký tài khoản thành công!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 2. API Tạo lớp học
class ClassCreateView(APIView):
    """ Bắt buộc đăng nhập. Người tạo lớp tự động trở thành quản trị viên của lớp. """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        class_name = request.data.get('class_name')
        if not class_name:
            return Response({"error": "Vui lòng nhập tên lớp học (class_name)"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo lớp học mới và gán creator là user đang request
        new_class = Class.objects.create(class_name=class_name, creator=request.user)
        serializer = ClassSerializer(new_class)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# 3. API Tham gia lớp học
class ClassJoinView(APIView):
    """
    Bắt buộc đăng nhập. Sau khi tham gia, trạng thái `face_registered` mặc định là False.
    Người dùng cần đăng ký khuôn mặt để xem nội dung và điểm danh.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        class_code = request.data.get('class_code')
        if not class_code:
            return Response({"error": "Vui lòng nhập mã lớp học (class_code)"}, status=status.HTTP_400_BAD_REQUEST)
        
        class_room = get_object_or_404(Class, class_code=class_code)
        
        # Người tạo không cần ấn tham gia lại
        if class_room.creator == request.user:
            return Response({"message": "Bạn là người tạo lớp học này nên không cần tham gia thêm."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra nếu đã tham gia từ trước
        if ClassMember.objects.filter(user=request.user, class_room=class_room).exists():
            return Response({"message": "Bạn đã tham gia lớp học này rồi."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo thông tin thành viên (face_registered = False mặc định trong Models)
        member = ClassMember.objects.create(user=request.user, class_room=class_room)
        serializer = ClassMemberSerializer(member)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# 4. API Lấy danh sách lớp học của tôi
class MyClassesView(APIView):
    """ Trả về các lớp do người dùng tạo và các lớp đang tham gia học """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        created_classes = Class.objects.filter(creator=request.user)
        joined_class_members = ClassMember.objects.filter(user=request.user)
        joined_classes = [member.class_room for member in joined_class_members]
        
        created_serializer = ClassSerializer(created_classes, many=True)
        joined_serializer = ClassSerializer(joined_classes, many=True)
        
        return Response({
            "created_classes": created_serializer.data,
            "joined_classes": joined_serializer.data
        }, status=status.HTTP_200_OK)

# 5. API Danh sách thành viên lớp học
class ClassMembersView(APIView):
    """ Trả về danh sách học viên kèm theo trạng thái đăng ký khuôn mặt """
    permission_classes = [IsAuthenticated]

    def get(self, request, class_id):
        class_room = get_object_or_404(Class, id=class_id)
        
        # Chỉ người tạo hoặc thành viên lớp mới được xem danh sách
        is_creator = class_room.creator == request.user
        is_member = ClassMember.objects.filter(user=request.user, class_room=class_room).exists()
        
        if not (is_creator or is_member):
            return Response({"error": "Bạn không có quyền truy cập dữ liệu lớp học này."}, status=status.HTTP_403_FORBIDDEN)
            
        members = ClassMember.objects.filter(class_room=class_room)
        serializer = ClassMemberSerializer(members, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

from apps.utils import get_embedding_from_image

# 6. API Đăng ký khuôn mặt
class ClassRegisterFaceView(APIView):
    """
    API đăng ký khuôn mặt cho thành viên lớp.
    Người dùng (thành viên lớp học) phải đăng nhập, truyền lên 1 danh sách/vector đặc trưng.
    (Hệ thống dùng MTCNN/Facenet để xử lý ảnh)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, class_id):
        # 1. Tìm lớp và xác nhận là thành viên
        class_room = get_object_or_404(Class, id=class_id)
        
        try:
            member = ClassMember.objects.get(user=request.user, class_room=class_room)
        except ClassMember.DoesNotExist:
            return Response({"error": "Bạn không phải thành viên của lớp học này."}, status=status.HTTP_403_FORBIDDEN)
            
        # 2. Lấy dữ liệu Upload Image
        image_file = request.FILES.get('face_image')
        if not image_file:
            # Fallback nếu client chưa chuyển qua dạng Upload File cho giai đoạn test này
            return Response({"error": "Yêu cầu cung cấp file ảnh khuôn mặt (face_image)."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Lấy vector đặc trưng 512D từ file ảnh bằng MTCNN + FaceNet
            image_bytes = image_file.read()
            embedding_vector = get_embedding_from_image(image_bytes)
            
            if not embedding_vector:
                return Response({"error": "Không tìm thấy khuôn mặt trong ảnh tải lên."}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            # Nếu chưa cài thư viện AI, chặn ngay lập tức
            return Response({"error": f"Lỗi trích xuất: {str(e)}. Hãy chắc chắn hệ thống Backend đã cài đủ thư viện AI."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        from apps.models import FaceRegistration
        
        # Cập nhật nếu đã có, hoặc tạo mới nếu chưa
        face_reg, created = FaceRegistration.objects.update_or_create(
            class_member=member,
            defaults={'embedding_vector': str(embedding_vector)}
        )
        
        # Đánh dấu đã đăng ký khuôn mặt để Unlock các chức năng khác
        member.face_registered = True
        member.save()
        
        return Response({
            "message": "Đăng ký khuôn mặt bằng AI đại diện thành công!",
            "face_registered": True
        }, status=status.HTTP_200_OK)

# -------------------------------------------------------------
# PHẦN II: BÀI VIẾT VÀ BÌNH LUẬN
# -------------------------------------------------------------
from apps.models import Post, Comment
from apps.serializers import PostSerializer, CommentSerializer
from apps.permissions import IsFaceRegisteredMemberOrCreator

# 7. Danh sách Bài viết (Timeline Lớp học)
class PostListView(APIView):
    """
    Hiển thị timeline bài viết của một lớp hoặc tạo bài viết mới.
    Quyền: Bắt buộc đã Đăng ký khuôn mặt hoặc là người tạo lớp.
    """
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def get(self, request, class_id):
        class_room = get_object_or_404(Class, id=class_id)
        # Sắp xếp bài mới nhất lên đầu
        posts = Post.objects.filter(class_room=class_room).order_by('-created_at')
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, class_id):
        class_room = get_object_or_404(Class, id=class_id)
        # Chỉ người tạo lớp mới được đăng bài (Đề bài: "Người tạo lớp đăng bài")
        if class_room.creator != request.user:
            return Response({"error": "Chỉ người tạo lớp mới được quyền đăng bài."}, status=status.HTTP_403_FORBIDDEN)
            
        content = request.data.get('content')
        if not content:
            return Response({"error": "Nội dung bài viết (content) không được để trống."}, status=status.HTTP_400_BAD_REQUEST)
            
        post = Post.objects.create(class_room=class_room, author=request.user, content=content)
        serializer = PostSerializer(post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# 8. Bình luận vào bài viết
class CommentCreateView(APIView):
    """
    Thành viên lớp hoặc giáo viên bình luận vào một bài viết.
    Quyền: Bắt buộc đã Đăng ký khuôn mặt hoặc là người tạo lớp.
    """
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def post(self, request, class_id, post_id):
        # class_id có trên URL để Permission hoạt động
        post_obj = get_object_or_404(Post, id=post_id, class_room_id=class_id)
        
        content = request.data.get('content')
        if not content:
            return Response({"error": "Nội dung bình luận (content) không được để trống."}, status=status.HTTP_400_BAD_REQUEST)
            
        comment = Comment.objects.create(post=post_obj, user=request.user, content=content)
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# -------------------------------------------------------------
# PHẦN III: TÀI LIỆU (DOCUMENTS)
# -------------------------------------------------------------
from apps.models import Document
from apps.serializers import DocumentSerializer

# 9. Upload Tài liệu
class DocumentUploadView(APIView):
    """
    Giáo viên tải tài liệu đính kèm vào bài viết.
    Chỉ Creator mới có quyền Upload.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, class_id, post_id):
        class_room = get_object_or_404(Class, id=class_id)
        
        # Chỉ người tạo lớp mới được upload tài liệu
        if class_room.creator != request.user:
            return Response({"error": "Chỉ người tạo lớp mới có quyền tải lên tài liệu."}, status=status.HTTP_403_FORBIDDEN)
            
        post_obj = get_object_or_404(Post, id=post_id, class_room=class_room)
        
        # Handle actual file upload
        uploaded_file = request.FILES.get('file')
        file_name = request.data.get('file_name', '')
        file_path = request.data.get('file_path', '')
        
        # If file is uploaded, use it. Otherwise fall back to file_name/file_path
        if uploaded_file:
            document = Document.objects.create(
                post=post_obj, 
                file_name=uploaded_file.name,
                file=uploaded_file
            )
        elif file_name and file_path:
            document = Document.objects.create(
                post=post_obj, 
                file_name=file_name, 
                file_path=file_path
            )
        else:
            return Response({"error": "Vui lòng cung cấp file hoặc cả tên file (file_name) và đường dẫn (file_path)."}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# 10. Tải/Xem Tài liệu
class DocumentListView(APIView):
    """
    Lấy danh sách tài liệu của một bài viết.
    Quyền: Thành viên đã đăng ký khuôn mặt hoặc người tạo lớp.
    """
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def get(self, request, class_id, post_id):
        # class_id có trên URL để check Permission khuôn mặt
        post_obj = get_object_or_404(Post, id=post_id, class_room_id=class_id)
        documents = Document.objects.filter(post=post_obj)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# -------------------------------------------------------------
# PHẦN IV: ĐIỂM DANH (ATTENDANCE)
# -------------------------------------------------------------
from apps.models import AttendanceSession, AttendanceRecord, FaceRegistration
from apps.serializers import AttendanceSessionSerializer, AttendanceRecordSerializer
from django.utils import timezone
import math

class AttendanceSessionCreateView(APIView):
    """
    Người tạo lớp mở phiên điểm danh, sinh link/QR và cấu hình thời gian hiệu lực.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, class_id):
        class_room = get_object_or_404(Class, id=class_id)
        
        # Chỉ người tạo mới được mở phiên
        if class_room.creator != request.user:
            return Response({"error": "Chỉ người tạo lớp mới được mở phiên điểm danh."}, status=status.HTTP_403_FORBIDDEN)
            
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        
        if not start_time or not end_time:
            return Response({"error": "Cần cung cấp thời gian bắt đầu (start_time) và kết thúc (end_time)."}, status=status.HTTP_400_BAD_REQUEST)
            
        session = AttendanceSession.objects.create(
            class_room=class_room,
            created_by=request.user,
            start_time=start_time,
            end_time=end_time
        )
        serializer = AttendanceSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

from apps.utils import get_embedding_from_image, compare_faces

class AttendanceCheckInView(APIView):
    """
    Học viên thực hiện điểm danh.
    Kiểm tra: Khuôn mặt đã đăng ký, Thuộc IP nội bộ, So khớp Vector.
    """
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def post(self, request, class_id, session_id):
        class_room = get_object_or_404(Class, id=class_id)
        session = get_object_or_404(AttendanceSession, id=session_id, class_room=class_room)
        
        # 1. Kiểm tra thời gian (Session Valid)
        now = timezone.now()
        if now < session.start_time or now > session.end_time:
            return Response({"error": "Phiên điểm danh hiện không khả dụng (Chưa mở hoặc đã đóng)."}, status=status.HTTP_400_BAD_REQUEST)
            
        member = get_object_or_404(ClassMember, user=request.user, class_room=class_room)
        
        # 2. Kiểm tra IP Nội bộ (Giả lập đơn giản)
        # Trong thực tế, đọc từ request.META.get('REMOTE_ADDR')
        client_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        is_internal = client_ip.startswith('192.168.') or client_ip.startswith('10.') or client_ip == '127.0.0.1'
        if not is_internal:
            return Response({"error": "Từ chối truy cập. Bạn không sử dụng mạng nội bộ của trường."}, status=status.HTTP_403_FORBIDDEN)

        # 3. So khớp Vector khuôn mặt
        image_file = request.FILES.get('checkin_image')
        if not image_file:
             return Response({"error": "Yêu cầu cung cấp file ảnh chụp hiện tại (checkin_image)."}, status=status.HTTP_400_BAD_REQUEST)
             
        face_reg = get_object_or_404(FaceRegistration, class_member=member)
        
        try:
            # Dùng MTCNN & FaceNet lấy đặc trưng từ ảnh chụp điểm danh
            checkin_bytes = image_file.read()
            checkin_vector = get_embedding_from_image(checkin_bytes)
            
            if not checkin_vector:
                return Response({"error": "Không tìm thấy khuôn mặt trong ảnh điểm danh tải lên."}, status=status.HTTP_400_BAD_REQUEST)
            
            registered_vector = face_reg.embedding_vector
            
            # Hàm so sánh bằng Cosine Similarity
            is_match, distance = compare_faces(checkin_vector, registered_vector, threshold=0.45)
            
            if not is_match:
                return Response({
                    "error": "Nhận diện khuôn mặt thất bại (Không khớp với dữ liệu đăng ký).",
                    "distance": float(distance)
                 }, status=status.HTTP_400_BAD_REQUEST)
                 
        except Exception as e:
            return Response({"error": f"Lỗi tính toán AI: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        # 4. Ghi nhận điểm danh
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            class_member=member,
            defaults={'status': 'present'}
        )
        
        if not created:
            return Response({"message": "Bạn đã điểm danh trong phiên này trước đó rồi."}, status=status.HTTP_200_OK)
            
        serializer = AttendanceRecordSerializer(record)
        return Response({
            "message": "Điểm danh (Xác thực AI) thành công!",
            "distance": float(distance),
            "record": serializer.data
        }, status=status.HTTP_201_CREATED)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from apps.models import Class, AttendanceSession, AttendanceRecord, ClassMember

class AttendanceStatsView(APIView):
    """
    Thống kê điểm danh của một lớp học.
    (Giáo viên thấy tổng quan, Sinh viên thấy số buổi mình đi)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, class_id):
        class_room = get_object_or_404(Class, id=class_id)
        
        is_creator = class_room.creator == request.user
        
        try:
            member = ClassMember.objects.get(user=request.user, class_room=class_room)
            is_member = True
        except ClassMember.DoesNotExist:
            is_member = False
            
        if not (is_creator or is_member):
             return Response({"error": "Không có quyền truy cập thống kê."}, status=status.HTTP_403_FORBIDDEN)
             
        # Tổng số phiên điểm danh đã tạo
        total_sessions = AttendanceSession.objects.filter(class_room=class_room).count()
        
        if is_creator:
            # ======= GÓC NHÌN GIÁO VIÊN =======
            # Lấy danh sách record để đếm số lần có mặt của mỗi member
            members = ClassMember.objects.filter(class_room=class_room)
            stats = []
            for m in members:
                present_count = AttendanceRecord.objects.filter(class_member=m, status='present').count()
                stats.append({
                    "user_id": m.user.id,
                    "student_name": m.user.full_name,
                    "total_sessions": total_sessions,
                    "present_count": present_count,
                    "absent_count": total_sessions - present_count,
                    "attendance_rate": f"{round((present_count/total_sessions*100), 2)}%" if total_sessions > 0 else "0%"
                })
            return Response({"role": "teacher", "class_sessions": total_sessions, "stats": stats}, status=status.HTTP_200_OK)
            
        else:
            # ======= GÓC NHÌN HỌC VIÊN =======
            present_count = AttendanceRecord.objects.filter(class_member=member, status='present').count()
            return Response({
                "role": "student",
                "class_sessions": total_sessions,
                "present_count": present_count,
                "absent_count": total_sessions - present_count,
                "attendance_rate": f"{round((present_count/total_sessions*100), 2)}%" if total_sessions > 0 else "0%"
            }, status=status.HTTP_200_OK)
