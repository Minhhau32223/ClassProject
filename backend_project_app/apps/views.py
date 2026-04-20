import json
import ipaddress
import uuid

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.core import signing
# from apps.utils import is_live_image

from apps.models import Class, ClassMember
from apps.serializers import RegisterSerializer, ClassSerializer, ClassMemberSerializer


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '').strip()


def get_private_network_for_ip(ip_text):
    try:
        ip_obj = ipaddress.ip_address(ip_text)
    except ValueError:
        return None

    if ip_obj.version == 4:
        if ip_obj.is_loopback:
            return ipaddress.ip_network('127.0.0.0/8')
        if ip_obj.is_private:
            return ipaddress.ip_network(f'{ip_obj}/24', strict=False)
        return None

    if ip_obj.is_loopback:
        return ipaddress.ip_network('::1/128')
    if ip_obj.is_private:
        return ipaddress.ip_network(f'{ip_obj}/64', strict=False)
    return None


def is_ip_allowed_for_session(ip_text, session):
    try:
        attendee_ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False

    if not session.creator_network:
        return False

    try:
        creator_network = ipaddress.ip_network(session.creator_network, strict=False)
    except ValueError:
        return False

    return attendee_ip.version == creator_network.version and attendee_ip in creator_network

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

from apps.face_runtime import (
    DEFAULT_FACE_MATCH_THRESHOLD,
    DEFAULT_FACE_MATCH_MARGIN,
    cosine_distance_between,
    get_embedding_from_image,
    get_average_embedding,
    registration_embeddings_are_consistent,
    validate_face_image,
)

# 6. API Đăng ký khuôn mặt
''''''
class ClassRegisterFaceView(APIView):
    """
    API đăng ký khuôn mặt cho thành viên lớp.
    Người dùng (thành viên lớp học) phải đăng nhập, truyền lên 3 ảnh:
    image_front, image_left, image_right (Định dạng multipart/form-data).
    """
    permission_classes = [IsAuthenticated]
   
    def post(self, request, class_id):
        # 1. Tìm lớp và xác nhận là thành viên
        class_room = get_object_or_404(Class, id=class_id)
        
        try:
            member = ClassMember.objects.get(user=request.user, class_room=class_room)
        except ClassMember.DoesNotExist:
            return Response({"error": "Bạn không phải thành viên của lớp học này."}, status=status.HTTP_403_FORBIDDEN)
            
        # 2. Lấy dữ liệu Upload Image (3 ảnh)
        image_front = request.FILES.get('image_front')
        image_left = request.FILES.get('image_left')
        image_right = request.FILES.get('image_right')
            

        if not (image_front and image_left and image_right):
            return Response({"error": "Yêu cầu cung cấp đủ 3 file ảnh khuôn mặt (Front, Left, Right)."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            try:
                # Lấy vector đặc trưng 512D từ 3 file ảnh bằng MTCNN + FaceNet
                emb_front, front_error, front_meta = validate_face_image(image_front.read())
                if not emb_front:
                    return Response(
                        {"error": front_error or "Không tìm thấy khuôn mặt trong ảnh Trực diện.", "meta": front_meta},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                emb_left, left_error, left_meta = validate_face_image(image_left.read())
                if not emb_left:
                    return Response(
                        {"error": left_error or "Không tìm thấy khuôn mặt trong ảnh góc Trái.", "meta": left_meta},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                emb_right, right_error, right_meta = validate_face_image(image_right.read())
                if not emb_right:
                    return Response(
                        {"error": right_error or "Không tìm thấy khuôn mặt trong ảnh góc Phải.", "meta": right_meta},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                is_consistent, worst_distance = registration_embeddings_are_consistent(
                    [emb_front, emb_left, emb_right]
                )
                if not is_consistent:
                    return Response(
                        {
                            "error": (
                                "Ba ảnh đăng ký chưa đủ nhất quán để tạo mẫu khuôn mặt. "
                                "Vui lòng chụp lại rõ mặt, đúng cùng một người và đủ ánh sáng."
                            ),
                            "worst_distance": float(worst_distance),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Tổng hợp 3 vector thành 1
                embedding_vector = get_average_embedding([emb_front, emb_left, emb_right])
                
            except RuntimeError as rte:
                return Response({
                    "error": "Hệ thống nhận diện khuôn mặt chưa sẵn sàng. Vui lòng kiểm tra lại AI backend.",
                    "details": str(rte)
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
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
            "message": "Đăng ký khuôn mặt 3D (Trung bình Vector) thành công!",
            "face_registered": True
        }, status=status.HTTP_200_OK)


class ClassFaceValidateView(APIView):
    """
    Kiểm tra nhanh một ảnh chụp từ camera có chứa khuôn mặt hợp lệ hay không
    trước khi cho phép người dùng chuyển sang bước chụp tiếp theo.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, class_id):
        class_room = get_object_or_404(Class, id=class_id)

        try:
            ClassMember.objects.get(user=request.user, class_room=class_room)
        except ClassMember.DoesNotExist:
            return Response({"error": "Bạn không phải thành viên của lớp học này."}, status=status.HTTP_403_FORBIDDEN)

        image = request.FILES.get('image')
        if not image:
            return Response({"error": "Thiếu ảnh kiểm tra khuôn mặt."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            embedding, error_message, diagnostics = validate_face_image(image.read())
        except RuntimeError as e:
            return Response({
                "error": "Hệ thống nhận diện khuôn mặt chưa sẵn sàng. Vui lòng kiểm tra lại AI backend.",
                "details": str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({
                "error": f"Lỗi xử lý ảnh khuôn mặt: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not embedding:
            return Response({
                "error": error_message or "Không phát hiện khuôn mặt trong ảnh. Vui lòng đưa mặt vào khung hình và chụp lại.",
                "meta": diagnostics,
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Ảnh hợp lệ.", "face_detected": True}, status=status.HTTP_200_OK)

# -------------------------------------------------------------
# PHẦN II: BÀI VIẾT VÀ BÌNH LUẬN
# -------------------------------------------------------------
from apps.models import Post, Comment
from apps.serializers import PostSerializer, CommentSerializer
from apps.permissions import IsFaceRegisteredMemberOrCreator

from django.db.models import Count

# 7. Danh sách Bài viết (Timeline Lớp học)
class PostListView(APIView):
    """
    Hiển thị timeline bài viết của một lớp hoặc tạo bài viết mới.
    Quyền: Bắt buộc đã Đăng ký khuôn mặt hoặc là người tạo lớp.
    """
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def get(self, request, class_id):
        class_room = get_object_or_404(Class, id=class_id)
        # Sắp xếp bài mới nhất lên đầu và thêm biến đếm comments
        posts = Post.objects.filter(class_room=class_room).annotate(
            comment_count=Count('comments')
        ).order_by('-created_at')
        serializer = PostSerializer(posts, many=True, context={'request': request})
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
        serializer = PostSerializer(post, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# 7.5. Sửa & Xóa bài viết — PUT/DELETE /posts/<post_id>/
class PostDetailView(APIView):
    """
    Cho phép tác giả bài viết sửa hoặc xóa bài viết.
    Người tạo lớp (creator) cũng có quyền xóa bài viết của người khác (nếu lớp có nhiều giáo viên/admin).
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, class_id, post_id):
        post = get_object_or_404(Post, id=post_id, class_room_id=class_id)

        # Chỉ người viết bài mới được sửa
        if post.author != request.user:
            return Response({"error": "Bạn chỉ có thể sửa bài viết của chính mình."}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content')
        if not content:
            return Response({"error": "Nội dung bài viết mới không được để trống."}, status=status.HTTP_400_BAD_REQUEST)

        post.content = content
        post.save()
        serializer = PostSerializer(post, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, class_id, post_id):
        post = get_object_or_404(Post, id=post_id, class_room_id=class_id)
        class_room = post.class_room

        # Tác giả bài viết hoặc Creator của lớp học mới được xóa
        is_author = post.author == request.user
        is_creator = class_room.creator == request.user

        if not (is_author or is_creator):
            return Response({"error": "Bạn không có quyền xóa bài viết này."}, status=status.HTTP_403_FORBIDDEN)

        post.delete()
        return Response({"message": "Đã xóa bài viết thành công."}, status=status.HTTP_200_OK)

# 8. Bình luận vào bài viết
class CommentCreateView(APIView):
    """
    Thành viên lớp hoặc giáo viên bình luận vào một bài viết.
    Quyền: Bắt buộc đã Đăng ký khuôn mặt hoặc là người tạo lớp.
    """
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def get(self, request, class_id, post_id):
        # Lấy danh sách tất cả comments của post, cũ nhất lên đầu
        post_obj = get_object_or_404(Post, id=post_id, class_room_id=class_id)
        comments = Comment.objects.filter(post=post_obj).select_related('user').order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, class_id, post_id):
        # class_id có trên URL để Permission hoạt động
        post_obj = get_object_or_404(Post, id=post_id, class_room_id=class_id)
        
        content = request.data.get('content')
        if not content:
            return Response({"error": "Nội dung bình luận (content) không được để trống."}, status=status.HTTP_400_BAD_REQUEST)
            
        comment = Comment.objects.create(post=post_obj, user=request.user, content=content)
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# 9. Sửa & Xóa bình luận — PUT/DELETE /comments/<comment_id>/
class CommentDetailView(APIView):
    """
    Cho phép chủ bài post hoặc chủ commment xóa hoặc sửa comment đó

    """
    permission_classes = [IsAuthenticated]

    def put(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)

        # Chỉ người viết comment mới được sửa
        if comment.user != request.user:
            return Response({"error": "Bạn chỉ có thể sửa bình luận của chính mình."}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content')
        if not content:
            return Response({"error": "Nội dung mới (content) không được để trống."}, status=status.HTTP_400_BAD_REQUEST)

        comment.content = content
        comment.save()
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        class_room = comment.post.class_room

        # Chủ comment hoặc Creator lớp mới được xóa
        is_owner = comment.user == request.user
        is_creator = class_room.creator == request.user

        if not (is_owner or is_creator):
            return Response({"error": "Bạn không có quyền xóa bình luận này."}, status=status.HTTP_403_FORBIDDEN)

        comment.delete()
        return Response({"message": "Đã xóa bình luận thành công."}, status=status.HTTP_200_OK)

# -------------------------------------------------------------
# PHẦN III: TÀI LIỆU (DOCUMENTS)
# -------------------------------------------------------------
from apps.models import Document
from apps.serializers import DocumentSerializer

# 10. Upload Tài liệu (file thật)
class DocumentUploadView(APIView):
    """
    Upload file thật (PDF, DOCX, PPTX...) đính kèm vào bài viết.
    Chỉ Creator lớp mới có quyền upload.
    Dùng form-data trong Postman, key 'file' là file upload.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, class_id, post_id):
        class_room = get_object_or_404(Class, id=class_id)

        # Chỉ người tạo lớp mới được upload tài liệu
        if class_room.creator != request.user:
            return Response({"error": "Chỉ người tạo lớp mới có quyền tải lên tài liệu."}, status=status.HTTP_403_FORBIDDEN)

        post_obj = get_object_or_404(Post, id=post_id, class_room=class_room)

        # Lấy file thật từ request.FILES
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"error": "Vui lòng chọn file cần upload (key: 'file')."}, status=status.HTTP_400_BAD_REQUEST)

        # Lấy tên hiển thị, mặc định dùng tên file gốc
        file_name = request.data.get('file_name', uploaded_file.name)

        document = Document.objects.create(
            post=post_obj,
            file_name=file_name,
            file=uploaded_file,
            file_path=''
        )
        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# 11. Danh sách Tài liệu của bài viết
class DocumentListView(APIView):
    """
    Lấy danh sách tài liệu kèm link download của một bài viết.
    Quyền: Thành viên đã đăng ký khuôn mặt hoặc người tạo lớp.
    """
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def get(self, request, class_id, post_id):
        # class_id có trên URL để check Permission khuôn mặt
        post_obj = get_object_or_404(Post, id=post_id, class_room_id=class_id)
        documents = Document.objects.filter(post=post_obj)
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# 12. Download file tài liệu
from django.http import FileResponse
import os

class DocDownloadView(APIView):
    """
    Download file tài liệu về máy.
    GET /documents/<doc_id>/download/
    Quyền: ClassMember hoặc Creator.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        document = get_object_or_404(Document, id=doc_id)
        class_room = document.post.class_room

        is_creator = class_room.creator == request.user
        is_member = ClassMember.objects.filter(user=request.user, class_room=class_room).exists()

        if not (is_creator or is_member):
            return Response({"error": "Bạn không có quyền tải tài liệu này."}, status=status.HTTP_403_FORBIDDEN)

        if not document.file:
            return Response({"error": "Tài liệu này chưa có file đính kèm."}, status=status.HTTP_404_NOT_FOUND)

        file_path = document.file.path
        if not os.path.exists(file_path):
            return Response({"error": "File không tồn tại trên server."}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=document.file_name
        )

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

        creator_ip = get_client_ip(request)
        creator_network = get_private_network_for_ip(creator_ip)
        if not creator_network:
            return Response(
                {"error": "Không thể mở phiên điểm danh vì IP của người tạo không thuộc mạng nội bộ hợp lệ."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        session = AttendanceSession.objects.create(
            class_room=class_room,
            created_by=request.user,
            start_time=start_time,
            end_time=end_time,
            creator_ip=creator_ip,
            creator_network=str(creator_network)
        )
        serializer = AttendanceSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, class_id):
        """
        Lấy danh sách tất cả phiên điểm danh của lớp (kèm filter active=true nếu cần).
        Học viên dùng endpoint này để biết có phiên đang mở không.
        """
        class_room = get_object_or_404(Class, id=class_id)
        now = timezone.now()

        active_only = request.query_params.get('active', 'false').lower() == 'true'

        if active_only:
            sessions = AttendanceSession.objects.filter(
                class_room=class_room,
                start_time__lte=now,
                end_time__gte=now
            ).order_by('-start_time')
        else:
            sessions = AttendanceSession.objects.filter(
                class_room=class_room
            ).order_by('-start_time')

        serializer = AttendanceSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

import logging
logger = logging.getLogger(__name__)


CHECKIN_CHALLENGE_MAX_AGE_SECONDS = 120
CHECKIN_REQUIRED_FRAME_COUNT = 3
CHECKIN_POSE_SEQUENCE = ["front", "left", "right"]


def build_checkin_challenge_token(*, class_id, session_id, user_id):
    payload = {
        "class_id": class_id,
        "session_id": session_id,
        "user_id": user_id,
        "steps": CHECKIN_POSE_SEQUENCE,
        "nonce": uuid.uuid4().hex,
    }
    return signing.dumps(payload)


def load_checkin_challenge_token(token, *, class_id, session_id, user_id):
    payload = signing.loads(token, max_age=CHECKIN_CHALLENGE_MAX_AGE_SECONDS)
    if (
        payload.get("class_id") != class_id
        or payload.get("session_id") != session_id
        or payload.get("user_id") != user_id
    ):
        raise signing.BadSignature("Challenge token mismatch")
    return payload


def pose_matches(expected_pose, detected_pose):
    if expected_pose == "front":
        return detected_pose in {"front", "left", "right"}
    if detected_pose == expected_pose:
        return True
    # Cho phep xoay chua hoan hao nhung da nghieng dung huong
    return False


def evaluate_checkin_frames(image_files, expected_steps):
    frame_results = []
    embeddings = []

    if len(image_files) != len(expected_steps):
        return None, None, None, {
            "error": f"Cần đúng {len(expected_steps)} ảnh cho thử thách điểm danh.",
        }

    for index, (image_file, expected_pose) in enumerate(zip(image_files, expected_steps), start=1):
        embedding, error_message, diagnostics = validate_face_image(image_file.read())
        diagnostics = diagnostics or {}
        detected_pose = diagnostics.get("pose_label", "unknown")

        if embedding is None:
            return None, None, None, {
                "error": error_message or f"Frame {index} không hợp lệ.",
                "step": index,
                "expected_pose": expected_pose,
                "detected_pose": detected_pose,
                "meta": diagnostics,
            }

        if not pose_matches(expected_pose, detected_pose):
            return None, None, None, {
                "error": (
                    f"Frame {index} chưa đúng động tác liveness yêu cầu. "
                    f"Cần tư thế '{expected_pose}' nhưng hệ thống nhận '{detected_pose}'."
                ),
                "step": index,
                "expected_pose": expected_pose,
                "detected_pose": detected_pose,
                "meta": diagnostics,
            }

        embeddings.append(embedding)
        frame_results.append(
            {
                "step": index,
                "expected_pose": expected_pose,
                "detected_pose": detected_pose,
                "yaw_score": diagnostics.get("yaw_score"),
                "face_confidence": diagnostics.get("face_confidence"),
            }
        )

    average_embedding = get_average_embedding(embeddings)
    if not average_embedding:
        return None, None, None, {
            "error": "Không tổng hợp được vector khuôn mặt từ chuỗi frame điểm danh.",
        }

    return average_embedding, embeddings, frame_results, None


def find_best_face_match_for_member(class_room, member, probe_embedding):
    registrations = (
        FaceRegistration.objects
        .filter(class_member__class_room=class_room, class_member__face_registered=True)
        .select_related("class_member__user")
    )

    candidates = []
    for registration in registrations:
        distance = cosine_distance_between(probe_embedding, registration.embedding_vector)
        candidates.append(
            {
                "class_member_id": registration.class_member_id,
                "username": registration.class_member.user.username,
                "distance": float(distance),
            }
        )

    if not candidates:
        raise FaceRegistration.DoesNotExist("Không có dữ liệu khuôn mặt nào trong lớp.")

    candidates.sort(key=lambda item: item["distance"])
    best_match = candidates[0]
    second_best = candidates[1] if len(candidates) > 1 else None
    margin = (
        float(second_best["distance"] - best_match["distance"])
        if second_best is not None else None
    )
    is_identity_match = best_match["class_member_id"] == member.id
    passes_threshold = best_match["distance"] < DEFAULT_FACE_MATCH_THRESHOLD
    passes_margin = second_best is None or margin >= DEFAULT_FACE_MATCH_MARGIN

    return {
        "best_match": best_match,
        "second_best": second_best,
        "margin": margin,
        "passes_threshold": passes_threshold,
        "passes_margin": passes_margin,
        "is_identity_match": is_identity_match,
        "candidates": candidates[:5],
    }


class AttendanceCheckInChallengeView(APIView):
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def get(self, request, class_id, session_id):
        class_room = get_object_or_404(Class, id=class_id)
        session = get_object_or_404(AttendanceSession, id=session_id, class_room=class_room)
        member = get_object_or_404(ClassMember, user=request.user, class_room=class_room)
        get_object_or_404(FaceRegistration, class_member=member)

        now = timezone.now()
        if now < session.start_time or now > session.end_time:
            return Response(
                {"error": "Phiên điểm danh hiện không khả dụng (Chưa mở hoặc đã đóng)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = build_checkin_challenge_token(
            class_id=class_room.id,
            session_id=session.id,
            user_id=request.user.id,
        )
        return Response(
            {
                "challenge_token": token,
                "steps": CHECKIN_POSE_SEQUENCE,
                "required_frames": CHECKIN_REQUIRED_FRAME_COUNT,
                "expires_in_seconds": CHECKIN_CHALLENGE_MAX_AGE_SECONDS,
            },
            status=status.HTTP_200_OK,
        )

class AttendanceCheckInView(APIView):
    """
    Học viên thực hiện điểm danh.
    Kiểm tra: Khuôn mặt đã đăng ký, Thuộc IP nội bộ, So khớp Vector.
    """
    permission_classes = [IsAuthenticated, IsFaceRegisteredMemberOrCreator]

    def post(self, request, class_id, session_id):
         # Log thông tin để debug
        logger.info(f"Check-in attempt: user={request.user.id}, session={session_id}, ip={get_client_ip(request)}")
        class_room = get_object_or_404(Class, id=class_id)
        session = get_object_or_404(AttendanceSession, id=session_id, class_room=class_room)
        
        # 1. Kiểm tra thời gian (Session Valid)
        now = timezone.now()
        if now < session.start_time or now > session.end_time:
            return Response({"error": "Phiên điểm danh hiện không khả dụng (Chưa mở hoặc đã đóng)."}, status=status.HTTP_400_BAD_REQUEST)
            
        member = get_object_or_404(ClassMember, user=request.user, class_room=class_room)
        
        # 2. Kiểm tra IP của người điểm danh có cùng mạng nội bộ với người tạo phiên hay không
        client_ip = get_client_ip(request)
        if not is_ip_allowed_for_session(client_ip, session):
            return Response(
                {"error": "Từ chối điểm danh. IP hiện tại không nằm trong cùng mạng nội bộ với người tạo phiên."},
                status=status.HTTP_403_FORBIDDEN
            )

        challenge_token = request.data.get("challenge_token")
        if not challenge_token:
            return Response(
                {"error": "Thiếu challenge_token cho phiên điểm danh."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            challenge_payload = load_checkin_challenge_token(
                challenge_token,
                class_id=class_room.id,
                session_id=session.id,
                user_id=request.user.id,
            )
        except signing.SignatureExpired:
            return Response(
                {"error": "Thử thách liveness đã hết hạn. Vui lòng mở lại camera để lấy thử thách mới."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except signing.BadSignature:
            return Response(
                {"error": "challenge_token không hợp lệ."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_files = request.FILES.getlist("checkin_images")
        if not image_files:
            return Response(
                {"error": "Yêu cầu cung cấp 5 ảnh điểm danh (checkin_images)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        get_object_or_404(FaceRegistration, class_member=member)

        try:
            checkin_vector, _, frame_results, frame_error = evaluate_checkin_frames(
                image_files=image_files,
                expected_steps=challenge_payload.get("steps", CHECKIN_POSE_SEQUENCE),
            )
        except RuntimeError as e:
            return Response({
                "error": "Hệ thống nhận diện khuôn mặt chưa sẵn sàng. Vui lòng liên hệ quản trị viên.",
                "details": str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({
                "error": f"Lỗi xử lý chuỗi ảnh điểm danh: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if frame_error:
            return Response(frame_error, status=status.HTTP_400_BAD_REQUEST)

        match_result = find_best_face_match_for_member(class_room, member, checkin_vector)
        best_match = match_result["best_match"]
        second_best = match_result["second_best"]
        margin = match_result["margin"]

        logger.info(
            "Check-in compare: user=%s best=%s best_distance=%.4f second=%s margin=%s threshold=%.2f margin_threshold=%.2f frames=%s",
            request.user.id,
            best_match["username"],
            best_match["distance"],
            second_best["username"] if second_best else None,
            f"{margin:.4f}" if margin is not None else None,
            DEFAULT_FACE_MATCH_THRESHOLD,
            DEFAULT_FACE_MATCH_MARGIN,
            frame_results,
        )

        if not match_result["passes_threshold"]:
            return Response(
                {
                    "error": "Khuôn mặt không khớp với dữ liệu đã đăng ký.",
                    "best_distance": best_match["distance"],
                    "threshold": DEFAULT_FACE_MATCH_THRESHOLD,
                    "frame_results": frame_results,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not match_result["is_identity_match"]:
            return Response(
                {
                    "error": "Khuôn mặt không khớp với dữ liệu đã đăng ký.",
                    "best_match_username": best_match["username"],
                    "best_distance": best_match["distance"],
                    "frame_results": frame_results,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not match_result["passes_margin"]:
            return Response(
                {
                    "error": "Khuôn mặt không khớp với dữ liệu đã đăng ký.",
                    "best_distance": best_match["distance"],
                    "second_best_distance": second_best["distance"] if second_best else None,
                    "margin": margin,
                    "required_margin": DEFAULT_FACE_MATCH_MARGIN,
                    "frame_results": frame_results,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Check-in success: user={request.user.id}, session={session_id}")
        # 4. Ghi nhận điểm danh
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            class_member=member,
            defaults={'status': 'present'}
        )
        
        if not created:
            return Response({"message": "Đã điểm danh trong phiên này trước đó rồi.", "already_checked": True}, status=status.HTTP_200_OK)
            
        serializer = AttendanceRecordSerializer(record)
        return Response({
            "message": "Điểm danh (Xác thực AI) thành công!",
            "best_distance": float(best_match["distance"]),
            "second_best_distance": float(second_best["distance"]) if second_best else None,
            "margin": float(margin) if margin is not None else None,
            "frame_results": frame_results,
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
