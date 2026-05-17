// web/js/message.js - 完整版（支持行业研究样式）

/**
 * 添加思考消息
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
    startThinkingAnimation(messageId);

    if (autoScroll) scrollToBottom();
    return messageId;
}

/**
 * 启动思考动画
 */
function startThinkingAnimation(messageId) {
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
 * 创建用于流式输出的消息
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
 * 添加空助手消息
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

/**
 * 添加消息到 UI
 */
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

// 渲染锁，防止重复渲染
let isRenderingMessages = false;
let lastRenderedHash = '';

/**
 * 计算消息哈希，用于检测变化
 */
function getMessagesHash(messages) {
    if (!messages || messages.length === 0) return '';
    return messages.map(m => `${m.role}:${m.content.substring(0, 50)}`).join('|');
}

/**
 * 渲染所有消息
 */
function renderMessages() {
    if (!messagesArea) return;

    // 防止重复渲染
    if (isRenderingMessages) {
        console.log('已经在渲染消息，跳过');
        return;
    }

    // 检查消息是否真的变化了
    const currentHash = getMessagesHash(chatHistory);
    if (currentHash === lastRenderedHash && chatHistory.length > 0) {
        console.log('消息未变化，跳过渲染');
        return;
    }
    lastRenderedHash = currentHash;

    isRenderingMessages = true;

    if (chatHistory.length === 0) {
        // 只有在没有消息时才显示欢迎消息
        const existingMessages = messagesArea.querySelectorAll('.message:not(.welcome-message)');
        if (existingMessages.length === 0) {
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
                        <button class="suggestion-chip industry-chip" data-msg="帮我查一下月之暗面（Moonshot AI）这家公司">
                            <i class="fas fa-building"></i> 公司查询
                        </button>
                        <button class="suggestion-chip industry-chip" data-msg="对比字节跳动的豆包和百度的文心一言">
                            <i class="fas fa-chart-simple"></i> 竞品对比
                        </button>
                        <button class="suggestion-chip industry-chip" data-msg="整理AIGC领域的融资事件">
                            <i class="fas fa-coins"></i> 融资追踪
                        </button>
                    </div>
                </div>
            `;
        }
        isRenderingMessages = false;
        return;
    }

    // 检查是否已经有相同数量的消息
    const existingCount = messagesArea.querySelectorAll('.message:not(.welcome-message)').length;
    if (existingCount === chatHistory.length) {
        console.log('消息数量相同，跳过渲染');
        isRenderingMessages = false;
        return;
    }

    // 移除欢迎消息
    const welcomeMsg = messagesArea.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }

    // 清空现有消息
    const existingMessages = messagesArea.querySelectorAll('.message');
    existingMessages.forEach(msg => msg.remove());

    // 渲染所有消息
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
    isRenderingMessages = false;
}

/**
 * 清空消息区域
 */
function clearMessagesArea() {
    if (!messagesArea) return;

    const messages = messagesArea.querySelectorAll('.message');
    messages.forEach(msg => msg.remove());

    // 重新渲染欢迎消息
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
                <button class="suggestion-chip industry-chip" data-msg="帮我查一下月之暗面（Moonshot AI）这家公司">
                    <i class="fas fa-building"></i> 公司查询
                </button>
                <button class="suggestion-chip industry-chip" data-msg="对比字节跳动的豆包和百度的文心一言">
                    <i class="fas fa-chart-simple"></i> 竞品对比
                </button>
                <button class="suggestion-chip industry-chip" data-msg="整理AIGC领域的融资事件">
                    <i class="fas fa-coins"></i> 融资追踪
                </button>
            </div>
        </div>
    `;
}

/**
 * 获取最后一条用户消息
 */
function getLastUserMessage() {
    for (let i = chatHistory.length - 1; i >= 0; i--) {
        if (chatHistory[i].role === 'user') {
            return chatHistory[i].content;
        }
    }
    return null;
}

/**
 * 获取最后一条助手消息
 */
function getLastAssistantMessage() {
    for (let i = chatHistory.length - 1; i >= 0; i--) {
        if (chatHistory[i].role === 'assistant') {
            return chatHistory[i].content;
        }
    }
    return null;
}

/**
 * 格式化 Markdown 为 HTML（增强版，支持行业研究样式）
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

    // 提取行内代码
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

    // 处理标题
    formatted = formatted.replace(/^#### (.*?)$/gm, '<h4>$1</h4>');
    formatted = formatted.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    formatted = formatted.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // 处理粗体和斜体
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 处理链接
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // ========== 行业研究专用样式增强 ==========

    // 增强表格样式
    formatted = formatted.replace(/<table>/g, '<table class="comparison-table">');

    // 检测公司信息卡片（包含公司相关关键词）
    const companyKeywords = ['**公司名称**', '**企业名称**', '**创始团队**', '**融资情况**', '**核心产品**', '**业务范围**', '**创始人**'];
    const hasCompanyCard = companyKeywords.some(kw => formatted.includes(kw));
    if (hasCompanyCard && !formatted.includes('company-card')) {
        formatted = `<div class="company-card">${formatted}</div>`;
    }

    // 检测融资信息并高亮金额
    if (formatted.includes('融资') || formatted.includes('轮次') || formatted.includes('估值')) {
        formatted = formatted.replace(/(\d+\.?\d*亿|\d+\.?\d*万|\d+亿|\d+万)\s*元/g, '<span class="amount">$&</span>');
        formatted = formatted.replace(/(\d+\.?\d*亿|\d+\.?\d*万|\d+亿|\d+万)\s*美元/g, '<span class="amount">$&</span>');
        formatted = formatted.replace(/(\d+\.?\d*亿|\d+\.?\d*万|\d+亿|\d+万)\s*人民币/g, '<span class="amount">$&</span>');
    }

    // 检测并格式化时间线（格式：YYYY-MM-DD：事件 或 YYYY年MM月DD日：事件）
    const timelinePattern1 = /\d{4}-\d{2}-\d{2}[：:]\s*[^\n]+/g;
    const timelinePattern2 = /\d{4}年\d{1,2}月\d{1,2}日[：:]\s*[^\n]+/g;

    if (timelinePattern1.test(formatted) || timelinePattern2.test(formatted)) {
        // 恢复被替换的字符串（因为 test 会消耗）
        let timelineHtml = '<div class="timeline">';
        let tempFormatted = formatted;

        // 处理 YYYY-MM-DD 格式
        tempFormatted = tempFormatted.replace(/(\d{4}-\d{2}-\d{2})[：:]\s*([^\n]+)/g, (match, date, event) => {
            return `<div class="timeline-item"><span class="timeline-date">${date}</span><span class="timeline-event">${event}</span></div>`;
        });

        // 处理 YYYY年MM月DD日 格式
        tempFormatted = tempFormatted.replace(/(\d{4}年\d{1,2}月\d{1,2}日)[：:]\s*([^\n]+)/g, (match, date, event) => {
            return `<div class="timeline-item"><span class="timeline-date">${date}</span><span class="timeline-event">${event}</span></div>`;
        });

        if (tempFormatted.includes('timeline-item')) {
            formatted = timelineHtml + tempFormatted + '</div>';
        }
    }

    // 检测推理路径（行业研究模式特有）
    if (formatted.includes('推理路径') || formatted.includes('关系路径')) {
        formatted = formatted.replace(/(推理路径[：:]\s*)([^\n]+)/g, (match, label, content) => {
            return `<div class="reasoning-path"><div class="path-title"><i class="fas fa-code-branch"></i> ${label}</div><div class="path-content">${content}</div></div>`;
        });
    }

    // 检测并高亮实体名称（公司名、人名等）
    const entityPattern = /「([^」]+)」/g;
    if (entityPattern.test(formatted)) {
        formatted = formatted.replace(/「([^」]+)」/g, '<strong class="entity-name">$1</strong>');
    }

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

    // 处理换行
    formatted = formatted.replace(/\n\n/g, '</p><p>');
    formatted = formatted.replace(/\n/g, '<br>');

    // 包装段落（避免重复包装）
    const blockElements = ['<h1', '<h2', '<h3', '<h4', '<ul', '<ol', '<table', '<div', '<pre', '<blockquote'];
    const startsWithBlock = blockElements.some(tag => formatted.trim().startsWith(tag));

    if (!startsWithBlock && !formatted.trim().startsWith('<p')) {
        formatted = `<p>${formatted}</p>`;
    }

    // 修复嵌套段落的问题
    formatted = formatted.replace(/<p><div/g, '<div');
    formatted = formatted.replace(/<\/div><\/p>/g, '</div>');
    formatted = formatted.replace(/<p><ul/g, '<ul');
    formatted = formatted.replace(/<\/ul><\/p>/g, '</ul>');
    formatted = formatted.replace(/<p><table/g, '<table');
    formatted = formatted.replace(/<\/table><\/p>/g, '</table>');

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