// Chat application client script

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Socket.IO connection
    const socket = io({
        transports: ['websocket', 'polling']
    });

    // DOM Elements
    const chatMessagesContainer = document.getElementById('chatMessagesContainer');
    const chatMessages = document.getElementById('chatMessages');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const btnSend = document.getElementById('btnSend');

    // Radios & Target selector
    const sendTypeRadios = document.querySelectorAll('input[name="sendType"]');
    const receiverSelectWrapper = document.getElementById('receiverSelectWrapper');
    const receiverSelect = document.getElementById('receiverSelect');

    // Online users elements
    const onlineUsersList = document.getElementById('onlineUsersList');
    const onlineUserCount = document.getElementById('onlineUserCount');

    // Notice elements
    const noticeBanner = document.getElementById('noticeBanner');
    const noticeContent = document.getElementById('noticeContent');
    const noticeAuthor = document.getElementById('noticeAuthor');
    const noticeTime = document.getElementById('noticeTime');
    const btnDeleteNotice = document.getElementById('btnDeleteNotice');
    const btnClearChat = document.getElementById('btnClearChat');

    // File upload elements
    const fileInput = document.getElementById('fileInput');
    const btnAttachFile = document.getElementById('btnAttachFile');
    const attachedFilePreviewContainer = document.getElementById('attachedFilePreviewContainer');
    const attachedFileName = document.getElementById('attachedFileName');
    const attachedFileSize = document.getElementById('attachedFileSize');
    const attachedFileIcon = document.getElementById('attachedFileIcon');
    const btnRemoveAttachedFile = document.getElementById('btnRemoveAttachedFile');

    let selectedFile = null;

    // Nickname modal elements
    const newNicknameInput = document.getElementById('newNicknameInput');
    const btnSaveNickname = document.getElementById('btnSaveNickname');
    const currentNicknameSpan = document.getElementById('currentNicknameSpan');
    const nicknameModalElement = document.getElementById('nicknameModal');
    const nicknameModal = new bootstrap.Modal(nicknameModalElement);

    // Search modal elements
    const searchKeyword = document.getElementById('searchKeyword');
    const searchTypeFilter = document.getElementById('searchTypeFilter');
    const btnExecuteSearch = document.getElementById('btnExecuteSearch');
    const searchResultsList = document.getElementById('searchResultsList');
    const searchResultCount = document.getElementById('searchResultCount');

    // Duplicate Connection Modal
    const duplicateModalElement = document.getElementById('duplicateConnectionModal');
    const duplicateModal = new bootstrap.Modal(duplicateModalElement);

    // Screen sharing elements
    const btnToggleScreenShare = document.getElementById('btnToggleScreenShare');
    const screenShareSection = document.getElementById('screenShareSection');
    const screenSharerText = document.getElementById('screenSharerText');
    const screenShareVideo = document.getElementById('screenShareVideo');
    const screenShareLoading = document.getElementById('screenShareLoading');
    const btnFullscreenScreen = document.getElementById('btnFullscreenScreen');
    const btnStopSharingMyScreen = document.getElementById('btnStopSharingMyScreen');

    // Auto-scroll to bottom of messages
    function scrollToBottom() {
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }
    scrollToBottom();

    // Ensure disconnect on window close / unload
    window.addEventListener('beforeunload', () => {
        if (typeof stopMyScreenSharing === 'function') {
            stopMyScreenSharing();
        }
        socket.disconnect();
    });

    // 2. Handle Connection Rejection (IP already in use)
    function handleRejection(message) {
        document.getElementById('rejectionMessage').textContent = message || '이미 다른 창이나 탭에서 동일한 IP로 접속 중입니다.';
        messageInput.disabled = true;
        btnSend.disabled = true;
        duplicateModal.show();
        socket.disconnect();
    }

    socket.on('connection_rejected', (data) => {
        handleRejection(data.message);
    });

    socket.on('connect_error', (err) => {
        console.warn('Socket connect error:', err);
        handleRejection(err.message || '접속이 거부되었습니다. (동일 IP 중복 접속 제한)');
    });

    // 3. Radio buttons toggle receiver dropdown
    sendTypeRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            if (radio.value === 'dm') {
                receiverSelectWrapper.classList.remove('d-none');
                receiverSelect.focus();
            } else {
                receiverSelectWrapper.classList.add('d-none');
            }
        });
    });

    // 4. Update online users list and recipient dropdown
    socket.on('user_list_update', (users) => {
        renderUsersList(users);
        updateReceiverDropdown(users);
    });

    function renderUsersList(users) {
        onlineUserCount.textContent = `${users.length}명`;
        onlineUsersList.innerHTML = '';

        users.forEach(u => {
            const isMe = (u.ip === CURRENT_USER_IP);
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center px-2 py-2 border-0 rounded mb-1 bg-light user-item';
            li.setAttribute('data-ip', u.ip);

            li.innerHTML = `
                <div class="d-flex align-items-center text-truncate">
                    <i class="bi bi-circle-fill text-success me-2" style="font-size: 0.6rem;"></i>
                    <div class="text-truncate">
                        <div class="fw-semibold small text-truncate">${escapeHtml(u.nickname)}</div>
                        <small class="text-muted font-monospace" style="font-size: 0.75rem;">${escapeHtml(u.ip)}</small>
                    </div>
                </div>
                <div>
                    ${isMe 
                        ? '<span class="badge bg-primary-subtle text-primary border border-primary-subtle">나</span>'
                        : `<button class="btn btn-outline-secondary btn-sm py-0 px-2 btn-quick-dm" title="귓속말 보내기">
                               <i class="bi bi-chat-quote"></i>
                           </button>`
                    }
                </div>
            `;

            if (!isMe) {
                const dmBtn = li.querySelector('.btn-quick-dm');
                dmBtn.addEventListener('click', () => {
                    selectDmTarget(u.ip);
                });
            }

            onlineUsersList.appendChild(li);
        });
    }

    function updateReceiverDropdown(users) {
        const currentSelected = receiverSelect.value;
        receiverSelect.innerHTML = '<option value="">수신자 선택...</option>';

        users.forEach(u => {
            if (u.ip !== CURRENT_USER_IP) {
                const opt = document.createElement('option');
                opt.value = u.ip;
                opt.textContent = `${u.nickname} (${u.ip})`;
                if (u.ip === currentSelected) {
                    opt.selected = true;
                }
                receiverSelect.appendChild(opt);
            }
        });
    }

    function selectDmTarget(targetIp) {
        document.getElementById('typeDm').checked = true;
        receiverSelectWrapper.classList.remove('d-none');
        receiverSelect.value = targetIp;
        messageInput.focus();
    }

    // File attachment handling
    if (btnAttachFile && fileInput) {
        btnAttachFile.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files[0]) {
                selectedFile = fileInput.files[0];
                attachedFileName.textContent = selectedFile.name;
                attachedFileSize.textContent = `(${formatFileSize(selectedFile.size)})`;

                if (selectedFile.type.startsWith('image/')) {
                    attachedFileIcon.className = 'bi bi-file-image fs-5 text-success me-2';
                } else {
                    attachedFileIcon.className = 'bi bi-file-earmark-arrow-up fs-5 text-primary me-2';
                }

                attachedFilePreviewContainer.classList.remove('d-none');
            }
        });
    }

    if (btnRemoveAttachedFile) {
        btnRemoveAttachedFile.addEventListener('click', () => {
            clearSelectedFile();
        });
    }

    function clearSelectedFile() {
        selectedFile = null;
        if (fileInput) fileInput.value = '';
        if (attachedFilePreviewContainer) attachedFilePreviewContainer.classList.add('d-none');
    }

    // 5. Send message handler
    async function sendMessage() {
        const content = messageInput.value.trim();
        if (!content && !selectedFile) return;

        const selectedType = document.querySelector('input[name="sendType"]:checked').value;
        let receiverIp = null;

        if (selectedType === 'dm') {
            receiverIp = receiverSelect.value;
            if (!receiverIp) {
                alert('귓속말을 보낼 대상 사용자를 선택해주세요.');
                receiverSelect.focus();
                return;
            }
        }

        let fileData = null;

        // Upload file if selected
        if (selectedFile) {
            btnSend.disabled = true;
            btnSend.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';

            const formData = new FormData();
            formData.append('file', selectedFile);

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const resJson = await response.json();
                if (!resJson.success) {
                    alert(resJson.message || '파일 업로드에 실패했습니다.');
                    resetSendButton();
                    return;
                }
                fileData = resJson;
            } catch (err) {
                console.error('File upload error:', err);
                alert('파일 업로드 중 네트워크 오류가 발생했습니다.');
                resetSendButton();
                return;
            } finally {
                resetSendButton();
            }
        }

        socket.emit('send_message', {
            type: selectedType,
            content: content,
            receiver_ip: receiverIp,
            file_url: fileData ? fileData.file_url : null,
            file_name: fileData ? fileData.file_name : null,
            file_size: fileData ? fileData.file_size : null,
            file_type: fileData ? fileData.file_type : null
        });

        messageInput.value = '';
        clearSelectedFile();
        messageInput.focus();
    }

    function resetSendButton() {
        btnSend.disabled = false;
        btnSend.innerHTML = '<div><i class="bi bi-send-fill me-1"></i>전송</div><small class="text-white-50" style="font-size: 0.65rem;">Enter</small>';
    }

    btnSend.addEventListener('click', sendMessage);

    // Keydown handler: Enter sends message, Ctrl + Enter inserts newline!
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            if (e.ctrlKey) {
                // Ctrl + Enter: Insert newline and don't send!
                e.preventDefault();
                const start = messageInput.selectionStart;
                const end = messageInput.selectionEnd;
                const val = messageInput.value;
                messageInput.value = val.substring(0, start) + "\n" + val.substring(end);
                messageInput.selectionStart = messageInput.selectionEnd = start + 1;
            } else if (!e.shiftKey) {
                // Normal Enter: Send message!
                e.preventDefault();
                sendMessage();
            }
        }
    });

    // 6. Receive chat messages
    socket.on('receive_message', (msg) => {
        appendMessage(msg);
        scrollToBottom();
    });

    function renderFileHtml(msg) {
        if (!msg.file_url) return '';
        const filename = msg.file_name || '첨부파일';
        const cleanUrl = msg.file_url;
        const savedName = cleanUrl.split('/').pop();
        const downloadUrl = `/api/download/${savedName}?name=${encodeURIComponent(filename)}`;

        if (msg.file_type === 'image') {
            return `
                <div class="mt-2">
                    <a href="${cleanUrl}" target="_blank" title="클릭하여 원본 사진 보기">
                        <img src="${cleanUrl}" class="chat-image-attachment border shadow-sm" alt="${escapeHtml(filename)}">
                    </a>
                </div>
            `;
        } else {
            const sizeStr = msg.file_size ? formatFileSize(msg.file_size) : '';
            return `
                <div class="mt-2">
                    <a href="${downloadUrl}" class="chat-file-box shadow-sm" download>
                        <i class="bi bi-file-earmark-arrow-down-fill fs-4 text-primary me-2"></i>
                        <div class="text-truncate" style="max-width: 280px;">
                            <div class="fw-semibold small text-truncate">${escapeHtml(filename)}</div>
                            <small class="text-muted">${sizeStr ? sizeStr + ' • ' : ''}클릭하여 다운로드</small>
                        </div>
                    </a>
                </div>
            `;
        }
    }

    function appendMessage(msg) {
        const div = document.createElement('div');
        const fileHtml = renderFileHtml(msg);
        const contentHtml = msg.content ? `<div class="message-body ps-1 text-break">${escapeHtml(msg.content)}</div>` : '';

        if (msg.msg_type === 'notice') {
            div.className = 'message-card notice-message p-2 rounded-3 border-start border-4 border-warning bg-warning-subtle shadow-sm';
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span>
                        <span class="badge bg-warning text-dark me-1"><i class="bi bi-megaphone-fill me-1"></i>공지</span>
                        <strong class="text-dark">${escapeHtml(msg.sender_name)}</strong>
                        <small class="text-muted">(${escapeHtml(msg.sender_ip)})</small>
                    </span>
                    <small class="text-muted">${msg.created_at}</small>
                </div>
                ${msg.content ? `<div class="message-body text-dark fw-bold ps-2">${escapeHtml(msg.content)}</div>` : ''}
                ${fileHtml}
            `;
        } else if (msg.msg_type === 'dm') {
            div.className = 'message-card dm-message p-2 rounded-3 border-start border-4 border-info bg-info-subtle shadow-sm';
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span>
                        <span class="badge bg-info text-dark me-1"><i class="bi bi-lock-fill me-1"></i>귓속말</span>
                        <strong class="text-primary">${escapeHtml(msg.sender_name)}</strong>
                        <i class="bi bi-arrow-right mx-1 text-muted"></i>
                        <strong class="text-dark">${escapeHtml(msg.receiver_name || msg.receiver_ip)}</strong>
                    </span>
                    <small class="text-muted">${msg.created_at}</small>
                </div>
                ${msg.content ? `<div class="message-body ps-2">${escapeHtml(msg.content)}</div>` : ''}
                ${fileHtml}
            `;
        } else {
            const isMe = (msg.sender_ip === CURRENT_USER_IP);
            div.className = `message-card all-message p-2 rounded-3 bg-white border shadow-sm ${isMe ? 'border-primary-subtle' : ''}`;
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span>
                        <strong class="${isMe ? 'text-primary' : 'text-dark'}">${escapeHtml(msg.sender_name)}</strong>
                        <small class="text-muted">(${escapeHtml(msg.sender_ip)})</small>
                        ${isMe ? '<span class="badge bg-light text-primary border">나</span>' : ''}
                    </span>
                    <small class="text-muted">${msg.created_at}</small>
                </div>
                ${contentHtml}
                ${fileHtml}
            `;
        }

        chatMessages.appendChild(div);
    }

    // 7. Receive notice event (Update top notice banner)
    socket.on('receive_notice', (notice) => {
        noticeContent.textContent = notice.content;
        noticeAuthor.textContent = notice.author_name;
        noticeTime.textContent = notice.created_at;
        noticeBanner.setAttribute('data-notice-id', notice.id || '');
        noticeBanner.classList.remove('d-none');
    });

    // Handle notice deletion request
    if (btnDeleteNotice) {
        btnDeleteNotice.addEventListener('click', () => {
            if (confirm('현재 등록된 공지사항을 삭제하시겠습니까?')) {
                const noticeId = noticeBanner.getAttribute('data-notice-id');
                socket.emit('delete_notice', { notice_id: noticeId ? parseInt(noticeId) : null });
            }
        });
    }

    // Notice deleted event from server
    socket.on('notice_deleted', () => {
        noticeBanner.classList.add('d-none');
        noticeBanner.removeAttribute('data-notice-id');
        noticeContent.textContent = '';
        noticeAuthor.textContent = '';
        noticeTime.textContent = '';
    });

    // 8. Receive system message
    socket.on('system_message', (data) => {
        const div = document.createElement('div');
        div.className = 'text-center my-1';
        div.innerHTML = `
            <span class="system-message">
                <i class="bi bi-info-circle me-1"></i>${escapeHtml(data.content)}
            </span>
        `;
        chatMessages.appendChild(div);
        scrollToBottom();
    });

    // 9. Error message
    socket.on('error_message', (data) => {
        alert(data.message);
    });

    // 10. Nickname change handler
    btnSaveNickname.addEventListener('click', () => {
        const newNick = newNicknameInput.value.trim();
        if (!newNick) {
            alert('닉네임을 입력해주세요.');
            return;
        }
        if (newNick.length > 30) {
            alert('닉네임은 30자 이하여야 합니다.');
            return;
        }

        socket.emit('change_nickname', { nickname: newNick });
        nicknameModal.hide();
    });

    socket.on('nickname_changed', (data) => {
        if (data.ip === CURRENT_USER_IP) {
            CURRENT_USER_NICKNAME = data.new_nickname;
            currentNicknameSpan.textContent = data.new_nickname;
            newNicknameInput.value = data.new_nickname;
        }
    });

    // 10-1. Clear all messages functionality
    if (btnClearChat) {
        btnClearChat.addEventListener('click', () => {
            if (confirm('저장된 모든 대화 내용을 삭제하시겠습니까?\n이 작업은 취소할 수 없습니다.')) {
                socket.emit('clear_all_messages');
            }
        });
    }

    socket.on('chat_cleared', () => {
        chatMessages.innerHTML = '';
    });

    // 11. Search / Explore messages modal functionality
    btnExecuteSearch.addEventListener('click', performSearch);
    searchKeyword.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch();
        }
    });

    async function performSearch() {
        const keyword = searchKeyword.value.trim();
        const type = searchTypeFilter.value;

        searchResultsList.innerHTML = `
            <div class="text-center py-4 text-muted">
                <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                메시지를 검색하고 있습니다...
            </div>
        `;

        try {
            const res = await fetch(`/api/search?keyword=${encodeURIComponent(keyword)}&type=${encodeURIComponent(type)}`);
            const data = await res.json();

            if (!data.success) {
                searchResultsList.innerHTML = `<div class="alert alert-danger">검색 중 오류가 발생했습니다.</div>`;
                return;
            }

            searchResultCount.textContent = `${data.count}건`;

            if (data.results.length === 0) {
                searchResultsList.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-emoji-neutral display-6 mb-2 d-block"></i>
                        검색 조건에 일치하는 채팅 내용이 없습니다.
                    </div>
                `;
                return;
            }

            searchResultsList.innerHTML = '';
            data.results.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'search-result-item bg-white p-3 rounded-3 border shadow-sm';

                let badgeHtml = '';
                if (item.msg_type === 'notice') {
                    badgeHtml = '<span class="badge bg-warning text-dark"><i class="bi bi-megaphone-fill me-1"></i>공지</span>';
                } else if (item.msg_type === 'dm') {
                    badgeHtml = `<span class="badge bg-info text-dark"><i class="bi bi-lock-fill me-1"></i>귓속말 (${escapeHtml(item.receiver_name || item.receiver_ip)})</span>`;
                } else {
                    badgeHtml = '<span class="badge bg-secondary"><i class="bi bi-globe me-1"></i>전체</span>';
                }

                let fileBadgeHtml = '';
                if (item.file_url) {
                    if (item.file_type === 'image') {
                        fileBadgeHtml = `<div class="mt-2"><a href="${item.file_url}" target="_blank"><img src="${item.file_url}" class="chat-image-attachment border" style="max-height: 120px;"></a></div>`;
                    } else {
                        fileBadgeHtml = `<div class="mt-2"><span class="badge bg-light text-dark border"><i class="bi bi-paperclip me-1"></i>첨부: ${escapeHtml(item.file_name || '파일')}</span></div>`;
                    }
                }

                itemDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <div>
                            ${badgeHtml}
                            <strong class="ms-2 text-dark">${escapeHtml(item.sender_name)}</strong>
                            <small class="text-muted">(${escapeHtml(item.sender_ip)})</small>
                        </div>
                        <small class="text-muted font-monospace">${item.created_at}</small>
                    </div>
                    ${item.content ? `<div class="text-dark mt-2 ps-1 text-break message-body">${highlightKeyword(escapeHtml(item.content), keyword)}</div>` : ''}
                    ${fileBadgeHtml}
                `;

                searchResultsList.appendChild(itemDiv);
            });

        } catch (err) {
            console.error('Search error:', err);
            searchResultsList.innerHTML = `<div class="alert alert-danger">서버와 통신할 수 없습니다.</div>`;
        }
    }

    function highlightKeyword(text, keyword) {
        if (!keyword) return text;
        const regex = new RegExp(`(${escapeRegExp(keyword)})`, 'gi');
        return text.replace(regex, '<mark class="bg-warning-subtle fw-bold">$1</mark>');
    }

    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // Helper: HTML escaping to prevent XSS
    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    // -------------------------------------------------------------
    // Screen Sharing WebRTC Logic
    // -------------------------------------------------------------
    const rtcConfig = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ]
    };

    let localScreenStream = null;
    let isSharingMyScreen = false;
    let currentSharerSid = null;
    let peerConnections = {};        // Presenter: { [viewerSid]: RTCPeerConnection }
    let viewerPeerConnection = null; // Viewer: RTCPeerConnection

    // Screen share button click
    if (btnToggleScreenShare) {
        btnToggleScreenShare.addEventListener('click', () => {
            if (isSharingMyScreen) {
                stopMyScreenSharing();
            } else {
                startScreenSharing();
            }
        });
    }

    if (btnStopSharingMyScreen) {
        btnStopSharingMyScreen.addEventListener('click', () => {
            stopMyScreenSharing();
        });
    }

    if (btnFullscreenScreen) {
        btnFullscreenScreen.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                if (screenShareVideo && screenShareVideo.requestFullscreen) {
                    screenShareVideo.requestFullscreen();
                }
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                }
            }
        });
    }

    async function startScreenSharing() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
            alert('현재 브라우저에서는 화면 공유(Display Media) 기능을 지원하지 않습니다.');
            return;
        }

        try {
            localScreenStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    cursor: 'always'
                },
                audio: false
            });
        } catch (err) {
            console.warn('Screen share canceled or denied:', err);
            return;
        }

        isSharingMyScreen = true;

        // When user stops sharing from browser's native floating bar
        const videoTrack = localScreenStream.getVideoTracks()[0];
        if (videoTrack) {
            videoTrack.addEventListener('ended', () => {
                stopMyScreenSharing();
            });
        }

        // Display local screen in video player
        if (screenShareVideo) {
            screenShareVideo.srcObject = localScreenStream;
            screenShareVideo.muted = true;
        }
        if (screenShareSection) {
            screenShareSection.classList.remove('d-none');
        }
        if (screenSharerText) {
            screenSharerText.textContent = '내 화면 (공유 중)';
        }
        if (btnStopSharingMyScreen) {
            btnStopSharingMyScreen.classList.remove('d-none');
        }

        // Update nav toggle button
        if (btnToggleScreenShare) {
            btnToggleScreenShare.innerHTML = '<i class="bi bi-display-fill me-1"></i>공유 중지';
            btnToggleScreenShare.classList.remove('btn-outline-warning');
            btnToggleScreenShare.classList.add('btn-danger');
        }

        // Notify server that screen share started
        socket.emit('start_screen_share');
    }

    function stopMyScreenSharing() {
        if (!isSharingMyScreen) return;
        isSharingMyScreen = false;

        if (localScreenStream) {
            localScreenStream.getTracks().forEach(track => track.stop());
            localScreenStream = null;
        }

        // Close all peer connections
        for (const sid in peerConnections) {
            if (peerConnections[sid]) {
                peerConnections[sid].close();
            }
        }
        peerConnections = {};

        // Notify server
        socket.emit('stop_screen_share');
        resetScreenShareUI();
    }

    function resetScreenShareUI() {
        if (screenShareVideo) {
            screenShareVideo.srcObject = null;
        }
        if (screenShareSection) {
            screenShareSection.classList.add('d-none');
        }
        if (btnStopSharingMyScreen) {
            btnStopSharingMyScreen.classList.add('d-none');
        }
        if (btnToggleScreenShare) {
            btnToggleScreenShare.innerHTML = '<i class="bi bi-display me-1"></i>화면 공유';
            btnToggleScreenShare.classList.remove('btn-danger');
            btnToggleScreenShare.classList.add('btn-outline-warning');
            btnToggleScreenShare.disabled = false;
        }
        if (screenShareLoading) {
            screenShareLoading.classList.add('d-none');
        }
        currentSharerSid = null;
    }

    // Server says someone started screen sharing
    socket.on('screen_share_started', async (data) => {
        if (data.sid === socket.id) {
            // I am the presenter, UI already set
            return;
        }

        // I am a viewer
        currentSharerSid = data.sid;
        if (screenShareSection) {
            screenShareSection.classList.remove('d-none');
        }
        if (screenSharerText) {
            screenSharerText.textContent = `${data.nickname} (${data.ip})`;
        }
        if (btnStopSharingMyScreen) {
            btnStopSharingMyScreen.classList.add('d-none');
        }

        if (btnToggleScreenShare) {
            btnToggleScreenShare.disabled = true;
            btnToggleScreenShare.innerHTML = '<i class="bi bi-display me-1"></i>시청 중';
        }

        if (screenShareLoading) {
            screenShareLoading.classList.remove('d-none');
        }

        // Prepare viewer peer connection
        if (viewerPeerConnection) {
            viewerPeerConnection.close();
        }

        viewerPeerConnection = new RTCPeerConnection(rtcConfig);

        viewerPeerConnection.ontrack = (event) => {
            if (event.streams && event.streams[0]) {
                if (screenShareVideo) {
                    screenShareVideo.srcObject = event.streams[0];
                }
                if (screenShareLoading) {
                    screenShareLoading.classList.add('d-none');
                }
            }
        };

        viewerPeerConnection.onicecandidate = (event) => {
            if (event.candidate && currentSharerSid) {
                socket.emit('screen_signal', {
                    target_sid: currentSharerSid,
                    signal: { type: 'candidate', candidate: event.candidate }
                });
            }
        };

        // Notify presenter that viewer is ready to receive offer
        socket.emit('screen_signal', {
            target_sid: currentSharerSid,
            signal: { type: 'viewer_ready' }
        });
    });

    // Server says screen sharing stopped
    socket.on('screen_share_stopped', () => {
        if (viewerPeerConnection) {
            viewerPeerConnection.close();
            viewerPeerConnection = null;
        }
        if (isSharingMyScreen) {
            if (localScreenStream) {
                localScreenStream.getTracks().forEach(track => track.stop());
                localScreenStream = null;
            }
            peerConnections = {};
            isSharingMyScreen = false;
        }
        resetScreenShareUI();
    });

    // Handle incoming WebRTC signals
    socket.on('screen_signal', async (data) => {
        const fromSid = data.from_sid;
        const signal = data.signal;

        if (isSharingMyScreen) {
            // Presenter received signal from viewer
            if (signal.type === 'viewer_ready') {
                const pc = new RTCPeerConnection(rtcConfig);
                peerConnections[fromSid] = pc;

                if (localScreenStream) {
                    localScreenStream.getTracks().forEach(track => {
                        pc.addTrack(track, localScreenStream);
                    });
                }

                pc.onicecandidate = (event) => {
                    if (event.candidate) {
                        socket.emit('screen_signal', {
                            target_sid: fromSid,
                            signal: { type: 'candidate', candidate: event.candidate }
                        });
                    }
                };

                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);

                socket.emit('screen_signal', {
                    target_sid: fromSid,
                    signal: { type: 'offer', sdp: pc.localDescription }
                });

            } else if (signal.type === 'answer') {
                const pc = peerConnections[fromSid];
                if (pc && signal.sdp) {
                    await pc.setRemoteDescription(new RTCSessionDescription(signal.sdp));
                }

            } else if (signal.type === 'candidate') {
                const pc = peerConnections[fromSid];
                if (pc && signal.candidate) {
                    try {
                        await pc.addIceCandidate(new RTCIceCandidate(signal.candidate));
                    } catch (e) {
                        console.warn('Error adding ice candidate:', e);
                    }
                }
            }

        } else if (viewerPeerConnection && currentSharerSid === fromSid) {
            // Viewer received signal from presenter
            if (signal.type === 'offer' && signal.sdp) {
                await viewerPeerConnection.setRemoteDescription(new RTCSessionDescription(signal.sdp));
                const answer = await viewerPeerConnection.createAnswer();
                await viewerPeerConnection.setLocalDescription(answer);

                socket.emit('screen_signal', {
                    target_sid: currentSharerSid,
                    signal: { type: 'answer', sdp: viewerPeerConnection.localDescription }
                });

            } else if (signal.type === 'candidate' && signal.candidate) {
                try {
                    await viewerPeerConnection.addIceCandidate(new RTCIceCandidate(signal.candidate));
                } catch (e) {
                    console.warn('Error adding ice candidate on viewer:', e);
                }
            }
        }
    });
});

