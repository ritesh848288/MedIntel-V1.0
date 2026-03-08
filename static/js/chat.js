document.addEventListener('DOMContentLoaded', function () {
    const messagesArea = document.getElementById('messagesArea');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const typingIndicator = document.getElementById('typingIndicator');
    const clearChat = document.getElementById('clearChat');

    // Enable/disable send button
    messageInput.addEventListener('input', function () {
        sendBtn.disabled = !this.value.trim();
        // Auto-resize textarea
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // Send on Enter (Shift+Enter for new line)
    messageInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (this.value.trim()) sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    // Topic buttons
    document.querySelectorAll('.topic-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            messageInput.value = this.getAttribute('data-msg');
            messageInput.dispatchEvent(new Event('input'));
            sendMessage();
        });
    });

    // Clear chat
    if (clearChat) {
        clearChat.addEventListener('click', function () {
            if (confirm('Clear the chat display? (History is still saved)')) {
                messagesArea.innerHTML = '';
            }
        });
    }

    function sendMessage() {
        var msg = messageInput.value.trim();
        if (!msg) return;

        // Hide welcome message
        var welcome = messagesArea.querySelector('.welcome-msg');
        if (welcome) welcome.remove();

        // Add user message
        appendMessage(msg, 'user');

        // Clear input
        messageInput.value = '';
        messageInput.style.height = 'auto';
        sendBtn.disabled = true;

        // Show typing
        typingIndicator.classList.add('active');
        scrollToBottom();

        // Send AJAX request
        var formData = new FormData();
        formData.append('msg', msg);

        fetch('/get', { method: 'POST', body: formData })
            .then(function (res) {
                if (!res.ok) throw new Error('Server error');
                return res.text();
            })
            .then(function (answer) {
                typingIndicator.classList.remove('active');
                appendMessage(answer, 'bot');
            })
            .catch(function (err) {
                typingIndicator.classList.remove('active');
                appendMessage('Sorry, an error occurred. Please try again.', 'bot');
            });
    }

    function appendMessage(text, sender) {
        var div = document.createElement('div');
        div.className = 'message ' + sender;

        var avatar = document.createElement('div');
        avatar.className = 'msg-avatar';
        avatar.innerHTML = sender === 'user'
            ? '<i class="fas fa-user-md"></i>'
            : '<i class="fas fa-robot"></i>';

        var bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        bubble.textContent = text;

        div.appendChild(avatar);
        div.appendChild(bubble);
        messagesArea.appendChild(div);
        scrollToBottom();
    }

    function scrollToBottom() {
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }
});
