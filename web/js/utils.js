// utils.js - 工具函数

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
 * Toast 通知
 */
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

/**
 * 生成会话 ID
 */
function generateSessionId() {
    return 'local_' + Math.random().toString(36).substring(2, 10);
}

/**
 * 滚动到底部
 */
function scrollToBottom() {
    if (autoScroll && messagesArea) {
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }
}

/**
 * 更新字符计数
 */
function updateCharCount() {
    const count = messageInput.value.length;
    if (charCountSpan) charCountSpan.textContent = `${count} 字符`;
}

/**
 * 设置输入框自动调整高度
 */
function setupAutoResize() {
    messageInput.addEventListener('input', () => {
        updateCharCount();
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
    });
}