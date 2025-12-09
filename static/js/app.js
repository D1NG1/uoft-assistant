// UofT Assistant - 前端 JavaScript

// DOM 元素引用
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// 处理回车键发送
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// 添加消息到界面
function addMessage(text, sender) {
    const div = document.createElement('div');
    div.classList.add('message', sender);
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight; // 自动滚动到底部
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
        const response = await fetch('http://127.0.0.1:8000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: question })
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
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
