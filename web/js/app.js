// web/js/app.js - 完整版（已删除行业研究专题相关代码）

document.addEventListener('DOMContentLoaded', async () => {
    initDomElements();
    loadSettings();
    loadModeSettings();

    // 显示用户名
    const username = localStorage.getItem('agent_username');
    const userNameDisplay = document.getElementById('userNameDisplay');
    if (userNameDisplay && username) {
        userNameDisplay.textContent = username;
    } else if (userNameDisplay) {
        userNameDisplay.textContent = '用户';
    }

    // 初始化会话
    await initSession();
    await checkHealth();
    setupEventListeners();
    setupAutoResize();
});