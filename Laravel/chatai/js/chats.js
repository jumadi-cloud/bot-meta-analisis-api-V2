// Debug functions
function debugLog(message, data = null) {
    console.log(message, data);
    const debugContent = document.getElementById('debug-content');
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${message}`;
    debugContent.innerHTML = logEntry + (data ? `<br><pre>${JSON.stringify(data, null, 2)}</pre>` : '') + '<br>' + debugContent.innerHTML;
}

document.getElementById('debug-toggle').addEventListener('click', () => {
    const panel = document.getElementById('debug-panel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
});

// Get CSRF token
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// DOM elements
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const sendText = document.getElementById('send-text');
const chatMessages = document.getElementById('chat-messages');
const typingIndicator = document.getElementById('typing-indicator');
const newChatBtn = document.getElementById('new-chat-btn');
const chatSidebar = document.getElementById('chat-sidebar');
const contextMenu = document.getElementById('context-menu');
const deleteChatBtn = document.getElementById('delete-chat');
const closeMenuBtn = document.getElementById('close-menu');
const workflowTypeSelect = document.getElementById('workflow-type');

// State
let currentSessionId = null;
let rightClickedSessionId = null;

messageInput.focus();
scrollToBottom();

// =============== FUNGSI: UPDATE TAMPILAN MODE ===============
function updateCurrentModelDisplay(workflow) {
    const modelMap = {
        'workflow1': 'Agent Meta Ads',
        'workflow2': 'Agent Google Ads',
        'workflow3': 'Agent Admin Apps'
    };
    const displayText = modelMap[workflow] || 'Agent N8N';
    document.getElementById('current-model').textContent = displayText;
}

// =============== FUNGSI: MUAT SESI BERDASARKAN WORKFLOW ===============
async function loadSessionsByWorkflow(workflow) {
    try {
        const params = new URLSearchParams();
        if (workflow) params.set('workflow', workflow);
        
        const response = await fetch(`/chat/sessions?${params.toString()}`, {
            headers: { 'Accept': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            chatSidebar.innerHTML = '';
            if (data.data.length === 0) {
                chatSidebar.innerHTML = '<p id="empty-message" class="text-sm text-gray-500 text-center py-4">Belum ada percakapan</p>';
            } else {
                data.data.forEach(session => {
                    addSessionToSidebar({
                        id: session.id,
                        title: session.title,
                        created_at: new Date(session.created_at)
                    });
                });
            }
        }
    } catch (error) {
        console.error('Gagal muat sesi:', error);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    const workflow = params.get('workflow');

    // Set dropdown dan tampilan mode sesuai URL
    if (workflow && ['workflow1', 'workflow2', 'workflow3'].includes(workflow)) {
        if (workflowTypeSelect) {
            workflowTypeSelect.value = workflow;
            updateCurrentModelDisplay(workflow);
            await loadSessionsByWorkflow(workflow);
        }
    } else {
        // Default ke workflow1 jika tidak ada
        if (workflowTypeSelect) {
            workflowTypeSelect.value = 'workflow1';
            updateCurrentModelDisplay('workflow1');
        }
        await loadSessionsByWorkflow(null);
    }

    debugLog('Page loaded with:', { sessionId, workflow });
    if (sessionId && sessionId.trim() !== '') {
        currentSessionId = sessionId.trim();
        loadChatSession(currentSessionId);
    }
});

sendBtn.addEventListener('click', sendMessage);
newChatBtn.addEventListener('click', startNewChat);
deleteChatBtn.addEventListener('click', handleDeleteChat);
closeMenuBtn.addEventListener('click', closeContextMenu);

if (workflowTypeSelect) {
    workflowTypeSelect.addEventListener('change', async () => {
        currentSessionId = null;
        showWelcomeMessage();
        updateUrl(null);
        updateCurrentModelDisplay(workflowTypeSelect.value);
        await loadSessionsByWorkflow(workflowTypeSelect.value);
    });
}

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

document.addEventListener('click', (e) => {
    const chatItem = e.target.closest('.chat-item');
    if (chatItem && contextMenu.classList.contains('hidden')) {
        const sessionId = chatItem.dataset.sessionId;
        if (sessionId && sessionId.trim() !== '') {
            currentSessionId = sessionId.trim();
            loadChatSession(currentSessionId);
        }
    }
});

document.addEventListener('contextmenu', (e) => {
    const chatItem = e.target.closest('.chat-item');
    if (chatItem) {
        e.preventDefault();
        const sessionId = chatItem.dataset.sessionId;
        if (sessionId && sessionId.trim() !== '') {
            rightClickedSessionId = sessionId.trim();
            contextMenu.style.left = `${e.pageX}px`;
            contextMenu.style.top = `${e.pageY}px`;
            contextMenu.classList.remove('hidden');
        }
    }
});

function closeContextMenu() {
    contextMenu.classList.add('hidden');
    rightClickedSessionId = null;
}

async function handleDeleteChat() {
    if (!rightClickedSessionId) {
        debugLog('Invalid rightClickedSessionId:', rightClickedSessionId);
        return;
    }

    if (!confirm('Yakin ingin menghapus chat ini? Tidak bisa dikembalikan.')) {
        closeContextMenu();
        return;
    }

    try {
        debugLog('Deleting chat session:', rightClickedSessionId);

        const response = await fetch(`/chat/${encodeURIComponent(rightClickedSessionId)}`, {
            method: 'DELETE',
            headers: {
                'X-CSRF-TOKEN': getCsrfToken(),
                'Accept': 'application/json'
            }
        });

        if (!response.ok) throw new Error('Gagal menghapus chat');

        const data = await response.json();
        if (data.success) {
            const item = document.querySelector(`[data-session-id="${rightClickedSessionId}"]`);
            if (item) item.remove();

            if (currentSessionId === rightClickedSessionId) {
                currentSessionId = null;
                showWelcomeMessage();
                updateUrl(null);
            }

            // Refresh sidebar
            const currentWorkflow = workflowTypeSelect?.value || null;
            await loadSessionsByWorkflow(currentWorkflow);

            closeContextMenu();
        }
    } catch (error) {
        debugLog('Error deleting chat:', error);
        alert('Gagal menghapus chat: ' + error.message);
        closeContextMenu();
    }
}

function scrollToBottom() {
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
}

function showTyping() {
    typingIndicator.classList.add('show');
    scrollToBottom();
}

function hideTyping() {
    typingIndicator.classList.remove('show');
}

function setLoading(loading) {
    sendBtn.disabled = loading;
    messageInput.disabled = loading;
    if (loading) {
        sendText.textContent = 'Mengirim...';
        showTyping();
    } else {
        sendText.textContent = 'Kirim';
        hideTyping(); // <-- Ini akan sembunyikan "sedang mengetik"
    }
}

function showWelcomeMessage() {
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">🤖</div>
            <p class="welcome-title">Selamat datang!</p>
            <p class="welcome-subtitle">Mulai percakapan dengan ketik pesan di bawah</p>
        </div>
    `;
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || sendBtn.disabled) return;

    debugLog('Sending message', {
        message: message.substring(0, 50) + '...',
        currentSessionId: currentSessionId,
        sessionIdType: typeof currentSessionId
    });

    appendMessage(message, 'user');
    messageInput.value = '';
    setLoading(true); // <-- Ini akan tampilkan "sedang mengetik"

    try {
        const payload = { 
            message: message,
            model: 'n8n',
            type: workflowTypeSelect?.value || 'workflow1'
        };

        if (currentSessionId && typeof currentSessionId === 'string' && currentSessionId.trim() !== '') {
            payload.session_id = currentSessionId.trim();
            debugLog('Using existing session:', currentSessionId);
        } else {
            debugLog('No existing session, backend will create new one');
        }

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken(),
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Error jaringan' }));
            throw new Error(error.message || `HTTP ${response.status}`);
        }

        const data = await response.json();
        debugLog('Response received:', data);

        if (data.success && data.data) {
            let aiResponse = '';
            if (data.data.ai_response) {
                aiResponse = data.data.ai_response;
            } else {
                throw new Error('Tidak ada respons yang valid dari AI');
            }

            appendMessage(aiResponse, 'assistant');

            if (!currentSessionId && data.data.session_id) {
                currentSessionId = String(data.data.session_id);
                debugLog('Setting new currentSessionId:', currentSessionId);
                addSessionToSidebar({
                    id: currentSessionId,
                    title: message.substring(0, 50) + (message.length > 50 ? '...' : ''),
                    created_at: new Date()
                });
                updateCurrentModelDisplay(workflowTypeSelect.value);
            }

            updateActiveChat(currentSessionId);
            updateUrl(currentSessionId);

            // ✅ Sembunyikan "sedang mengetik" setelah AI merespons
            hideTyping();
        } else {
            throw new Error('Respons tidak valid dari server');
        }
    } catch (error) {
        debugLog('Error occurred:', error);
        console.error('Error:', error);
        appendMessage(`❌ Gagal: ${error.message}`, 'assistant');
        // ✅ Juga sembunyikan jika error
        hideTyping();
    }

    setLoading(false);
    messageInput.focus();
}

function appendMessage(text, role) {
    const div = document.createElement('div');
    const isUser = role === 'user';
    div.className = `message ${isUser ? 'user' : 'assistant'}`;

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    const formattedText = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/(?<!\n)\*(?!\s)(.*?)\*(?!\w)/g, '<strong>$1</strong>')
        .replace(/^\*\s+(.*?)(?=\n|$)/gm, '<li>$1</li>')
        .replace(/(<li>.*?<\/li>)/gs, '<ul class="list-disc pl-5 my-2">$1</ul>')
        .replace(/\n(?!(\s*<li>|<\/ul>))/g, '<br>');

    messageContent.innerHTML = formattedText;
    div.appendChild(messageContent);
    chatMessages.appendChild(div);
    scrollToBottom();
}

async function loadChatSession(sessionId) {
    try {
        if (!sessionId || typeof sessionId !== 'string' || sessionId.trim() === '') {
            debugLog('Invalid sessionId provided:', sessionId);
            throw new Error('Session ID tidak valid');
        }

        const validSessionId = sessionId.trim();
        debugLog('Loading chat session:', validSessionId);

        setLoading(true);
        const response = await fetch(`/chat/${encodeURIComponent(validSessionId)}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken()
            }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        debugLog('Chat session loaded:', data);

        if (data.success && Array.isArray(data.data.messages)) {
            chatMessages.innerHTML = '';
            data.data.messages.forEach(msg => {
                appendMessage(msg.content, msg.role === 'user' ? 'user' : 'assistant');
            });
            
            currentSessionId = validSessionId;
            updateActiveChat(currentSessionId);
            updateUrl(currentSessionId);
        } else {
            throw new Error(data.error || 'Data tidak valid');
        }
    } catch (error) {
        debugLog('Error loading chat session:', error);
        console.error('Error:', error);
        appendMessage(`❌ Gagal muat: ${error.message}`, 'assistant');
    } finally {
        setLoading(false);
    }
}

async function startNewChat() {
    try {
        setLoading(true);
        currentSessionId = null;
        showWelcomeMessage();
        updateActiveChat(null);
        updateUrl(null);
    } catch (error) {
        console.error('Error:', error);
    } finally {
        setLoading(false);
        messageInput.focus();
    }
}

function updateActiveChat(sessionId) {
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
    });

    if (sessionId) {
        const activeItem = document.querySelector(`[data-session-id="${sessionId}"]`);
        if (activeItem) activeItem.classList.add('active');
    }
}

function updateUrl(sessionId) {
    const url = new URL(window.location);
    const currentWorkflow = workflowTypeSelect?.value;

    if (sessionId) {
        url.searchParams.set('session_id', sessionId);
    } else {
        url.searchParams.delete('session_id');
    }

    if (currentWorkflow) {
        url.searchParams.set('workflow', currentWorkflow);
    } else {
        url.searchParams.delete('workflow');
    }

    window.history.pushState({}, '', url);
}

function addSessionToSidebar(session) {
    const emptyMsg = document.getElementById('empty-message');
    if (emptyMsg) emptyMsg.remove();

    const now = new Date();
    const timeStr = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });

    const item = document.createElement('div');
    item.className = 'chat-item';
    item.setAttribute('data-session-id', session.id);
    item.title = session.title;

    item.innerHTML = `
        <div style="display: flex; align-items: center;">
            <div class="chat-avatar">AI</div>
            <div class="chat-content">
                <div class="chat-title">${session.title.length > 30 ? session.title.substring(0, 30) + '...' : session.title}</div>
                <div class="chat-time">${timeStr}</div>
            </div>
        </div>
    `;

    chatSidebar.insertBefore(item, chatSidebar.firstChild);
}

window.addEventListener('popstate', async () => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    const workflow = params.get('workflow');

    if (workflow && workflowTypeSelect) {
        workflowTypeSelect.value = workflow;
        updateCurrentModelDisplay(workflow);
    }

    if (sessionId && sessionId.trim() !== '') {
        currentSessionId = sessionId.trim();
        loadChatSession(currentSessionId);
    } else {
        currentSessionId = null;
        startNewChat();
        await loadSessionsByWorkflow(workflow || null);
    }
});

document.addEventListener('click', (e) => {
    if (!contextMenu.contains(e.target)) {
        closeContextMenu();
    }
});

// =============== TOGGLE SIDEBAR DI MOBILE ===============
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('-translate-x-full');
    }
}

const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
if (mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', toggleSidebar);
}

document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('mobile-menu-toggle');
    
    if (sidebar && !sidebar.contains(e.target) && menuToggle && !menuToggle.contains(e.target)) {
        sidebar.classList.add('-translate-x-full');
    }
});