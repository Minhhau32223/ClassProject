import { useState, useEffect, useRef } from 'react';
import Webcam from 'react-webcam';
import { postService } from '../../data/services/post.service';
import classService from '../../data/services/class.service';
import attendanceService from '../../data/services/attendance.service';
import {vi} from 'date-fns/locale';
import { formatDistanceToNow } from 'date-fns';
import Modal from '../../shared/components/Modal';

// Component hiển thị 1 bài viết + bình luận
function PostItem({ post, classId }) {
    const [expanded, setExpanded] = useState(false);
    const [comments, setComments] = useState(post.comments || []);
    const [comment, setComment] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [documents, setDocuments] = useState(post.documents || []);
    const [loadingDocs, setLoadingDocs] = useState(false);

    // Load documents when component mounts
    useEffect(() => {
        if (documents.length === 0 && !loadingDocs) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setLoadingDocs(true);
            postService.getDocuments(classId, post.id)
                .then(r => setDocuments(r.data))
                .catch(() => setDocuments([]))
                .finally(() => setLoadingDocs(false));
        }
    }, []);

    const submitComment = async (e) => {
        e.preventDefault();
        if (!comment.trim()) return;
        setSubmitting(true);
        try {
            const res = await postService.addComment(classId, post.id, { content: comment });
            setComments(prev => [...prev, res.data]);
            setComment('');
        } catch (e) {
            console.error(e);
        }
        setSubmitting(false);
    };

    return (
        <div className="post-card">
            <div className="post-meta">
                <strong>{post.author_name}</strong> · <span style={{ color: '#64748b', marginLeft: 4 }}>
                {formatDistanceToNow(new Date(post.created_at), { addSuffix: true, locale: vi })}
            </span>
            </div>
            <div className="post-content">{post.content}</div>
            {/* Hiển thị documents if have any */}
            {documents && documents.length > 0 && (
                <div>
                    {documents.map(doc => (
                        <div key={doc.id} style={{ 
                            marginBottom: 15, 
                            padding: '10px 14px', 
                            background: '#f8fafc', 
                            borderRadius: 8, 
                            border: '1px solid #e2e8f0',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10
                        }}>
                            <span style={{ fontSize: 18 }}>📄</span>
                            <a 
                                href={doc.file_url || doc.file_path} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                style={{ 
                                    textDecoration: 'none', 
                                    color: '#2563eb', 
                                    fontSize: 13, 
                                    fontWeight: 600,
                                    wordBreak: 'break-all' 
                                }}
                            >
                                {doc.file_name}
                            </a>
                        </div>
                    ))}
                </div>
            )}
            <div className="post-actions">
                <button
                    style={{ background: '#f1f5f9', border: 'none', borderRadius: 6, padding: '6px 12px', cursor: 'pointer', color: '#64748b', fontSize: 13 }}
                    onClick={() => setExpanded(!expanded)}
                >
                    💬 {comments.length} bình luận
                </button>
            </div>
            {expanded && (
                <>
                    <div className="comment-list">
                        {comments.length === 0 && <p style={{ color: '#94a3b8', fontSize: 13 }}>Chưa có bình luận.</p>}
                        {comments.map(c => (
                            <div className="comment-item" key={c.id}>
                                <span className="comment-user">{c.user_name}: </span>{c.content}
                                <small style={{ color: '#94a3b8', fontSize: 11, marginLeft: 10 }}>
                                    {formatDistanceToNow(new Date(c.created_at), { addSuffix: true, locale: vi })}
                                </small>
                            </div>
                        ))}
                    </div>
                    <form onSubmit={submitComment} style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                        <input
                            value={comment}
                            onChange={e => setComment(e.target.value)}
                            placeholder="Viết bình luận..."
                            style={{ flex: 1, padding: '7px 12px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13 }}
                        />
                        <button className="btn-sm btn-filled" type="submit" disabled={submitting}>Gửi</button>
                    </form>
                </>
            )}
        </div>
    );
}

// Component tab thống kê điểm danh
function StatsTab({ classId }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        attendanceService.getStats(classId)
            .then(res => setStats(res.data))
            .catch(() => setStats(null))
            .finally(() => setLoading(false));
    }, [classId]);

    if (loading) return <div className="loading">Đang tải thống kê...</div>;
    if (!stats) return <div className="card" style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>Không có dữ liệu hoặc bạn chưa đăng ký khuôn mặt.</div>;

    return (
        <div className="card">
            <p style={{ marginBottom: 16 }}><strong>Tổng số buổi học:</strong> {stats.class_sessions}</p>
            {stats.role === 'teacher' ? (
                <table>
                    <thead>
                        <tr><th>Sinh viên</th><th>Có mặt</th><th>Vắng</th><th>Tỷ lệ</th></tr>
                    </thead>
                    <tbody>
                        {stats.stats?.map((s, i) => (
                            <tr key={i}>
                                <td><strong>{s.student_name}</strong></td>
                                <td><span className="badge badge-green">{s.present_count}</span></td>
                                <td><span className="badge badge-gray">{s.absent_count}</span></td>
                                <td><strong>{s.attendance_rate}</strong></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    {[
                        { label: 'Buổi có mặt', value: stats.present_count, color: '#22c55e', bg: '#f0fdf4' },
                        { label: 'Buổi vắng', value: stats.absent_count, color: '#f97316', bg: '#fff7ed' },
                        { label: 'Tỷ lệ đi học', value: stats.attendance_rate, color: '#3B5BDB', bg: '#eff2ff' },
                    ].map(item => (
                        <div key={item.label} className="card" style={{ flex: 1, textAlign: 'center', background: item.bg }}>
                            <div style={{ fontSize: 26, fontWeight: 700, color: item.color }}>{item.value}</div>
                            <div style={{ color: '#64748b', fontSize: 13 }}>{item.label}</div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// Trang chi tiết lớp học
export default function ClassDetailPage({ cls, onBack, username }) {
    const [tab, setTab] = useState('posts');
    const [posts, setPosts] = useState([]);
    const [members, setMembers] = useState([]);
    const [loadingTab, setLoadingTab] = useState(false);
    const [newPost, setNewPost] = useState('');
    const [posting, setPosting] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null); //Luu filw
    const [needFaceReg, setNeedFaceReg] = useState(false);
    const [capturing, setCapturing] = useState(false);
    const webcamRef = useRef(null);
    
    // UI Modal Đăng ký KM
    const [showFaceModal, setShowFaceModal] = useState(false);
    const [regStep, setRegStep] = useState(1);
    const [faces, setFaces] = useState({ front: null, left: null, right: null });
    const [notice, setNotice] = useState(null);

    // === STATE ĐIỂM DANH ===
    const [activeSessions, setActiveSessions] = useState([]);
    const [allSessions, setAllSessions] = useState([]);
    const [sessionMinutes, setSessionMinutes] = useState(15); // Số phút điểm danh
    const [creatingSession, setCreatingSession] = useState(false);
    const [showCheckInModal, setShowCheckInModal] = useState(false);
    const [checkInSession, setCheckInSession] = useState(null); // Phiên đang check-in
    const [scanStatus, setScanStatus] = useState('idle'); // idle | scanning | success | error
    const [scanMessage, setScanMessage] = useState('');
    const [checkInChallenge, setCheckInChallenge] = useState(null);
    const [challengeStepIndex, setChallengeStepIndex] = useState(0);
    const [capturedFrames, setCapturedFrames] = useState([]);
    const scanIntervalRef = useRef(null);
    const scanStartupTimeoutRef = useRef(null);
    const checkInWebcamRef = useRef(null);

    const isCreator = cls.creator?.username === username || cls.role === 'Người tạo';

    useEffect(() => {
        setLoadingTab(true);
        if (tab === 'posts') {
            postService.list(cls.id)
                .then(r => { setPosts(r.data); setNeedFaceReg(false); })
                .catch((err) => {
                    if (err.response?.status === 403) setNeedFaceReg(true);
                })
                .finally(() => setLoadingTab(false));
        } else if (tab === 'members') {
            classService.getMembers(cls.id).then(r => setMembers(r.data)).catch(() => { }).finally(() => setLoadingTab(false));
        } else if (tab === 'attendance') {
            Promise.all([
                attendanceService.getActiveSessions(cls.id),
                attendanceService.getSessions(cls.id)
            ])
            .then(([activeRes, allRes]) => {
                setActiveSessions(activeRes.data);
                setAllSessions(allRes.data);
            })
            .catch(err => console.error('Load attendance failed:', err))
            .finally(() => setLoadingTab(false));
        } else {
            setLoadingTab(false);
        }
    }, [tab]);

    useEffect(() => () => stopAutoScan(), []);

    const showNotice = (type, title, message, options = {}) => {
        if (options.closeFaceModal) {
            handleCloseFaceModal();
        }

        if (options.closeCheckInModal) {
            handleCloseCheckInModal();
        }

        setNotice({ type, title, message });
    };

    const buildFriendlyFaceMessage = (payload, fallbackMessage) => {
        const rawError = payload?.error || '';
        const meta = payload?.meta || {};
        const detectedPose = payload?.detected_pose;
        const expectedPose = payload?.expected_pose;

        if (expectedPose && detectedPose) {
            const poseMap = {
                front: 'nhìn thẳng',
                left: 'quay mặt sang trái',
                right: 'quay mặt sang phải',
                unknown: 'chưa xác định',
            };
            return `Bạn cần ${poseMap[expectedPose] || expectedPose}, nhưng hệ thống đang nhận là ${poseMap[detectedPose] || detectedPose}. Hãy giữ đầu ổn định thêm một chút rồi thử lại.`;
        }

        if (rawError.includes('mờ') || (meta.laplacian_variance !== undefined && meta.laplacian_variance < 20)) {
            return 'Ảnh đang bị mờ. Hãy giữ điện thoại hoặc laptop đứng yên khoảng 1-2 giây và đưa mặt gần camera hơn.';
        }

        if (rawError.includes('tối') || (meta.brightness_mean !== undefined && meta.brightness_mean < 55)) {
            return 'Ảnh đang hơi tối. Hãy xoay ra chỗ sáng hơn hoặc tăng đèn trước mặt rồi thử lại.';
        }

        if (rawError.includes('cháy')) {
            return 'Ảnh đang bị chói sáng. Hãy tránh đèn rọi trực tiếp vào mặt hoặc đổi góc ngồi.';
        }

        if (rawError.includes('quá nhỏ') || rawError.includes('diện tích')) {
            return 'Khuôn mặt đang ở quá xa camera. Hãy tiến gần thêm một chút để mặt nằm gọn trong khung tròn.';
        }

        if (rawError.includes('không phát hiện') || rawError.includes('khuôn mặt')) {
            return 'Hệ thống chưa thấy rõ khuôn mặt. Hãy đưa mặt vào giữa khung, nhìn thẳng và giữ yên một chút.';
        }

        if (rawError.includes('không khớp với dữ liệu đã đăng ký') || rawError.includes('Khuôn mặt không khớp')) {
            return 'Khuôn mặt hiện tại không khớp với dữ liệu đã đăng ký của tài khoản này.';
        }

        return fallbackMessage || rawError || 'Hệ thống chưa nhận diện ổn định. Hãy giữ mặt rõ hơn và thử lại.';
    };

    const buildFriendlyRuntimeMessage = (payload, fallbackMessage) => {
        const rawError = payload?.error || '';
        const meta = payload?.meta || {};

        if (
            rawError.toLowerCase().includes('ảnh giả')
            || rawError.toLowerCase().includes('không phải khuôn mặt thật')
            || meta.anti_spoof_label === 'fake'
        ) {
            return 'Hệ thống phát hiện đây không phải khuôn mặt thật trực tiếp trước camera. Hãy dùng khuôn mặt thật của bạn và không dùng ảnh, video hoặc màn hình khác.';
        }

        return buildFriendlyFaceMessage(payload, fallbackMessage);
    };

    const closeNotice = () => setNotice(null);

    const resetFaceRegistrationState = () => {
        setCapturing(false);
        setRegStep(1);
        setFaces({ front: null, left: null, right: null });
    };

    const handleCloseFaceModal = () => {
        resetFaceRegistrationState();
        setShowFaceModal(false);
    };

    const handlePostSubmit = async (e) => {
        e.preventDefault();
        if (!newPost.trim() && !selectedFile) return;
        setPosting(true);
        try {
            // Step 1: Create the post with just content
            const r = await postService.create(cls.id, { content: newPost });
            
            // Step 2: If file selected, upload it as a document
            let uploadedDoc = null;
            if (selectedFile && r.data.id) {
                const docFormData = new FormData();
                docFormData.append('file_name', selectedFile.name);
                docFormData.append('file', selectedFile);
                
                try {
                    const docRes = await postService.uploadDocument(cls.id, r.data.id, docFormData);
                    uploadedDoc = docRes.data;
                } catch (docErr) {
                    console.warn('Document upload failed, but post was created:', docErr);
                }
            }
            
            // Add the new post to the list with empty documents array
            setPosts(prev => [{ ...r.data, documents: uploadedDoc ? [uploadedDoc] : [] }, ...prev]);
            setNewPost('');
            setSelectedFile(null);
        } catch (e) { 
            console.error(e);
        }
        setPosting(false);
    };

    const instructions = {
        1: "Nhìn thẳng trực diện vào Camera",
        2: "Từ từ xoay nhẹ mặt sang TRÁI",
        3: "Từ từ xoay nhẹ mặt sang PHẢI"
    };

    const challengeInstructions = {
        front: 'Nhìn thẳng vào camera',
        left: 'Xoay nhẹ đầu sang trái',
        right: 'Xoay nhẹ đầu sang phải',
    };
    const CHECKIN_CAMERA_STARTUP_MS = 2200;
    const CHECKIN_STEP_CAPTURE_DELAY_MS = 2600;
    const cameraShellStyle = {
        width: '100%',
        maxWidth: 640,
        aspectRatio: '4/3',
        margin: '0 auto 20px',
        background: 'radial-gradient(circle at top, #1e293b 0%, #020617 100%)',
        borderRadius: 20,
        overflow: 'hidden',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    };
    const circleViewportStyle = {
        width: '72%',
        maxWidth: 340,
        aspectRatio: '1 / 1',
        borderRadius: '50%',
        overflow: 'hidden',
        position: 'relative',
        background: '#020617',
        boxShadow: '0 0 0 9999px rgba(2, 6, 23, 0.82), 0 0 0 6px rgba(255,255,255,0.18)',
    };
    const webcamCircleStyle = {
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        transform: 'scaleX(-1)',
    };

    const handleCaptureFace = async () => {
        if (!webcamRef.current) {
            showNotice('error', 'Không mở được camera', 'Camera đăng ký khuôn mặt chưa sẵn sàng. Vui lòng thử mở lại.', { closeFaceModal: true });
            return;
        }

        const imageSrc = webcamRef.current.getScreenshot();
        if (!imageSrc) {
            showNotice('error', 'Chưa nhận được ảnh khuôn mặt', 'Hệ thống chưa chụp được ảnh từ camera. Hãy cho phép camera và đưa mặt vào khung rồi thử lại.', { closeFaceModal: true });
            return;
        }

        try {
            const res = await fetch(imageSrc);
            const blob = await res.blob();
            const validationFormData = new FormData();
            validationFormData.append('image', blob, `face-step-${regStep}.jpg`);

            await classService.validateFaceImage(cls.id, validationFormData);

            if (regStep === 1) setFaces(p => ({ ...p, front: blob }));
            if (regStep === 2) setFaces(p => ({ ...p, left: blob }));
            if (regStep === 3) setFaces(p => ({ ...p, right: blob }));

            if (regStep < 3) {
                setRegStep(regStep + 1);
                return;
            }

            submitFaceRegistration({ ...faces, right: blob });
        } catch (e) {
            showNotice(
                'error',
                'Ảnh chụp chưa hợp lệ',
                buildFriendlyRuntimeMessage(e.response?.data, 'Ảnh từ camera không hợp lệ hoặc không thấy khuôn mặt. Vui lòng chụp lại.'),
                { closeFaceModal: true }
            );
        }
    };

    const submitFaceRegistration = async (finalFaces) => {
        if (!finalFaces.front || !finalFaces.left || !finalFaces.right) {
            showNotice('error', 'Thiếu ảnh đăng ký', 'Bạn cần chụp đủ 3 góc khuôn mặt trước khi gửi đăng ký.', { closeFaceModal: true });
            return;
        }

        setCapturing(true);
        try {
            const formData = new FormData();
            formData.append('image_front', finalFaces.front, 'front.jpg');
            formData.append('image_left', finalFaces.left, 'left.jpg');
            formData.append('image_right', finalFaces.right, 'right.jpg');
            
            await classService.registerFace(cls.id, formData);
            handleCloseFaceModal();
            setNeedFaceReg(false);
            showNotice('success', 'Đăng ký thành công', 'Khuôn mặt 3 góc độ đã được xác minh thành công.');
            postService.list(cls.id).then(r => setPosts(r.data)); // reload list
        } catch(e) {
            const errorMessage = buildFriendlyRuntimeMessage(e.response?.data, 'Lỗi đăng ký khuôn mặt.');
            showNotice('error', 'Đăng ký khuôn mặt thất bại', errorMessage, { closeFaceModal: true });
            // Reset cho người dùng chụp lại
            resetFaceRegistrationState();
        }
        setCapturing(false);
    };

    const handleCreateSession = async () => {
        if (!sessionMinutes || sessionMinutes < 1) return;
        setCreatingSession(true);
        try {
            const now = new Date();
            const end = new Date(now.getTime() + sessionMinutes * 60 * 1000);
            // Format ISO 8601 để gửi lên Django
            await attendanceService.createSession(cls.id, {
                start_time: now.toISOString(),
                end_time: end.toISOString()
            });
            // Reload sau khi tạo
            const [activeRes, allRes] = await Promise.all([
                attendanceService.getActiveSessions(cls.id),
                attendanceService.getSessions(cls.id)
            ]);
            setActiveSessions(activeRes.data);
            setAllSessions(allRes.data);
            showNotice('success', 'Tạo phiên điểm danh thành công', `Đã mở phiên điểm danh ${sessionMinutes} phút.`);
        } catch (e) {
            showNotice('error', 'Không tạo được phiên điểm danh', e.response?.data?.error || 'Lỗi tạo phiên điểm danh.');
        }
        setCreatingSession(false);
    };

    // Bắt đầu chu kỳ Auto-Scan khuôn mặt (cứ 2.5s gửi 1 tấm lên AI)
    const startAutoScan = (session) => {
        setCheckInSession(session);
        setShowCheckInModal(true);
        setScanStatus('scanning');
        setScanMessage('Đang khởi tạo thử thách liveness...');
        setCheckInChallenge(null);
        setChallengeStepIndex(0);
        setCapturedFrames([]);

        attendanceService.getCheckInChallenge(cls.id, session.id)
            .then((response) => {
                const challenge = response.data;
                setCheckInChallenge(challenge);
                setScanMessage('Đang khởi động camera...');

                scanStartupTimeoutRef.current = setTimeout(() => {
                    if (!checkInWebcamRef.current) {
                        stopAutoScan();
                        setScanStatus('error');
                        setScanMessage('Camera điểm danh chưa sẵn sàng. Vui lòng mở lại và thử lại.');
                        showNotice('error', 'Không mở được camera điểm danh', 'Camera điểm danh chưa sẵn sàng. Vui lòng thử lại.', { closeCheckInModal: true });
                        return;
                    }

                    runCheckInSequence(session, challenge, 0, []);
                }, CHECKIN_CAMERA_STARTUP_MS);
            })
            .catch((err) => {
                const errMsg = buildFriendlyRuntimeMessage(err.response?.data, 'Không lấy được thử thách điểm danh.');
                showNotice('error', 'Không thể bắt đầu điểm danh', errMsg, { closeCheckInModal: true });
            });
    };

    const runCheckInSequence = (session, challenge, stepIndex, framesSoFar) => {
        const expectedPose = challenge.steps?.[stepIndex];
        if (!expectedPose) {
            submitCheckInSequence(session, challenge, framesSoFar);
            return;
        }

        setChallengeStepIndex(stepIndex);
        setCapturedFrames(framesSoFar);
        setScanMessage(`Bước ${stepIndex + 1}/${challenge.steps.length}: ${challengeInstructions[expectedPose] || 'Làm theo hướng dẫn trên màn hình'}...`);

        scanIntervalRef.current = setTimeout(async () => {
            if (!checkInWebcamRef.current) {
                showNotice('error', 'Camera đã bị ngắt', 'Camera điểm danh không còn sẵn sàng. Vui lòng mở lại và thử lại.', { closeCheckInModal: true });
                return;
            }

            const imageSrc = checkInWebcamRef.current.getScreenshot();
            if (!imageSrc) {
                showNotice('error', 'Chưa nhận được ảnh khuôn mặt', 'Hệ thống chưa lấy được ảnh từ camera. Vui lòng mở lại camera và thử lại.', { closeCheckInModal: true });
                return;
            }

            try {
                const res = await fetch(imageSrc);
                const blob = await res.blob();
                const nextFrames = [...framesSoFar, blob];
                runCheckInSequence(session, challenge, stepIndex + 1, nextFrames);
            } catch (e) {
                showNotice('error', 'Không xử lý được ảnh camera', 'Ảnh từ camera không hợp lệ. Vui lòng thử lại.', { closeCheckInModal: true });
            }
        }, CHECKIN_STEP_CAPTURE_DELAY_MS);
    };

    const submitCheckInSequence = async (session, challenge, frames) => {
        try {
            setCapturedFrames(frames);
            setScanMessage(`Đang gửi ${frames.length} frame lên hệ thống để xác minh...`);

            const formData = new FormData();
            formData.append('challenge_token', challenge.challenge_token);
            frames.forEach((frame, index) => {
                formData.append('checkin_images', frame, `checkin-${index + 1}.jpg`);
            });

            const result = await attendanceService.checkIn(cls.id, session.id, formData);
            stopAutoScan();
            setScanStatus('success');
            if (result.data?.already_checked) {
                setScanMessage('Đã ghi nhận điểm danh trước đó.');
            } else {
                setScanMessage(result.data?.message || 'Điểm danh thành công!');
            }
        } catch (err) {
            const httpStatus = err.response?.status;
            const errMsg = err.response?.data?.error || '';

            if (httpStatus === 400 && errMsg.includes('không khả dụng')) {
                showNotice('error', 'Phiên điểm danh đã đóng', 'Phiên điểm danh hiện không còn khả dụng.', { closeCheckInModal: true });
            } else if (httpStatus === 403) {
                showNotice('error', 'Không thể điểm danh', buildFriendlyRuntimeMessage(err.response?.data, errMsg || 'Không có quyền điểm danh.'), { closeCheckInModal: true });
            } else if (httpStatus === 404) {
                showNotice('error', 'Chưa đăng ký khuôn mặt', 'Bạn chưa có dữ liệu khuôn mặt để điểm danh. Hãy đăng ký khuôn mặt trước.', { closeCheckInModal: true });
            } else if (httpStatus === 503) {
                showNotice('error', 'AI backend chưa sẵn sàng', buildFriendlyRuntimeMessage(err.response?.data, errMsg || 'Hệ thống nhận diện khuôn mặt chưa sẵn sàng.'), { closeCheckInModal: true });
            } else if (httpStatus === 400) {
                showNotice('error', 'Điểm danh thất bại', buildFriendlyRuntimeMessage(err.response?.data, errMsg || 'Chuỗi ảnh điểm danh chưa hợp lệ.'), { closeCheckInModal: true });
            } else {
                showNotice('error', 'Lỗi hệ thống', buildFriendlyRuntimeMessage(err.response?.data, errMsg || 'Có lỗi xảy ra trong lúc điểm danh. Vui lòng thử lại sau.'), { closeCheckInModal: true });
            }
        }
    };

    const stopAutoScan = () => {
        if (scanStartupTimeoutRef.current) {
            clearTimeout(scanStartupTimeoutRef.current);
            scanStartupTimeoutRef.current = null;
        }
        if (scanIntervalRef.current) {
            clearTimeout(scanIntervalRef.current);
            scanIntervalRef.current = null;
        }
    };

    // Dọn dẹp interval khi đóng modal
    const handleCloseCheckInModal = () => {
        stopAutoScan();
        setShowCheckInModal(false);
        setCheckInSession(null);
        setCheckInChallenge(null);
        setChallengeStepIndex(0);
        setCapturedFrames([]);
        setScanStatus('idle');
        setScanMessage('');
    };

    const tabStyle = (t) => ({
        flex: 1,
        textAlign: 'center',
        padding: '10px 16px',
        border: 'none',
        borderRadius: 999,
        background: tab === t ? '#ffffff' : 'transparent',
        color: '#334155',
        fontWeight: 600,
        cursor: 'pointer',
        fontSize: 14,
        boxShadow: tab === t ? '0 2px 6px rgba(0,0,0,0.25)' : 'none',
        transition: '0.2s'
    });

    return (
        <div>
            <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#000000', fontSize: 16,fontWeight: 700 , cursor: 'pointer', marginBottom: 12 }}>
                ←     Quay lại
            </button>
        {/* Header lớp học */}
        <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            padding: '20px 24px',
            background: '#ffffff',
            borderRadius: 16,
            boxShadow: '0 6px 20px rgba(0,0,0,0.06)',
            marginBottom: 20
        }}>
            {/* LEFT */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                
                {/* Tên lớp + role */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>
                        {cls.class_name}
                    </h1>

                <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    background: isCreator ? '#e0edff' : '#dcfce7',
                    color: isCreator ? '#1d4ed8' : '#16a34a',
                    fontSize: 12,
                    padding: '5px 12px',
                    borderRadius: 999,
                    fontWeight: 600
                }}>
                    {isCreator ? 'Người tạo' : 'Thành viên'}
                </span>

                </div>

                {/* Mã lớp + số thành viên */}
                <div style={{ display: 'flex', gap: 16, fontSize: 15 }}>
                    <span>
                        Mã lớp: 
                        <span style={{
                            background: '#f1f5f9',
                            padding: '2px 8px',
                            borderRadius: 6,
                            marginLeft: 6,
                            fontWeight: 600
                        }}>
                            {cls.class_code}
                        </span>
                    </span>

                    <span style={{ color: '#64748b' }}>
                        {cls.member_count || 1} thành viên
                    </span>
                </div>
            </div>
        </div>

            {/* Tabs */}
            <div style={{display: 'inline-flex',background: '#d6dce3', borderRadius: 12,padding: 4, marginBottom: 20,  width: '100%' }}>
                <button style={tabStyle('posts')} onClick={() => setTab('posts')}>📋 Bài viết</button>
                <button style={tabStyle('members')} onClick={() => setTab('members')}>👥 Thành viên</button>
                <button style={tabStyle('attendance')} onClick={() => setTab('attendance')}>✅ Điểm danh</button>
                <button style={tabStyle('stats')} onClick={() => setTab('stats')}>📊 Thống kê</button>
            </div>

            {/* Tab Bài viết */}
            {tab === 'posts' && (
                <>
                    {needFaceReg ? (
                        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                            <div style={{ fontSize: 40, marginBottom: 16 }}>🔒</div>
                            <h3 style={{ marginBottom: 12 }}>Yêu cầu Face Registration</h3>
                            <p style={{ color: '#64748b', marginBottom: 20 }}>Bạn bắt buộc phải xác minh nhân dạng 3 góc khuôn mặt trước khi truy cập nội dung lớp học.</p>
                            
                            <button className="btn btn-filled" onClick={() => {
                                setShowFaceModal(true);
                                resetFaceRegistrationState();
                            }} style={{ maxWidth: 300, margin: '0 auto', fontSize: 16 }}>
                                📸 Mở Camera Xác Thực Ngay
                            </button>
                        </div>
                    ) : (
                        <>
                            {isCreator && (
                                <form onSubmit={handlePostSubmit} style={{ marginBottom: 20 }}>
                                    <div className="card" style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
                                        <textarea
                                            value={newPost}
                                            onChange={e => setNewPost(e.target.value)}
                                            placeholder="Đăng thông báo cho lớp học..."
                                            rows={3}
                                            style={{ flex: 1, padding: '10px 14px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, resize: 'vertical' }}
                                        />
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        {/* Nút tải lên tài liệu giả lập bằng nhãn label */}
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                                <label style={{ 
                                                    padding: '8px 12px', 
                                                    background: '#f1f5f9', 
                                                    borderRadius: 6, 
                                                    cursor: 'pointer',
                                                    fontSize: 13,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 6,
                                                    color: '#475569',
                                                    border: '1px solid #e2e8f0'
                                                }}>
                                                    📁 {selectedFile ? 'Đổi file' : 'Đính kèm tài liệu'}
                                                    <input 
                                                        type="file" 
                                                        style={{ display: 'none' }} 
                                                        onChange={(e) => setSelectedFile(e.target.files[0])} 
                                                    />
                                                </label>
                                                 <button className="btn-sm btn-filled" type="submit" disabled={posting}>
                                                    {posting ? 'Đang đăng' : 'Đăng bài'}
                                                </button>
                                                
                                                {selectedFile && (
                                                    <span style={{ fontSize: 12, color: '#22c55e', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                        ✅ {selectedFile.name}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </form>
                            )}
                            {loadingTab ? (
                                <div className="loading">Đang tải bài viết...</div>
                            ) : posts.length === 0 ? (
                                <div className="card" style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>Chưa có bài viết nào.</div>
                            ) : (
                                posts.map(p => <PostItem key={p.id} post={p} classId={cls.id} />)
                            )}
                        </>
                    )}
                </>
            )}

            {/* Tab Thành viên */}
            {tab === 'members' && (
                <div className="card">
                    {loadingTab ? (
                        <div className="loading">Đang tải...</div>
                    ) : (
                        <>
                        <p style={{ marginBottom: 12 }}>
                            <strong>Tổng thành viên:</strong> {members.length}
                        </p>
                        
                        <table>
                            <thead>
                                <tr><th>Họ tên</th><th>Username</th><th>Khuôn mặt</th><th>Ngày tham gia</th></tr>
                            </thead>
                            <tbody>
                                {members.map(m => (
                                    <tr key={m.id}>
                                        <td><strong>{m.user.full_name}</strong></td>
                                        <td style={{ color: '#64748b' }}>@{m.user.username}</td>
                                        <td>
                                            <span
                                                style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    gap: 6,
                                                    padding: '4px 10px',
                                                    borderRadius: 999,
                                                    fontSize: 12,
                                                    fontWeight: 600,
                                                    background: m.face_registered ? '#f0fdf4' : '#fef2f2',
                                                    color: m.face_registered ? '#16a34a' : '#dc2626'
                                                }}
                                            >
                                                {m.face_registered ? '✔ Đã xác thực' : '✖ Chưa xác thực'}
                                            </span>
                                        </td>
                                        <td style={{ color: '#94a3b8' }}>{new Date(m.joined_at).toLocaleDateString('vi-VN')}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        </>
                    )}
                </div>
            )}

            {/* Tab Thống kê */}
            {tab === 'stats' && <StatsTab classId={cls.id} />}

            {/* === TAB ĐIỂM DANH === */}
            {tab === 'attendance' && (
                <div>
                    {loadingTab ? (
                        <div className="loading">Đang tải...</div>
                    ) : isCreator ? (
                        /* Góc nhìn GIÁO VIÊN */
                        <div>
                            {/* Form tạo phiên mới */}
                            <div className="card" style={{ marginBottom: 20 }}>
                                <h3 style={{ marginBottom: 16, fontSize: 16 }}>🕐 Tạo phiên điểm danh mới</h3>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <label style={{ fontSize: 14, fontWeight: 600, color: '#475569' }}>Thời gian mở cửa:</label>
                                        <input
                                            type="number"
                                            min={1}
                                            max={180}
                                            value={sessionMinutes}
                                            onChange={e => setSessionMinutes(Number(e.target.value))}
                                            style={{
                                                width: 70,
                                                padding: '8px 10px',
                                                border: '1.5px solid #e2e8f0',
                                                borderRadius: 8,
                                                fontSize: 14,
                                                fontWeight: 700,
                                                textAlign: 'center'
                                            }}
                                        />
                                        <span style={{ fontSize: 14, color: '#64748b' }}>phút</span>
                                    </div>
                                    <button
                                        className="btn-sm btn-filled"
                                        onClick={handleCreateSession}
                                        disabled={creatingSession}
                                        style={{ padding: '9px 20px', fontSize: 14 }}
                                    >
                                        {creatingSession ? 'Đang tạo...' : '▶ Mở phiên điểm danh'}
                                    </button>
                                </div>
                                {activeSessions.length > 0 && (
                                    <div style={{ marginTop: 12, padding: '10px 14px', background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0' }}>
                                        <span className="session-badge-active">🟢 Có {activeSessions.length} phiên đang mở</span>
                                    </div>
                                )}
                            </div>

                            {/* Lịch sử phiên */}
                            <div className="card">
                                <h3 style={{ marginBottom: 14, fontSize: 16 }}>📋 Lịch sử phiên điểm danh</h3>
                                {allSessions.length === 0 ? (
                                    <div style={{ textAlign: 'center', color: '#94a3b8', padding: '20px 0' }}>Chưa có phiên nào được tạo.</div>
                                ) : (
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Thời gian bắt đầu</th>
                                                <th>Thời gian kết thúc</th>
                                                <th>Trạng thái</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {allSessions.map(s => {
                                                const now = new Date();
                                                const isActive = new Date(s.start_time) <= now && new Date(s.end_time) >= now;
                                                return (
                                                    <tr key={s.id}>
                                                        <td>{new Date(s.start_time).toLocaleString('vi-VN')}</td>
                                                        <td>{new Date(s.end_time).toLocaleString('vi-VN')}</td>
                                                        <td>
                                                            {isActive
                                                                ? <span className="session-badge-active">🟢 Đang mở</span>
                                                                : <span className="session-badge-closed">■ Đã đóng</span>
                                                            }
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        </div>
                    ) : (
                        /* Góc nhìn HỌC VIÊN */
                        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                            {activeSessions.length === 0 ? (
                                <>
                                    <div style={{ fontSize: 48, marginBottom: 12 }}>⏳</div>
                                    <h3 style={{ marginBottom: 8 }}>Chưa có phiên điểm danh</h3>
                                    <p style={{ color: '#64748b' }}>Giáo viên chưa mở phiên điểm danh. Hãy chờ trong giờ học.</p>
                                </>
                            ) : (
                                <>
                                    <div style={{ fontSize: 48, marginBottom: 12 }}>✅</div>
                                    <h3 style={{ marginBottom: 8 }}>Phiên điểm danh đang mở!</h3>
                                    <p style={{ color: '#64748b', marginBottom: 8 }}>
                                        Kết thúc lúc: <strong>{new Date(activeSessions[0].end_time).toLocaleTimeString('vi-VN')}</strong>
                                    </p>
                                    <button
                                        className="btn btn-filled"
                                        style={{ maxWidth: 280, margin: '0 auto', fontSize: 16, padding: '12px 24px' }}
                                        onClick={() => startAutoScan(activeSessions[0])}
                                    >
                                        📷 Vào Điểm Danh Ngay
                                    </button>
                                </>
                            )}
                        </div>
                    )}
                </div>
            )}

            {notice && (
                <Modal title={notice.title} onClose={closeNotice}>
                    <div style={{ textAlign: 'center', padding: '8px 0 4px' }}>
                        <div style={{ fontSize: 56, marginBottom: 12 }}>
                            {notice.type === 'success' ? '✅' : '⚠️'}
                        </div>
                        <p style={{ color: '#64748b', marginBottom: 18, lineHeight: 1.6 }}>
                            {notice.message}
                        </p>
                        <button className="btn btn-filled" onClick={closeNotice} style={{ maxWidth: 180, margin: '0 auto' }}>
                            Đóng
                        </button>
                    </div>
                </Modal>
            )}

            {/* Popup Modal Camera */}
            {showFaceModal && (
                <Modal title="Xác minh Khuôn mặt 3D" onClose={handleCloseFaceModal}>
                    <div style={{ textAlign: 'center' }}>
                        <p style={{ fontSize: 18, fontWeight: 'bold', color: '#2563eb', marginBottom: 10 }}>
                            Bước {regStep}/3: {instructions[regStep]}
                        </p>
                        <div style={cameraShellStyle}>
                            <div style={circleViewportStyle}>
                                <Webcam
                                    audio={false}
                                    ref={webcamRef}
                                    screenshotFormat="image/jpeg"
                                    videoConstraints={{ facingMode: "user" }}
                                    style={webcamCircleStyle}
                                />
                            </div>
                            <div style={{
                                position: 'absolute',
                                bottom: 18,
                                left: '50%',
                                transform: 'translateX(-50%)',
                                background: 'rgba(15, 23, 42, 0.68)',
                                color: '#fff',
                                padding: '8px 14px',
                                borderRadius: 999,
                                fontSize: 13,
                                fontWeight: 600,
                                backdropFilter: 'blur(4px)'
                            }}>
                                Căn khuôn mặt vào giữa khung tròn
                            </div>
                        </div>
                        <button 
                            className="btn btn-filled" 
                            onClick={handleCaptureFace} 
                            disabled={capturing} 
                            style={{ fontSize: 16, padding: '10px 30px', maxWidth: 300, margin: '0 auto' }}
                        >
                            {capturing ? 'Đang phân tích AI...' : '📸 Chụp Góc Này'}
                        </button>
                        <button
                            className="btn-sm"
                            onClick={handleCloseFaceModal}
                            style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: '8px 20px', margin: '12px auto 0' }}
                        >
                            Đóng camera
                        </button>
                    </div>
                </Modal>
            )}
            {/* === POPUP MODAL AUTO-SCAN ĐIỂM DANH === */}
            {showCheckInModal && (
                <Modal
                    title="📷 Quét Khuôn Mặt Điểm Danh"
                    onClose={handleCloseCheckInModal}
                >
                    <div style={{ textAlign: 'center' }}>
                        {/* Thông tin phiên */}
                        {checkInSession && (
                            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 12 }}>
                                Kết thúc lúc: <strong>{new Date(checkInSession.end_time).toLocaleTimeString('vi-VN')}</strong>
                            </p>
                        )}

                        {scanStatus === 'scanning' && (
                            <>
                                {/* Indicator scanning */}
                                <div style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: 8,
                                    padding: '6px 16px',
                                    background: '#eff6ff',
                                    borderRadius: 999,
                                    marginBottom: 14,
                                    color: '#2563eb',
                                    fontSize: 13,
                                    fontWeight: 600,
                                    animation: 'scan-pulse 1.5s infinite'
                                }}>
                                    <span style={{ width: 8, height: 8, background: '#3b82f6', borderRadius: '50%', display: 'inline-block' }}></span>
                                    Đang quét AI...
                                </div>

                                {/* Camera Box */}
                                <div style={{ ...cameraShellStyle, maxWidth: 560, margin: '0 auto 16px', boxShadow: '0 0 0 4px rgba(59,130,246,0.14)' }}>
                                    <div style={{ ...circleViewportStyle, maxWidth: 320, boxShadow: '0 0 0 9999px rgba(2, 6, 23, 0.84), 0 0 0 6px rgba(59,130,246,0.28)' }}>
                                        <Webcam
                                            audio={false}
                                            ref={checkInWebcamRef}
                                            screenshotFormat="image/jpeg"
                                            videoConstraints={{ facingMode: "user" }}
                                            style={webcamCircleStyle}
                                        />
                                    </div>
                                </div>

                                <p style={{ color: '#64748b', fontSize: 13 }}>
                                    {checkInChallenge
                                        ? `Đã chụp ${capturedFrames.length}/${checkInChallenge.steps?.length || 5} frame. ${scanMessage}`
                                        : 'Hệ thống đang chuẩn bị thử thách điểm danh...'}
                                </p>
                                {checkInChallenge && (
                                    <div style={{ color: '#2563eb', fontSize: 13, fontWeight: 600, marginTop: 6 }}>
                                        Bước hiện tại: {challengeStepIndex + 1}/{checkInChallenge.steps.length} - {challengeInstructions[checkInChallenge.steps[challengeStepIndex]] || 'Làm theo hướng dẫn'}
                                    </div>
                                )}
                                <div style={{ color: '#64748b', fontSize: 12, marginTop: 8 }}>
                                    Chỉ cần đưa mặt vào giữa khung tròn, ngoại cảnh sẽ được bỏ qua.
                                </div>
                                <button
                                    className="btn-sm"
                                    style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: '8px 20px', margin: '12px auto 0' }}
                                    onClick={handleCloseCheckInModal}
                                >
                                    Tắt camera
                                </button>
                            </>
                        )}

                        {scanStatus === 'success' && (
                            <div style={{ padding: '20px 0' }}>
                                <div style={{ fontSize: 64, marginBottom: 16 }}>✅</div>
                                <h3 style={{ color: '#16a34a', marginBottom: 8, fontSize: 20 }}>Điểm Danh Thành Công!</h3>
                                <p style={{ color: '#64748b', marginBottom: 20 }}>{scanMessage}</p>
                                <button className="btn btn-filled" onClick={handleCloseCheckInModal} style={{ maxWidth: 200, margin: '0 auto' }}>
                                    Đóng
                                </button>
                            </div>
                        )}

                        {scanStatus === 'error' && (
                            <div style={{ padding: '20px 0' }}>
                                <div style={{ fontSize: 64, marginBottom: 16 }}>❌</div>
                                <h3 style={{ color: '#dc2626', marginBottom: 8, fontSize: 20 }}>Thất Bại</h3>
                                <p style={{ color: '#64748b', marginBottom: 20 }}>{scanMessage}</p>
                                <button className="btn-sm" style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: '8px 20px' }} onClick={handleCloseCheckInModal}>
                                    Đóng
                                </button>
                            </div>
                        )}
                    </div>
                </Modal>
            )}
        </div>
    );
}
