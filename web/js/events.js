// web/js/events.js - 完整版（已删除行业研究专题相关代码）

/**
 * 键盘事件处理
 */
function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

/**
 * 设置所有事件监听器
 */
function setupEventListeners() {
    // 主要按钮
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (messageInput) messageInput.addEventListener('keydown', handleKeydown);
    if (newChatBtn) newChatBtn.addEventListener('click', handleNewChat);
    if (clearAllBtn) clearAllBtn.addEventListener('click', clearAllSessions);
    if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
    if (menuBtn) menuBtn.addEventListener('click', toggleMobileSidebar);
    if (copySessionBtn) copySessionBtn.addEventListener('click', copySessionId);
    if (knowledgeBtn) knowledgeBtn.addEventListener('click', openKnowledgeModal);
    if (statsBtn) statsBtn.addEventListener('click', openStatsModal);
    if (settingsBtn) settingsBtn.addEventListener('click', openSettingsModal);

    // 登出按钮
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('确定要退出登录吗？')) {
                localStorage.removeItem('agent_token');
                localStorage.removeItem('agent_user_id');
                localStorage.removeItem('agent_username');
                localStorage.removeItem('agent_current_session_id');
                localStorage.removeItem('sessions');
                localStorage.removeItem('industry_mode');
                localStorage.removeItem('search_mode');
                localStorage.removeItem('expert_mode');

                if (window.sessionFirstMessages) {
                    window.sessionFirstMessages = {};
                }

                window.location.href = '/login.html';
            }
        });
    }

    // 设置开关
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

    // 快捷提问 - 追加到输入框末尾，不直接发送
    document.addEventListener('click', (e) => {
        const chip = e.target.closest('.suggestion-chip');
        if (chip) {
            const msg = chip.dataset.msg;
            if (msg && messageInput) {
                const currentValue = messageInput.value;

                // 直接追加到末尾
                if (currentValue === '') {
                    // 输入框为空，直接填充
                    messageInput.value = msg;
                } else {
                    // 已有内容，追加换行和消息
                    messageInput.value = currentValue + '\n' + msg;
                }

                // 更新字符计数
                if (typeof updateCharCount === 'function') {
                    updateCharCount();
                }

                // 调整输入框高度
                messageInput.style.height = 'auto';
                messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';

                // 聚焦输入框
                messageInput.focus();

                // 将光标移到末尾
                messageInput.selectionStart = messageInput.selectionEnd = messageInput.value.length;

                // 显示提示
                if (typeof showToast === 'function') {
                    showToast('消息已添加到输入框，按 Enter 发送', 'success');
                }
            }
        }
    });

    // 模态框关闭
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', closeAllModals);
    });

    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    document.addEventListener('click', (e) => {
        if (e.target.classList && e.target.classList.contains('modal')) {
            e.target.classList.remove('active');
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });

    // 知识库搜索按钮
    if (knowledgeSearchBtn) {
        knowledgeSearchBtn.addEventListener('click', () => {
            if (isExpertMode || isIndustryMode) {
                showToast(isExpertMode ? '专家模式下，搜索将由 AI 自动决策' : '行业研究模式下，搜索将由 AI 自动决策', 'info');
                return;
            }

            if (currentSearchMode === SearchMode.KNOWLEDGE) {
                currentSearchMode = SearchMode.NONE;
            } else {
                currentSearchMode = SearchMode.KNOWLEDGE;
                if (webSearchBtn && webSearchBtn.classList.contains('active')) {
                    webSearchBtn.classList.remove('active');
                }
            }
            updateModeButtons();
            saveModeSettings();
            showToast(currentSearchMode === SearchMode.KNOWLEDGE ? '✅ 知识库搜索已开启，联网搜索已关闭' : '知识库搜索已关闭', 'info');
        });
    }

    // 联网搜索按钮
    if (webSearchBtn) {
        webSearchBtn.addEventListener('click', () => {
            if (isExpertMode || isIndustryMode) {
                showToast(isExpertMode ? '专家模式下，搜索将由 AI 自动决策' : '行业研究模式下，搜索将由 AI 自动决策', 'info');
                return;
            }

            if (currentSearchMode === SearchMode.WEB) {
                currentSearchMode = SearchMode.NONE;
            } else {
                currentSearchMode = SearchMode.WEB;
                if (knowledgeSearchBtn && knowledgeSearchBtn.classList.contains('active')) {
                    knowledgeSearchBtn.classList.remove('active');
                }
            }
            updateModeButtons();
            saveModeSettings();
            showToast(currentSearchMode === SearchMode.WEB ? '🌐 联网搜索已开启，知识库搜索已关闭' : '联网搜索已关闭', 'info');
        });
    }

    // 专家模式按钮
    if (expertModeBtn) {
        expertModeBtn.addEventListener('click', () => {
            if (isIndustryMode) {
                // 如果行业研究模式已开启，先关闭它
                if (industryModeBtn) {
                    industryModeBtn.classList.remove('active');
                }
                isIndustryMode = false;
            }

            isExpertMode = !isExpertMode;
            updateModeButtons();
            saveModeSettings();

            if (isExpertMode) {
                showToast('🧠 专家模式已开启，AI 将自主决定是否使用知识库和联网搜索', 'success');
            } else {
                showToast('专家模式已关闭，搜索模式恢复为手动选择', 'info');
            }
        });
    }

    // 行业研究模式按钮
    if (industryModeBtn) {
        industryModeBtn.addEventListener('click', () => {
            if (isExpertMode) {
                // 如果专家模式已开启，先关闭它
                if (expertModeBtn) {
                    expertModeBtn.classList.remove('active');
                }
                isExpertMode = false;
            }

            isIndustryMode = !isIndustryMode;

            if (isIndustryMode) {
                currentSearchMode = IndustryConfig.defaultSearchMode;
                showToast('📊 行业研究模式已开启，将使用知识图谱增强检索', 'success');
            } else {
                showToast('行业研究模式已关闭', 'info');
            }

            updateModeButtons();
            saveModeSettings();
        });
    }
}