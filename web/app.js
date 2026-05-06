// web/app.js
// API 配置
let API_BASE = '/api/v1';
let currentSessionId = null;
let chatHistory = [];
let isStreaming = true;
let autoScroll = true;
let isSending = false;  // 防止重复发送
let thinkingAnimationInterval = null;  // 思考动画定时器

// DOM 元素
const messagesArea = document.getElementById('messagesArea');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const clearAllBtn = document.getElementById('clearAllBtn');
const sidebarToggle = document.getElementById('sidebarToggle');
const menuBtn = document.getElementById('menuBtn');
const sidebar = document.getElementById('sidebar');
const sessionIdDisplay = document.getElementById('sessionIdDisplay');
const copySessionBtn = document.getElementById('copySessionBtn');
const knowledgeBtn = document.getElementById('knowledgeBtn');
const statsBtn = document.getElementById('statsBtn');
const settingsBtn = document.getElementById('settingsBtn');
const streamToggle = document.getElementById('streamToggle');
const autoScrollToggle = document.getElementById('autoScrollToggle');
const apiUrlInput = document.getElementById('apiUrl');
const charCountSpan = document.getElementById('charCount');
const statusIcon = document.getElementById('statusIcon');
const statusText = document.getElementById('statusText');

// ========== 修复后的 Markdown 解析函数 ==========

/**
 * 转义 HTML 特殊字符
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 格式化 Markdown 为 HTML
 * 支持：标题、粗体、斜体、代码块、行内代码、列表、链接
 */
function formatMarkdown(text) {
    if (!text) return '';

    // 第一步：提取代码块，避免内部内容被处理
    const codeBlocks = [];
    let processed = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        const index = codeBlocks.length;
        codeBlocks.push({ lang: lang || 'text', code: code.trim() });
        return `__CODE_BLOCK_${index}__`;
    });

    // 提取行内代码，临时替换
    const inlineCodes = [];
    processed = processed.replace(/`([^`]+)`/g, (match, code) => {
        const index = inlineCodes.length;
        inlineCodes.push(code);
        return `__INLINE_CODE_${index}__`;
    });

    // 转义 HTML
    let formatted = escapeHtml(processed);

    // 恢复行内代码
    inlineCodes.forEach((code, index) => {
        const placeholder = `__INLINE_CODE_${index}__`;
        formatted = formatted.replace(placeholder, `<code>${escapeHtml(code)}</code>`);
    });

    // 处理标题（必须在其他格式之前，因为标题可能包含其他标记）
    formatted = formatted.replace(/^#### (.*?)$/gm, '<h4>$1</h4>');
    formatted = formatted.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    formatted = formatted.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // 处理粗体
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 处理斜体（不匹配已经处理过的粗体）
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 处理链接 [text](url)
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // 处理无序列表
    const listLines = formatted.split('\n');
    let inList = false;
    let listItems = [];
    const resultLines = [];

    for (let i = 0; i < listLines.length; i++) {
        const line = listLines[i];
        const isListItem = /^[-*]\s+(.*)$/.test(line);

        if (isListItem) {
            if (!inList) {
                inList = true;
                listItems = [];
            }
            const content = line.replace(/^[-*]\s+/, '');
            listItems.push(`<li>${content}</li>`);
        } else {
            if (inList) {
                resultLines.push('<ul>');
                resultLines.push(...listItems);
                resultLines.push('</ul>');
                inList = false;
                listItems = [];
            }
            resultLines.push(line);
        }
    }

    if (inList) {
        resultLines.push('<ul>');
        resultLines.push(...listItems);
        resultLines.push('</ul>');
    }

    formatted = resultLines.join('\n');

    // 处理换行（连续两个换行变成段落分隔）
    formatted = formatted.replace(/\n\n/g, '</p><p>');
    formatted = formatted.replace(/\n/g, '<br>');

    // 包装段落
    if (!formatted.startsWith('<h') && !formatted.startsWith('<ul') && !formatted.startsWith('<pre')) {
        formatted = `<p>${formatted}</p>`;
    }

    // 恢复代码块
    codeBlocks.forEach((block, index) => {
        const placeholder = `__CODE_BLOCK_${index}__`;
        const langClass = block.lang !== 'text' ? ` class="language-${block.lang}"` : '';
        const escapedCode = escapeHtml(block.code);
        formatted = formatted.replace(
            placeholder,
            `<pre><code${langClass}>${escapedCode}</code></pre>`
        );
    });

    return formatted;
}

// ========== 思考动画相关函数 ==========

let nextMessageId = 0;

/**
 * 添加带思考动画的等待消息
 * @returns {string} 消息元素ID
 */
function addThinkingMessage() {
    const messageId = `thinking_${Date.now()}_${nextMessageId++}`;
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant thinking';
    messageDiv.id = messageId;

    messageDiv.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-content">
            <div class="message-text">
                <span class="thinking-text">正在思考</span>
                <span class="thinking-dots">.</span>
            </div>
            <div class="message-meta"></div>
        </div>
    `;

    messagesArea.appendChild(messageDiv);

    // 启动点动画
    startThinkingAnimation(messageId);

    if (autoScroll) scrollToBottom();
    return messageId;
}

/**
 * 启动思考动画（... 循环闪烁）
 * @param {string} messageId 消息元素ID
 */
function startThinkingAnimation(messageId) {
    // 清除之前的动画
    if (thinkingAnimationInterval) {
        clearInterval(thinkingAnimationInterval);
    }

    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;

    const dotsSpan = messageDiv.querySelector('.thinking-dots');
    if (!dotsSpan) return;

    let dotCount = 1;

    thinkingAnimationInterval = setInterval(() => {
        const currentDiv = document.getElementById(messageId);
        if (!currentDiv) {
            if (thinkingAnimationInterval) {
                clearInterval(thinkingAnimationInterval);
                thinkingAnimationInterval = null;
            }
            return;
        }

        const currentDotsSpan = currentDiv.querySelector('.thinking-dots');
        if (!currentDotsSpan) return;

        dotCount = (dotCount % 3) + 1;
        currentDotsSpan.textContent = '.'.repeat(dotCount);

    }, 500);
}

/**
 * 停止思考动画
 * @param {string} thinkingMessageId 思考消息ID
 */
function stopThinkingAnimation(thinkingMessageId) {
    if (thinkingAnimationInterval) {
        clearInterval(thinkingAnimationInterval);
        thinkingAnimationInterval = null;
    }

    const thinkingDiv = document.getElementById(thinkingMessageId);
    if (thinkingDiv) {
        thinkingDiv.style.display = 'none';
    }
}

/**
 * 创建用于流式输出的消息（替换思考消息的位置）
 * @param {string} oldThinkingId 旧的思考消息ID
 * @returns {string} 新消息ID
 */
function createStreamingMessage(oldThinkingId) {
    const oldDiv = document.getElementById(oldThinkingId);
    if (!oldDiv) {
        return addEmptyAssistantMessage();
    }

    const messageId = `msg_${Date.now()}_${nextMessageId++}`;
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = messageId;

    messageDiv.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-content">
            <div class="message-text"></div>
            <div class="message-meta">${new Date().toLocaleTimeString()}</div>
        </div>
    `;

    oldDiv.parentNode.replaceChild(messageDiv, oldDiv);

    if (autoScroll) scrollToBottom();
    return messageId;
}

/**
 * 添加空助手消息（用于流式响应）
 * @returns {string} 消息ID
 */
function addEmptyAssistantMessage() {
    if (thinkingAnimationInterval) {
        clearInterval(thinkingAnimationInterval);
        thinkingAnimationInterval = null;
    }

    const messageId = `msg_${Date.now()}_${nextMessageId++}`;
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = messageId;

    messageDiv.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-content">
            <div class="message-text"></div>
            <div class="message-meta">${new Date().toLocaleTimeString()}</div>
        </div>
    `;

    messagesArea.appendChild(messageDiv);
    return messageId;
}

/**
 * 更新流式消息内容
 * @param {string} messageId 消息ID
 * @param {string} content 内容
 */
function updateStreamingMessage(messageId, content) {
    const messageDiv = document.getElementById(messageId);
    if (messageDiv) {
        const textDiv = messageDiv.querySelector('.message-text');
        if (textDiv) {
            textDiv.innerHTML = formatMarkdown(content);
        }
    }
}

/**
 * 替换思考消息为实际内容
 * @param {string} thinkingMessageId 思考消息ID
 * @param {string} content 实际内容
 * @returns {string} 新消息ID
 */
function replaceThinkingWithContent(thinkingMessageId, content) {
    if (thinkingAnimationInterval) {
        clearInterval(thinkingAnimationInterval);
        thinkingAnimationInterval = null;
    }

    const thinkingDiv = document.getElementById(thinkingMessageId);
    if (!thinkingDiv) {
        return addMessageToUI('assistant', content);
    }

    const textDiv = thinkingDiv.querySelector('.message-text');
    if (textDiv) {
        thinkingDiv.classList.remove('thinking');
        textDiv.innerHTML = formatMarkdown(content);
    }

    const newId = `msg_${Date.now()}_${nextMessageId++}`;
    thinkingDiv.id = newId;

    const metaSpan = thinkingDiv.querySelector('.message-meta');
    if (metaSpan) {
        metaSpan.textContent = new Date().toLocaleTimeString();
    }

    return newId;
}

function addMessageToUI(role, content) {
    const messageId = `msg_${Date.now()}_${nextMessageId++}`;
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.id = messageId;

    const avatar = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    const formattedContent = formatMarkdown(content);

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-text">${formattedContent}</div>
            <div class="message-meta">${new Date().toLocaleTimeString()}</div>
        </div>
    `;

    messagesArea.appendChild(messageDiv);

    if (autoScroll) scrollToBottom();
    return messageId;
}

function updateAssistantMessage(messageId, content) {
    const messageDiv = document.getElementById(messageId);
    if (messageDiv) {
        const textDiv = messageDiv.querySelector('.message-text');
        if (textDiv) {
            textDiv.innerHTML = formatMarkdown(content);
        }
    }
}

// ========== 初始化 ==========

document.addEventListener('DOMContentLoaded', async () => {
    loadSettings();
    await initSession();
    await checkHealth();
    setupEventListeners();
    setupAutoResize();
    loadChatHistoryFromStorage();
});

function loadSettings() {
    const savedApiUrl = localStorage.getItem('api_url');
    if (savedApiUrl) {
        API_BASE = savedApiUrl;
        if (apiUrlInput) apiUrlInput.value = savedApiUrl;
    }

    const savedStream = localStorage.getItem('stream_enabled');
    if (savedStream !== null) {
        isStreaming = savedStream === 'true';
        if (streamToggle) streamToggle.checked = isStreaming;
    }

    const savedAutoScroll = localStorage.getItem('auto_scroll');
    if (savedAutoScroll !== null) {
        autoScroll = savedAutoScroll === 'true';
        if (autoScrollToggle) autoScrollToggle.checked = autoScroll;
    }
}

function saveSettings() {
    localStorage.setItem('api_url', API_BASE);
    localStorage.setItem('stream_enabled', isStreaming);
    localStorage.setItem('auto_scroll', autoScroll);
}

async function initSession() {
    try {
        const response = await fetch(`${API_BASE}/session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_name: 'web_user' })
        });

        if (response.ok) {
            const data = await response.json();
            currentSessionId = data.session_id;
            sessionIdDisplay.textContent = `会话: ${currentSessionId.slice(0, 8)}...`;
            updateSessionId();
        } else {
            currentSessionId = generateSessionId();
            sessionIdDisplay.textContent = `会话: ${currentSessionId.slice(0, 8)}...`;
        }
    } catch (error) {
        console.warn('API 不可用，使用本地会话:', error);
        currentSessionId = generateSessionId();
        sessionIdDisplay.textContent = `会话: ${currentSessionId.slice(0, 8)}...`;
    }
}

function generateSessionId() {
    return 'local_' + Math.random().toString(36).substring(2, 10);
}

function updateSessionId() {
    const sessionKey = `chat_history_${currentSessionId}`;
    const saved = localStorage.getItem(sessionKey);
    if (saved) {
        try {
            chatHistory = JSON.parse(saved);
            renderMessages();
        } catch (e) {}
    } else {
        chatHistory = [];
        renderMessages();
    }
    saveChatHistoryToStorage();
    updateHistoryList();
}

function saveChatHistoryToStorage() {
    const sessionKey = `chat_history_${currentSessionId}`;
    localStorage.setItem(sessionKey, JSON.stringify(chatHistory));

    const sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
    if (!sessions.includes(currentSessionId)) {
        sessions.unshift(currentSessionId);
        if (sessions.length > 20) sessions.pop();
        localStorage.setItem('sessions', JSON.stringify(sessions));
    }
}

function loadChatHistoryFromStorage() {
    updateHistoryList();
}

function updateHistoryList() {
    const sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
    const historyList = document.getElementById('chatHistoryList');

    if (!historyList) return;

    if (sessions.length === 0) {
        historyList.innerHTML = '<div class="empty-history">暂无历史对话</div>';
        return;
    }

    historyList.innerHTML = sessions.map(sessionId => {
        const sessionKey = `chat_history_${sessionId}`;
        const history = JSON.parse(localStorage.getItem(sessionKey) || '[]');
        const firstMsg = history.find(m => m.role === 'user')?.content || '新对话';
        const preview = firstMsg.length > 20 ? firstMsg.slice(0, 20) + '...' : firstMsg;

        return `
            <div class="history-item ${sessionId === currentSessionId ? 'active' : ''}" data-session-id="${sessionId}">
                <div class="history-item-content">
                    <i class="fas fa-comment"></i>
                    <span>${escapeHtml(preview)}</span>
                </div>
                <button class="history-item-delete" data-session-id="${sessionId}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.closest('.history-item-delete')) return;
            const sessionId = item.dataset.sessionId;
            if (sessionId) switchSession(sessionId);
        });
    });

    document.querySelectorAll('.history-item-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const sessionId = btn.dataset.sessionId;
            if (sessionId) deleteSession(sessionId);
        });
    });
}

function switchSession(sessionId) {
    currentSessionId = sessionId;
    sessionIdDisplay.textContent = `会话: ${sessionId.slice(0, 8)}...`;

    const sessionKey = `chat_history_${sessionId}`;
    const saved = localStorage.getItem(sessionKey);
    if (saved) {
        try {
            chatHistory = JSON.parse(saved);
        } catch (e) {
            chatHistory = [];
        }
    } else {
        chatHistory = [];
    }

    renderMessages();
    updateHistoryList();
}

function deleteSession(sessionId) {
    const sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
    const newSessions = sessions.filter(s => s !== sessionId);
    localStorage.setItem('sessions', JSON.stringify(newSessions));
    localStorage.removeItem(`chat_history_${sessionId}`);

    if (sessionId === currentSessionId) {
        if (newSessions.length > 0) {
            switchSession(newSessions[0]);
        } else {
            createNewChat();
        }
    } else {
        updateHistoryList();
    }
}

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            statusIcon.className = 'fas fa-circle online';
            statusText.textContent = '已连接';
        } else {
            throw new Error('API 响应错误');
        }
    } catch (error) {
        statusIcon.className = 'fas fa-circle offline';
        statusText.textContent = '离线';
    }
}

function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', handleKeydown);
    newChatBtn.addEventListener('click', createNewChat);
    clearAllBtn.addEventListener('click', clearAllSessions);
    sidebarToggle.addEventListener('click', toggleSidebar);
    menuBtn.addEventListener('click', toggleMobileSidebar);
    copySessionBtn.addEventListener('click', copySessionId);
    knowledgeBtn.addEventListener('click', openKnowledgeModal);
    statsBtn.addEventListener('click', openStatsModal);
    settingsBtn.addEventListener('click', openSettingsModal);

    if (streamToggle) {
        streamToggle.addEventListener('change', (e) => {
            isStreaming = e.target.checked;
            saveSettings();
        });
    }

    if (autoScrollToggle) {
        autoScrollToggle.addEventListener('change', (e) => {
            autoScroll = e.target.checked;
            saveSettings();
        });
    }

    if (apiUrlInput) {
        apiUrlInput.addEventListener('change', (e) => {
            API_BASE = e.target.value;
            saveSettings();
            checkHealth();
        });
    }

    document.addEventListener('click', (e) => {
        const chip = e.target.closest('.suggestion-chip');
        if (chip) {
            const msg = chip.dataset.msg;
            if (msg) {
                messageInput.value = msg;
                sendMessage();
            }
        }
    });

    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.modal').forEach(modal => {
                modal.classList.remove('active');
            });
        });
    });

    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
}

function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
}

function toggleMobileSidebar() {
    sidebar.classList.toggle('mobile-open');
}

function copySessionId() {
    navigator.clipboard.writeText(currentSessionId);
    showToast('会话ID已复制', 'success');
}

function createNewChat() {
    currentSessionId = generateSessionId();
    sessionIdDisplay.textContent = `会话: ${currentSessionId.slice(0, 8)}...`;
    chatHistory = [];
    renderMessages();
    saveChatHistoryToStorage();
    updateHistoryList();
    sidebar.classList.remove('mobile-open');
}

function clearAllSessions() {
    if (confirm('确定要清空所有会话吗？此操作不可恢复。')) {
        const sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
        sessions.forEach(session => {
            localStorage.removeItem(`chat_history_${session}`);
        });
        localStorage.removeItem('sessions');
        createNewChat();
        showToast('所有会话已清空', 'info');
    }
}

// ========== 发送消息 ==========

let hasReceivedFirstChunk = false;

async function sendMessage() {
    if (isSending) {
        showToast('请等待上一消息完成', 'warning');
        return;
    }

    const message = messageInput.value.trim();
    if (!message) return;

    isSending = true;
    sendBtn.disabled = true;

    try {
        if (isStreaming) {
            await sendMessageStream(message);
        } else {
            await sendMessageNormal(message);
        }
    } catch (error) {
        console.error('发送消息失败:', error);
        showToast('发送失败: ' + error.message, 'error');
    } finally {
        isSending = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

async function sendMessageNormal(message) {
    addMessageToUI('user', message);
    messageInput.value = '';
    updateCharCount();

    const thinkingId = addThinkingMessage();

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                replaceThinkingWithContent(thinkingId, data.response);
                chatHistory.push({ role: 'user', content: message });
                chatHistory.push({ role: 'assistant', content: data.response });
                saveChatHistoryToStorage();
                updateHistoryList();
            } else {
                replaceThinkingWithContent(thinkingId, `错误: ${data.error || data.response || '未知错误'}`);
            }
        } else {
            const errorText = await response.text();
            replaceThinkingWithContent(thinkingId, `API 错误 (${response.status}): ${errorText.slice(0, 200)}`);
        }
    } catch (error) {
        replaceThinkingWithContent(thinkingId, `网络错误: ${error.message}`);
    } finally {
        if (autoScroll) scrollToBottom();
    }
}

async function sendMessageStream(message) {
    hasReceivedFirstChunk = false;

    addMessageToUI('user', message);
    messageInput.value = '';
    updateCharCount();

    const thinkingId = addThinkingMessage();

    let fullResponse = '';
    let hasError = false;

    try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId,
                stream: true
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'chunk') {
                            const chunk = data.data;
                            if (chunk) {
                                if (!hasReceivedFirstChunk) {
                                    hasReceivedFirstChunk = true;
                                    stopThinkingAnimation(thinkingId);
                                    const newMsgId = createStreamingMessage(thinkingId);
                                    window.currentStreamingMsgId = newMsgId;
                                    fullResponse += chunk;
                                    updateStreamingMessage(newMsgId, fullResponse);
                                } else {
                                    fullResponse += chunk;
                                    if (window.currentStreamingMsgId) {
                                        updateStreamingMessage(window.currentStreamingMsgId, fullResponse);
                                    }
                                }
                                if (autoScroll) scrollToBottom();
                            }
                        } else if (data.type === 'session') {
                            if (data.data.session_id && data.data.session_id !== currentSessionId) {
                                currentSessionId = data.data.session_id;
                                sessionIdDisplay.textContent = `会话: ${currentSessionId.slice(0, 8)}...`;
                            }
                        } else if (data.type === 'error') {
                            hasError = true;
                            fullResponse = `错误: ${data.data}`;
                            if (hasReceivedFirstChunk && window.currentStreamingMsgId) {
                                updateStreamingMessage(window.currentStreamingMsgId, fullResponse);
                            } else {
                                replaceThinkingWithContent(thinkingId, fullResponse);
                            }
                        } else if (data.type === 'complete') {
                            console.log('Stream complete', data);
                        }
                    } catch (e) {
                        console.warn('解析 SSE 数据失败:', e, line);
                    }
                }
            }
        }

        if (!hasReceivedFirstChunk && !hasError) {
            replaceThinkingWithContent(thinkingId, '收到空响应，请稍后重试。');
        }

        if (!hasError && fullResponse && !fullResponse.startsWith('错误:')) {
            chatHistory.push({ role: 'user', content: message });
            chatHistory.push({ role: 'assistant', content: fullResponse });
            saveChatHistoryToStorage();
            updateHistoryList();
        }

    } catch (error) {
        console.error('流式请求失败:', error);
        if (hasReceivedFirstChunk && window.currentStreamingMsgId) {
            updateStreamingMessage(window.currentStreamingMsgId, `网络错误: ${error.message}`);
        } else {
            replaceThinkingWithContent(thinkingId, `网络错误: ${error.message}`);
        }
    }
}

function renderMessages() {
    if (!messagesArea) return;

    if (chatHistory.length === 0) {
        messagesArea.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <i class="fas fa-robot"></i>
                </div>
                <h2>你好！我是 AI Agent</h2>
                <p>我可以帮你回答问题、搜索知识、处理任务。试试问我：</p>
                <div class="suggestion-chips">
                    <button class="suggestion-chip" data-msg="现在几点了？">
                        <i class="fas fa-clock"></i> 现在几点了？
                    </button>
                    <button class="suggestion-chip" data-msg="介绍一下 RAG 技术">
                        <i class="fas fa-brain"></i> 介绍一下 RAG 技术
                    </button>
                    <button class="suggestion-chip" data-msg="如何排查 CPU 告警问题？">
                        <i class="fas fa-chart-line"></i> 如何排查 CPU 告警？
                    </button>
                    <button class="suggestion-chip" data-msg="知识库里有什么内容？">
                        <i class="fas fa-database"></i> 知识库里有什么？
                    </button>
                </div>
            </div>
        `;
        return;
    }

    messagesArea.innerHTML = '';
    chatHistory.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.role}`;
        const avatar = msg.role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        const formattedContent = formatMarkdown(msg.content);

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${formattedContent}</div>
                <div class="message-meta">${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        messagesArea.appendChild(messageDiv);
    });

    scrollToBottom();
}

function scrollToBottom() {
    if (autoScroll && messagesArea) {
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }
}

function updateCharCount() {
    const count = messageInput.value.length;
    charCountSpan.textContent = `${count} 字符`;
}

function setupAutoResize() {
    messageInput.addEventListener('input', () => {
        updateCharCount();
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
    });
}

// ========== 知识库模态框 ==========

async function openKnowledgeModal() {
    const modal = document.getElementById('knowledgeModal');
    if (modal) modal.classList.add('active');

    await loadKnowledgeStats();

    const addBtn = document.getElementById('addKnowledgeBtn');
    const searchBtn = document.getElementById('searchKnowledgeBtn');

    if (addBtn) {
        addBtn.onclick = addKnowledge;
    }
    if (searchBtn) {
        searchBtn.onclick = searchKnowledge;
    }
}

async function loadKnowledgeStats() {
    try {
        const response = await fetch(`${API_BASE}/knowledge/stats`);
        if (response.ok) {
            const data = await response.json();
            const docCountSpan = document.getElementById('docCount');
            if (docCountSpan) {
                const match = data.message?.match(/\d+/);
                docCountSpan.textContent = match ? match[0] : '0';
            }
        }
    } catch (error) {
        console.error('加载知识库统计失败:', error);
    }
}

async function addKnowledge() {
    const content = document.getElementById('knowledgeContent')?.value.trim();
    const category = document.getElementById('knowledgeCategory')?.value.trim() || 'general';

    if (!content) {
        showToast('请输入知识内容', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/knowledge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, category })
        });

        if (response.ok) {
            const data = await response.json();
            showToast(data.message, data.success ? 'success' : 'error');
            if (data.success) {
                const textarea = document.getElementById('knowledgeContent');
                if (textarea) textarea.value = '';
                await loadKnowledgeStats();
            }
        } else {
            showToast('添加失败: HTTP ' + response.status, 'error');
        }
    } catch (error) {
        showToast('添加失败: ' + error.message, 'error');
    }
}

async function searchKnowledge() {
    const query = document.getElementById('knowledgeQuery')?.value.trim();
    if (!query) return;

    const resultsDiv = document.getElementById('knowledgeResults');
    if (resultsDiv) resultsDiv.innerHTML = '<div class="loading">搜索中...</div>';

    try {
        const response = await fetch(`${API_BASE}/knowledge/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, top_k: 5 })
        });

        if (response.ok && resultsDiv) {
            const data = await response.json();
            if (data.success && data.message) {
                resultsDiv.innerHTML = `<div class="knowledge-result-item">
                    <div class="content">${escapeHtml(data.message)}</div>
                </div>`;
            } else {
                resultsDiv.innerHTML = `<div class="knowledge-result-item">${escapeHtml(data.message || '无结果')}</div>`;
            }
        } else if (resultsDiv) {
            resultsDiv.innerHTML = '<div class="knowledge-result-item">搜索失败</div>';
        }
    } catch (error) {
        if (resultsDiv) {
            resultsDiv.innerHTML = `<div class="knowledge-result-item">搜索失败: ${escapeHtml(error.message)}</div>`;
        }
    }
}

// ========== 状态模态框 ==========

async function openStatsModal() {
    const modal = document.getElementById('statsModal');
    if (modal) modal.classList.add('active');

    try {
        const [statusRes, memoryRes, toolsRes] = await Promise.all([
            fetch(`${API_BASE}/status`),
            fetch(`${API_BASE}/memory/stats`),
            fetch(`${API_BASE}/tools`)
        ]);

        if (statusRes.ok) {
            const status = await statusRes.json();
            const initStatusSpan = document.getElementById('initStatus');
            if (initStatusSpan) {
                initStatusSpan.innerHTML = status.initialized ?
                    '<span style="color: #10b981">✅ 已初始化</span>' :
                    '<span style="color: #ef4444">❌ 未初始化</span>';
            }
            const statSessionSpan = document.getElementById('statSessionId');
            if (statSessionSpan) statSessionSpan.textContent = status.session_id?.slice(0, 12) + '...' || '--';
            const toolCountSpan = document.getElementById('toolCount');
            if (toolCountSpan) toolCountSpan.textContent = status.tools?.length || 0;
        }

        if (memoryRes.ok) {
            const memory = await memoryRes.json();
            const shortTermSpan = document.getElementById('shortTermCount');
            const workingSpan = document.getElementById('workingCount');
            const longTermSpan = document.getElementById('longTermCount');
            if (shortTermSpan) shortTermSpan.textContent = memory.short_term || 0;
            if (workingSpan) workingSpan.textContent = memory.working || 0;
            if (longTermSpan) longTermSpan.textContent = memory.long_term || 0;
        }

        if (toolsRes.ok) {
            const tools = await toolsRes.json();
            const toolsContainer = document.getElementById('toolsContainer');
            if (toolsContainer) {
                if (tools.tools && tools.tools.length > 0) {
                    toolsContainer.innerHTML = tools.tools.map(tool =>
                        `<span class="tool-badge">${escapeHtml(tool)}</span>`
                    ).join('');
                } else {
                    toolsContainer.innerHTML = '<span style="color: #64748b">暂无工具</span>';
                }
            }
        }
    } catch (error) {
        console.error('加载状态失败:', error);
        showToast('加载状态失败', 'error');
    }
}

function openSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.add('active');

    const testBtn = document.getElementById('testConnectionBtn');
    if (testBtn) {
        testBtn.onclick = async () => {
            try {
                const response = await fetch(`${API_BASE}/health`);
                if (response.ok) {
                    showToast('连接成功', 'success');
                } else {
                    showToast('连接失败', 'error');
                }
            } catch (error) {
                showToast('连接失败: ' + error.message, 'error');
            }
        };
    }
}

// ========== Toast 通知 ==========

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${escapeHtml(message)}</span>
    `;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#6366f1'};
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 0.85rem;
        z-index: 2000;
        display: flex;
        align-items: center;
        gap: 8px;
        animation: fadeIn 0.3s ease;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}