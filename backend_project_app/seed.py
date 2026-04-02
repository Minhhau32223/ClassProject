import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_project_app.settings')
django.setup()

from apps.models import CustomUser, Class, ClassMember, FaceRegistration, Post, Comment
import random

def seed_data():
    print("Start Seeding Database...")
    
    # 1. Tạo 5 Users
    users = []
    for i in range(1, 6):
        username = f"user_seed_{i}"
        if not CustomUser.objects.filter(username=username).exists():
            user = CustomUser.objects.create_user(
                username=username,
                password="password123",
                email=f"{username}@example.com",
                full_name=f"Người dùng Hệ thống {i}"
            )
            users.append(user)
        else:
            users.append(CustomUser.objects.get(username=username))
    print(f"Created {len(users)} users.")

    # 2. Tạo 2 Lớp học
    classes = []
    if users:
        teacher = users[0]
        for i in range(1, 3):
            class_name = f"Lớp Học Mẫu {i} - Khoa CNTT"
            c, created = Class.objects.get_or_create(class_name=class_name, creator=teacher)
            classes.append(c)
    print(f"Created {len(classes)} classes.")

    # 3. Tạo Thành viên & Đăng ký khuôn mặt mẫu
    if classes and users:
        c1 = classes[0]
        # Thêm 4 user còn lại vào lớp 1
        for u in users[1:]:
            member, created = ClassMember.objects.get_or_create(user=u, class_room=c1)
            # Giả lập đã đăng ký khuôn mặt để có thể tương tác
            member.face_registered = True
            member.save()
            FaceRegistration.objects.get_or_create(
                class_member=member,
                defaults={'embedding_vector': f"[0.1, 0.2, 0.3, {random.random()}]"}
            )
    print("Added members and fake face registrations.")

    # 4. Tạo 5 bài viết
    if classes and users:
        c1 = classes[0]
        for i in range(1, 6):
            Post.objects.get_or_create(
                class_room=c1,
                author=users[0],
                content=f"Chào các em, đây là bài thông báo / thảo luận quan trọng số {i}. Nhớ làm bài tập đầy đủ nhé!"
            )
            
        # Thêm comment vào bài đầu tiên
        p1 = Post.objects.filter(class_room=c1).first()
        if p1:
            for u in users[1:4]:
                Comment.objects.get_or_create(post=p1, user=u, content="Dạ em hiểu rồi ạ thầy. Cảm ơn thầy!")
    print("Created 5 posts and comments.")

if __name__ == "__main__":
    seed_data()
    print("Seed complete!")
