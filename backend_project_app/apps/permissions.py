from rest_framework import permissions
from django.shortcuts import get_object_or_404
from apps.models import Class, ClassMember

class IsFaceRegisteredMemberOrCreator(permissions.BasePermission):
    """
    Quyền truy cập tùy chỉnh:
    - Nếu là người tạo lớp: Được phép
    - Nếu là thành viên lớp: Phải có face_registered = True mới được phép
    """
    message = "Bạn cần hoàn tất đăng ký khuôn mặt để xem nội dung hoặc tương tác trong lớp học này."

    def has_permission(self, request, view):
        # Lấy class_id từ view kwargs
        class_id = view.kwargs.get('class_id')
        if not class_id:
            return False

        class_room = get_object_or_404(Class, id=class_id)
        
        # 1. Nếu là người tạo lớp (Creator) -> Bỏ qua check khuôn mặt
        if class_room.creator == request.user:
            return True
            
        # 2. Nếu là thành viên lớp -> Kiểm tra face_registered
        try:
            member = ClassMember.objects.get(user=request.user, class_room=class_room)
            return member.face_registered
        except ClassMember.DoesNotExist:
            self.message = "Bạn không phải thành viên của lớp học này."
            return False
