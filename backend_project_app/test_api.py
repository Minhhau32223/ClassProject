import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("--- 1. Testing /auth/register ---")
    teacher_data = {
        "username": "teacher1",
        "password": "password123",
        "email": "teacher1@example.com",
        "full_name": "Teacher One"
    }
    user_data = {
        "username": "student1",
        "password": "password123",
        "email": "student1@example.com",
        "full_name": "Student One"
    }
    
    r1 = requests.post(f"{BASE_URL}/auth/register/", json=teacher_data)
    print("Teacher Register:", r1.status_code, r1.text)
    
    r2 = requests.post(f"{BASE_URL}/auth/register/", json=user_data)
    print("Student Register:", r2.status_code, r2.text)

    print("\n--- 2. Testing /auth/login ---")
    print("Logging in Teacher...")
    lt = requests.post(f"{BASE_URL}/auth/login/", json={"username": "teacher1", "password": "password123"})
    print("Teacher Login:", lt.status_code)
    try:
        t_token = lt.json().get("access")
    except Exception:
        t_token = None
        print("Failed to get Teacher Token")

    print("Logging in Student...")
    ls = requests.post(f"{BASE_URL}/auth/login/", json={"username": "student1", "password": "password123"})
    print("Student Login:", ls.status_code)
    try:
        s_token = ls.json().get("access")
    except Exception:
        s_token = None
        print("Failed to get Student Token")

    t_headers = {"Authorization": f"Bearer {t_token}"}
    s_headers = {"Authorization": f"Bearer {s_token}"}

    class_code = None
    print("\n--- 3. Testing /classes/create ---")
    r3 = requests.post(f"{BASE_URL}/classes/create/", json={"class_name": "Math 101"}, headers=t_headers)
    print("Class Create:", r3.status_code, r3.text)
    if r3.status_code == 201:
        class_code = r3.json().get("class_code")
        print("Extracted Class Code:", class_code)

    print("\n--- 4. Testing /classes/join ---")
    if class_code:
        # Join as Student
        r4 = requests.post(f"{BASE_URL}/classes/join/", json={"class_code": class_code}, headers=s_headers)
        print("Class Join (Student):", r4.status_code, r4.text)

        # Join again as Student (Expect Error)
        r4_dup = requests.post(f"{BASE_URL}/classes/join/", json={"class_code": class_code}, headers=s_headers)
        print("Class Join Duplicate:", r4_dup.status_code, r4_dup.text)

        # Join as Teacher (Expect Error)
        r4_t = requests.post(f"{BASE_URL}/classes/join/", json={"class_code": class_code}, headers=t_headers)
        print("Class Join as Creator:", r4_t.status_code, r4_t.text)

    print("\n--- 5. Testing /classes/my ---")
    r5_t = requests.get(f"{BASE_URL}/classes/my/", headers=t_headers)
    print("Teacher My Classes:", r5_t.status_code, r5_t.text)

    r5_s = requests.get(f"{BASE_URL}/classes/my/", headers=s_headers)
    print("Student My Classes:", r5_s.status_code, r5_s.text)

    print("\n--- 6. Testing /classes/<id>/members ---")
    if class_code and r3.status_code == 201:
        class_id = r3.json().get("id")
        r6 = requests.get(f"{BASE_URL}/classes/{class_id}/members/", headers=t_headers)
        print("Class Members List (Before Face Reg):", r6.status_code, r6.text)

    print("\n--- 7. Testing /classes/<id>/register-face ---")
    if class_code and r3.status_code == 201:
        class_id = r3.json().get("id")
        
        # Thử xem bài viết trước khi đăng ký khuôn mặt (Mong đợi 403)
        r_posts_before = requests.get(f"{BASE_URL}/classes/{class_id}/posts/", headers=s_headers)
        print("MEMBER WITHOUT FACE TRYING TO VIEW POSTS:", r_posts_before.status_code, r_posts_before.text)

        # Tạo file ảnh giả lập (1x1 pixel màu đen chuẩn PNG)
        fake_png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # Test 1: Student registers face by uploading an image
        files = {'face_image': ('dummy.png', fake_png_bytes, 'image/png')}
        r7 = requests.post(f"{BASE_URL}/classes/{class_id}/register-face/", files=files, headers=s_headers)
        print("Face Registration (Student - Expect 500 if AI not installed):", r7.status_code)
        
        # Bằng cách mock vào Database, ta can thiệp cho phép user_id=2 (Student 1) 
        # có face_registered = True để tiếp tục chạy test
        import sqlite3
        import MySQLdb
        try:
            db_conn = MySQLdb.connect(host="127.0.0.1", user="root", passwd="", db="dacn_db")
            cursor = db_conn.cursor()
            cursor.execute("UPDATE apps_classmember SET face_registered = 1 WHERE class_room_id = %s", (class_id,))
            
            # Tao giã face registration data để pass được check in test (bước 3: so khớp vector)
            mock_vector = "[0.0, 0.0]"
            cursor.execute("INSERT INTO apps_faceregistration (embedding_vector, registered_at, class_member_id) VALUES (%s, NOW(), (SELECT id FROM apps_classmember WHERE class_room_id = %s AND user_id = 2 LIMIT 1))", (mock_vector, class_id))
            
            db_conn.commit()
            db_conn.close()
            print("Successfully mocked face_registered = True in MySQL for testing")
        except Exception as e:
            print("Failed to mock MySQL:", e)
        
        # Test 2: Teacher checks members again to see face_registered (might be false if registration failed)
        r8 = requests.get(f"{BASE_URL}/classes/{class_id}/members/", headers=t_headers)
        print("Class Members List (After Face Reg Run):", r8.status_code, r8.text)

    print("\n--- 8. Testing /classes/<id>/posts/ & comments ---")
    if class_code and r3.status_code == 201:
        class_id = r3.json().get("id")
        
        # Teacher tạo bài viết
        post_data = {"content": "Chào mừng các em đến với lớp Toán 101 bằng tiếng Việt!"}
        r9_p = requests.post(f"{BASE_URL}/classes/{class_id}/posts/", json=post_data, headers=t_headers)
        print("Teacher Creates Post:", r9_p.status_code, r9_p.text)
        
        post_id = None
        if r9_p.status_code == 201:
            post_id = r9_p.json().get("id")

        # Student xem bài viết (bây giờ đã đăng ký khuôn mặt nên hợp lệ 200)
        r9_g = requests.get(f"{BASE_URL}/classes/{class_id}/posts/", headers=s_headers)
        print("Student Views Timeline:", r9_g.status_code, r9_g.text)

        # Student bình luận vào bài viết
        if post_id:
            comment_data = {"content": "Em chào thầy ạ!"}
            r10_c = requests.post(f"{BASE_URL}/classes/{class_id}/posts/{post_id}/comments/", json=comment_data, headers=s_headers)
            print("Student Comments on Post:", r10_c.status_code, r10_c.text)


    print("\n--- 9. Testing /.../documents/ (Upload & View) ---")
    if class_code and post_id:
        # Teacher tải tài liệu lên (hợp lệ)
        doc_data = {
            "file_name": "Bai_tap_01.pdf",
            "file_path": "/var/media/uploads/bai_tap_01.pdf"
        }
        r11_up = requests.post(f"{BASE_URL}/classes/{class_id}/posts/{post_id}/documents/upload/", json=doc_data, headers=t_headers)
        print("Teacher Uploads Document:", r11_up.status_code, r11_up.text)

        # Student xem danh sách tài liệu
        r12_view = requests.get(f"{BASE_URL}/classes/{class_id}/posts/{post_id}/documents/", headers=s_headers)
        print("Student Views Documents:", r12_view.status_code, r12_view.text)

    print("\n--- 10. Testing /.../attendance/sessions/ (Create Session) ---")
    session_id = None
    if class_code:
        # Teacher tạo Phiên
        session_data = {
            "start_time": "2024-01-01T00:00:00Z", # Quá khứ để luôn Valid khi test
            "end_time": "2030-12-31T23:59:59Z"   # Tương lai xa
        }
        r13 = requests.post(f"{BASE_URL}/classes/{class_id}/attendance/sessions/", json=session_data, headers=t_headers)
        print("Teacher Creates Attendance Session:", r13.status_code, r13.text)
        if r13.status_code == 201:
            session_id = r13.json().get("id")

    print("\n--- 11. Testing /.../attendance/sessions/<id>/checkin/ ---")
    if session_id:
        # Gửi file dummy ảnh điểm danh
        fake_png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        files = {'checkin_image': ('checkin_dummy.png', fake_png_bytes, 'image/png')}
        
        r14 = requests.post(f"{BASE_URL}/classes/{class_id}/attendance/sessions/{session_id}/checkin/", files=files, headers=s_headers)
        print("Student Check-In (With Image - Expect 500 if AI not installed):", r14.status_code, r14.text)

    print("\n--- 12. Testing /.../attendance/stats/ ---")
    if class_code:
        # Teacher view stats
        r15_t = requests.get(f"{BASE_URL}/classes/{class_id}/attendance/stats/", headers=t_headers)
        print("Teacher Views Stats:", r15_t.status_code, r15_t.text)

        # Student view stats
        r15_s = requests.get(f"{BASE_URL}/classes/{class_id}/attendance/stats/", headers=s_headers)
        print("Student Views Stats:", r15_s.status_code, r15_s.text)

if __name__ == "__main__":
    test_api()
