// UofT Assistant - 前端 JavaScript

// ========================================
// 配置（从后端动态获取）
// ========================================
let API_BASE_URL = '';  // 将从 /api/config 动态获取

// ========================================
// 🚀 部署到 AWS 时取消下面一行注释，并与后端 .env 保持一致：
// ========================================
// const API_KEY = 'uoft-assistant-public-2024';

// ========================================
// 对话历史记录
// ========================================
let conversationHistory = [];

// DOM 元素引用
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// ========================================
// 配置加载函数
// ========================================

// 从后端获取配置
async function loadConfig() {
    try {
        // 首次调用使用相对路径（自动使用当前域名）
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error('Failed to load config');
        }
        const config = await response.json();
        API_BASE_URL = config.api_base_url;
        console.log('Loaded API config:', API_BASE_URL);
    } catch (error) {
        console.error('Failed to load config, using fallback:', error);
        // 降级：使用当前页面的 origin 作为 API 基础 URL
        API_BASE_URL = window.location.origin;
        console.log('Fallback API URL:', API_BASE_URL);
    }
}

// ========================================
// 历史记录管理函数
// ========================================

// 从 localStorage 加载历史记录
function loadChatHistory() {
    const saved = localStorage.getItem('uoft-chat-history');
    if (saved) {
        try {
            conversationHistory = JSON.parse(saved);
            // 恢复历史消息到界面
            conversationHistory.forEach(msg => {
                addMessage(msg.question, 'user', false); // false = 不保存
                addMessage(msg.answer, 'ai', false);
            });
            console.log(`Loaded ${conversationHistory.length} messages from history`);
        } catch (e) {
            console.error('Failed to load chat history:', e);
            conversationHistory = [];
        }
    }
}

// 保存对话到 localStorage
function saveChatHistory(question, answer) {
    conversationHistory.push({
        question: question,
        answer: answer,
        timestamp: new Date().toISOString()
    });
    localStorage.setItem('uoft-chat-history', JSON.stringify(conversationHistory));
}

// 清空对话历史
function clearChatHistory() {
    if (confirm('Clear all the Chat history？')) {
        conversationHistory = [];
        localStorage.removeItem('uoft-chat-history');
        chatBox.innerHTML = '<div class="message ai">Hello! I\'m your AI Assistant. Ask me anything about the syllabus!</div>';
        console.log('Chat history cleared');
    }
}

// 处理回车键发送
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// 添加消息到界面
function addMessage(text, sender, save = true) {
    const div = document.createElement('div');
    div.classList.add('message', sender);
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight; // 自动滚动到底部

    // 注意：实际保存由 sendMessage 中完成，这里的 save 参数用于防止重复保存
}

// 发送消息的主逻辑
async function sendMessage() {
    const question = userInput.value.trim();
    if (!question) return;

    // 1. 显示用户问题
    addMessage(question, 'user');
    userInput.value = '';

    // 2. 禁用按钮，显示加载中
    sendBtn.disabled = true;
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.innerText = 'AI is thinking...';
    chatBox.appendChild(loadingDiv);

    try {
        // 3. 调用后端 FastAPI 接口
        console.log('Sending question:', question);
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // ========================================
                // 🚀 部署到 AWS 时取消下面一行注释：
                // ========================================
                // 'Authorization': `Bearer ${API_KEY}`
            },
            body: JSON.stringify({ question: question })
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            console.error('Error response:', errorData);

            if (response.status === 401) {
                throw new Error('认证失败：API 密钥无效');
            } else if (response.status === 429) {
                throw new Error('请求过于频繁，请稍后再试');
            } else if (response.status === 503) {
                throw new Error('服务暂时不可用，请稍后重试');
            } else {
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
        }

        const data = await response.json();
        console.log('Received data:', data);
        console.log('Answer field:', data.answer);

        // 4. 移除加载文字，显示 AI 回答
        if (loadingDiv.parentNode) {
            chatBox.removeChild(loadingDiv);
        }

        if (data && data.answer) {
            addMessage(data.answer, 'ai');
            // 保存对话到历史记录
            saveChatHistory(question, data.answer);
        } else {
            addMessage('Error: No answer received from server', 'ai');
        }

    } catch (error) {
        console.error('Error details:', error);
        if (loadingDiv.parentNode) {
            chatBox.removeChild(loadingDiv);
        }
        addMessage(`Error: ${error.message}. Check console for details.`, 'ai');
    } finally {
        sendBtn.disabled = false;
    }
}

// ========================================
// 页面加载时初始化
// ========================================
window.addEventListener('DOMContentLoaded', async () => {
    console.log('Page loaded, initializing...');

    // 1. 先加载配置
    await loadConfig();

    // 2. 再加载聊天历史
    loadChatHistory();

    console.log('Initialization complete');
});
