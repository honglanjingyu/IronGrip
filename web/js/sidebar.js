// web/js/sidebar.js - 完整修复版（显示第一条消息）

/**
 * 切换侧边栏折叠状态
 */
function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
}

/**
 * 切换移动端侧边栏
 */
function toggleMobileSidebar() {
    sidebar.classList.toggle('mobile-open');
}

/**
 * 复制会话 ID
 */
function copySessionId() {
    if (currentSessionId && currentSessionId !== 'null' && currentSessionId !== 'undefined') {
        navigator.clipboard.writeText(currentSessionId);
        showToast('会话ID已复制', 'success');
    } else {
        showToast('暂无有效会话', 'warning');
    }
}

// 缓存会话第一条消息
window.sessionFirstMessages = window.sessionFirstMessages || {};

/**
 * 获取会话的第一条消息（第一个用户问题）
 * @param {string} sessionId - 会话ID
 * @returns {Promise<string|null>} 第一条消息内容
 */
async function getSessionFirstMessage(sessionId) {
    // 检查缓存
    if (window.sessionFirstMessages[sessionId]) {
        return window.sessionFirstMessages[sessionId];
    }

    // 如果是新会话，显示"新对话"
    if (sessionId && sessionId.startsWith('new_')) {
        return "新对话";
    }

    try {
        const response = await fetch(`${API_BASE}/session/${sessionId}/history?limit=10`);
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.messages && data.messages.length > 0) {
                // 找第一条用户消息
                const firstUserMsg = data.messages.find(msg => msg.role === 'user');
                if (firstUserMsg) {
                    let content = firstUserMsg.content;
                    // 截取前30个字符
                    if (content.length > 30) {
                        content = content.substring(0, 30) + '...';
                    }
                    window.sessionFirstMessages[sessionId] = content;
                    return content;
                }
            }
        }
        return null;
    } catch (error) {
        console.warn('获取会话第一条消息失败:', error);
        return null;
    }
}

/**
 * 更新会话的第一条消息缓存（在发送新消息时调用）
 * @param {string} sessionId - 会话ID
 * @param {string} message - 用户消息
 */
async function updateSessionFirstMessage(sessionId, message) {
    if (!sessionId || !message) return;

    // 检查是否已经有缓存
    if (window.sessionFirstMessages && window.sessionFirstMessages[sessionId]) {
        return;
    }

    // 缓存第一条消息
    let displayMsg = message;
    if (displayMsg.length > 30) {
        displayMsg = displayMsg.substring(0, 30) + '...';
    }
    window.sessionFirstMessages[sessionId] = displayMsg;

    // 刷新历史列表
    await updateHistoryList();
}

/**
 * 更新历史列表 UI - 显示第一条消息
 */
async function updateHistoryList() {
    let sessions = [];
    try {
        sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
    } catch (e) {
        sessions = [];
    }

    const historyList = document.getElementById('chatHistoryList');

    if (!historyList) return;

    // 过滤掉无效的会话ID
    const validSessions = sessions.filter(s => s && s !== 'null' && s !== 'undefined');

    if (validSessions.length === 0) {
        historyList.innerHTML = '<div class="empty-history">暂无历史对话</div>';
        return;
    }

    // 显示加载状态
    historyList.innerHTML = '<div class="empty-history">加载中...</div>';

    // 异步加载每条会话的第一条消息
    const historyItems = [];
    for (const sessionId of validSessions) {
        const isActive = (sessionId === currentSessionId);
        const shortId = sessionId.length > 8 ? sessionId.substring(0, 8) + '...' : sessionId;

        // 尝试获取第一条消息
        let firstMessage = await getSessionFirstMessage(sessionId);

        let displayText;
        if (firstMessage) {
            displayText = firstMessage;
        } else {
            displayText = `会话: ${shortId}`;
        }

        historyItems.push(`
            <div class="history-item ${isActive ? 'active' : ''}" data-session-id="${sessionId}">
                <div class="history-item-content">
                    <i class="fas fa-comment"></i>
                    <span title="${escapeHtml(firstMessage || sessionId)}">${escapeHtml(displayText)}</span>
                </div>
                <button class="history-item-delete" data-session-id="${sessionId}" title="删除会话">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `);
    }

    historyList.innerHTML = historyItems.join('');

    // 绑定历史列表事件
    document.querySelectorAll('.history-item').forEach(item => {
        const sessionId = item.dataset.sessionId;
        if (!sessionId) return;

        // 点击项目主体切换会话
        item.addEventListener('click', (e) => {
            if (e.target.closest('.history-item-delete')) return;
            e.stopPropagation();
            if (sessionId) switchSession(sessionId);
        });

        // 删除按钮
        const deleteBtn = item.querySelector('.history-item-delete');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (sessionId) deleteSession(sessionId);
            });
        }
    });
}

// 切换会话锁，防止重复切换
let isSwitchingSession = false;

/**
 * 切换会话 - 只从 Redis 加载
 * @param {string} sessionId - 会话ID
 */
async function switchSession(sessionId) {
    if (!sessionId) return;
    if (isSending) {
        showToast('请等待当前回答完成', 'warning');
        return;
    }

    // 防止重复切换
    if (isSwitchingSession) {
        console.log('已经在切换会话，跳过');
        return;
    }

    if (sessionId === currentSessionId) {
        console.log('已经是当前会话，跳过切换');
        return;
    }

    isSwitchingSession = true;

    console.log('切换会话:', sessionId);

    currentSessionId = sessionId;

    // 更新显示
    if (sessionIdDisplay) {
        const shortId = sessionId.length > 8 ? sessionId.substring(0, 8) + '...' : sessionId;
        sessionIdDisplay.textContent = `会话: ${shortId}`;
        sessionIdDisplay.title = `会话ID: ${sessionId}`;
    }

    // 更新 URL
    updateURLWithSessionId(sessionId);

    // 保存到 localStorage（只保存会话ID）
    try {
        localStorage.setItem(STORAGE_KEY_SESSION, sessionId);
    } catch (e) {
        console.warn('保存会话失败:', e);
    }

    // 清空当前消息区
    if (messagesArea) {
        const existingMessages = messagesArea.querySelectorAll('.message');
        existingMessages.forEach(msg => msg.remove());
    }

    // 从 Redis 加载会话历史
    try {
        const response = await fetch(`${API_BASE}/session/${sessionId}/history?limit=100`);
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.messages && data.messages.length > 0) {
                chatHistory = data.messages.map(msg => ({
                    role: msg.role,
                    content: msg.content
                }));
                renderMessages();

                // 获取第一条消息用于显示
                const firstUserMsg = data.messages.find(msg => msg.role === 'user');
                const firstMsgText = firstUserMsg ? (firstUserMsg.content.length > 30 ? firstUserMsg.content.substring(0, 30) + '...' : firstUserMsg.content) : sessionId.substring(0, 8);
                showToast(`已切换到会话 "${firstMsgText}" (${data.messages.length} 条消息)`, 'success');
            } else {
                chatHistory = [];
                renderWelcomeMessage();
                showToast(`已切换到会话`, 'info');
            }
        } else {
            chatHistory = [];
            renderWelcomeMessage();
            showToast(`已切换到会话`, 'info');
        }
    } catch (error) {
        console.error('加载会话历史失败:', error);
        chatHistory = [];
        renderWelcomeMessage();
        showToast(`切换到会话失败: ${error.message}`, 'error');
    }

    // 更新历史列表高亮
    await updateHistoryList();

    isSwitchingSession = false;
}

/**
 * 删除会话
 * @param {string} sessionId - 会话ID
 */
async function deleteSession(sessionId) {
    if (!sessionId) return;

    if (confirm('确定要删除这个会话吗？此操作不可恢复。')) {
        console.log('删除会话:', sessionId);

        // 调用后端删除
        try {
            const response = await fetch(`${API_BASE}/session/${sessionId}`, { method: 'DELETE' });
            if (!response.ok) {
                console.warn('后端删除返回:', response.status);
            }
        } catch (e) {
            console.warn('后端删除失败:', e);
        }

        // 从会话列表中移除
        let sessions = [];
        try {
            sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
        } catch (e) {
            sessions = [];
        }

        const newSessions = sessions.filter(s => s !== sessionId);
        localStorage.setItem('sessions', JSON.stringify(newSessions));

        // 清除缓存
        delete window.sessionFirstMessages[sessionId];

        // 如果删除的是当前会话
        if (sessionId === currentSessionId) {
            if (newSessions.length > 0) {
                // 切换到第一个会话
                await switchSession(newSessions[0]);
            } else {
                // 没有其他会话，创建新会话
                await handleNewChat();
            }
        } else {
            await updateHistoryList();
        }

        showToast('会话已删除', 'success');
    }
}

/**
 * 创建新对话
 */
async function createNewChat() {
    if (isSending) {
        showToast('请等待当前回答完成', 'warning');
        return;
    }

    // 防止重复创建
    if (isSwitchingSession) {
        console.log('正在切换会话，跳过创建');
        return;
    }

    isSwitchingSession = true;

    console.log('创建新对话');

    // 调用后端创建新会话
    try {
        const response = await fetch(`${API_BASE}/session/create?user_id=web_user`);
        if (response.ok) {
            const data = await response.json();
            if (data.session_id) {
                currentSessionId = data.session_id;

                if (sessionIdDisplay) {
                    const shortId = currentSessionId.substring(0, 8) + '...';
                    sessionIdDisplay.textContent = `会话: ${shortId}`;
                }

                // 更新 URL
                updateURLWithSessionId(currentSessionId);

                // 保存到 localStorage
                try {
                    localStorage.setItem(STORAGE_KEY_SESSION, currentSessionId);
                } catch (e) {}

                // 更新会话列表
                updateSessionList();

                chatHistory = [];
                renderWelcomeMessage();
                await updateHistoryList();

                showToast('✨ 已创建新会话', 'success');
            } else {
                throw new Error('No session_id returned');
            }
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('创建新会话失败:', error);
        // 降级方案：生成本地会话ID
        currentSessionId = 'new_' + Math.random().toString(36).substring(2, 10);
        if (sessionIdDisplay) {
            const shortId = currentSessionId.substring(0, 8) + '...';
            sessionIdDisplay.textContent = `会话: ${shortId}`;
        }
        updateURLWithSessionId(currentSessionId);
        try {
            localStorage.setItem(STORAGE_KEY_SESSION, currentSessionId);
        } catch (e) {}
        updateSessionList();
        chatHistory = [];
        renderWelcomeMessage();
        await updateHistoryList();
        showToast('✨ 已创建新会话（本地）', 'success');
    }

    // 关闭移动端侧边栏
    if (sidebar) {
        sidebar.classList.remove('mobile-open');
    }

    isSwitchingSession = false;
}

/**
 * 清空所有会话
 */
async function clearAllSessions() {
    if (confirm('确定要清空所有会话吗？此操作不可恢复。')) {
        let sessions = [];
        try {
            sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
        } catch (e) {
            sessions = [];
        }

        // 删除所有会话
        for (const sessionId of sessions) {
            try {
                await fetch(`${API_BASE}/session/${sessionId}`, { method: 'DELETE' });
            } catch (e) {
                console.warn('删除会话失败:', sessionId, e);
            }
        }

        localStorage.removeItem('sessions');
        localStorage.removeItem(STORAGE_KEY_SESSION);

        // 清除缓存
        window.sessionFirstMessages = {};

        // 创建新会话
        await handleNewChat();

        showToast('所有会话已清空', 'info');
    }
}

// 导出函数到全局（供其他模块调用）
window.updateSessionFirstMessage = updateSessionFirstMessage;
window.updateHistoryList = updateHistoryList;