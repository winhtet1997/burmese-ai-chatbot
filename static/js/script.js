
document.addEventListener("DOMContentLoaded", function () {
    const chatbox = document.getElementById("chatbox");
    const userInput = document.getElementById("user-input");
    const sendButton = document.getElementById("send-button");
    const micButton = document.getElementById("mic-button");

    const sendIcon = document.getElementById("send-icon");
    const voiceIcon = document.getElementById("voice-icon");

    if (chatbox.innerHTML.trim() === '') {
        document.getElementById('introMessage').style.display = 'flex';
    }

    document.querySelectorAll(".chat-link-button").forEach(link => {
        link.addEventListener("click", (e) => {
            const href = link.getAttribute("href");

            if (href.startsWith("ALL##REDIRECT##")) {
                e.preventDefault();

                const appPostData = {
                    url: href,
                    hash: "",
                    external: "false"
                };

                if (typeof jsInterface !== "undefined" && jsInterface.exec) {
                    jsInterface.exec("moa", "deeplink", JSON.stringify(appPostData));
                } else {
                    alert("App deep link triggered: " + href); // browser fallback
                }
            }
        });
    });

    document.querySelectorAll('.suggestion').forEach(button => {
        button.addEventListener('click', () => {
            const userText = button.innerText;
            document.getElementById('introMessage').style.display = 'none';
            addMessage(userText, "user");
            sendMessage(userText);
        });
    });

    function addMessage(text, sender, options = [], link = {}) {
        if (!text || text.trim() === "") return;
        if (sender !== "user" && sender !== "bot") return;
        if (typeof text !== "string") return;

        const msg = document.createElement("div");
        msg.className = "message " + (sender === "user" ? "user-message" : "bot-message");

        if (sender === "bot") {
            const allMessages = chatbox.querySelectorAll(".bot-message");
            allMessages.forEach(botMsg => botMsg.classList.remove("no-icon"));
            const lastMsg = chatbox.querySelector(".message:last-child");
            if (lastMsg && lastMsg.classList.contains("bot-message")) {
                lastMsg.classList.add("no-icon");
            }

            const optionRegex = /\[([^\]]+)\]\((option_text|option_link):([^\)]+)\)/g;
            let extractedOptions = [];
            let match;
            let cleanedText = text;

            while ((match = optionRegex.exec(text)) !== null) {
                const optionType = match[2];
                const optionValue = match[3];
                extractedOptions.push({
                    label: match[1],
                    type: optionType,
                    value: optionValue
                });
            }

            let safeText = cleanedText
                .replace(/\*/g, '\\*')
                .replace(/#/g, '\\#')
                .replace(/(?<!\n)\n(?!\n)/g, '  \n')
                .replace(/\[([^\]]+)\]\((option_text|option_link):([^\)]+)\)/g, '');
            safeText = safeText.replace(/^\s*[-*]\s*$/gm, '');

            let botContent = marked.parse(safeText);

            if (extractedOptions.length > 0) {
                const optionsHtml = extractedOptions.map(opt => {
                    if (opt.type === "option_link") {
                        return `<a href="${opt.value}" class="chat-option-button chat-link-button" data-link="${opt.value}">${opt.label}</a>`;
                    } else {
                        return `<button class="chat-option-button" data-label="${opt.label}">${opt.label}</button>`;
                    }
                }).join('');
                botContent += `<div class="chat-options-in-message">${optionsHtml}</div>`;
            }

            msg.innerHTML = botContent;

            msg.querySelectorAll('.chat-option-button').forEach(button => {
                if (button.tagName === "BUTTON") {
                    button.addEventListener('click', () => {
                        const userText = button.dataset.label;
                        addMessage(userText, "user");
                        sendMessage(userText);
                    });
                } else if (button.tagName === "A") {
                    button.addEventListener('click', (e) => {
                        e.preventDefault();
                        const deeplink = button.dataset.link;
                        const appPostData = {
                            url: deeplink,
                            hash: "",
                            external: "false"
                        };
                        if (typeof jsInterface !== "undefined" && jsInterface.exec) {
                            jsInterface.exec("moa", "deeplink", JSON.stringify(appPostData));
                        } else {
                            alert("App deep link triggered: " + deeplink);
                        }
                    });
                }
            });

        } else {
            msg.innerText = text;
        }

        chatbox.appendChild(msg);
        setTimeout(() => {
            chatbox.scrollTop = chatbox.scrollHeight;
        }, 50);;
    }

    async function sendMessage(userText) {
        document.getElementById('introMessage').style.display = 'none';
        let text = userInput.value.trim();
        if (userText) {
            text = userText;
        } else {
            text = userInput.value.trim();
            if (text === "") return;
            addMessage(text, "user");
        }
        sendIcon.style.display = "none";
        voiceIcon.style.display = "inline";
        userInput.value = "";

        const loadingBubble = document.createElement("div");
        loadingBubble.className = "message bot-message loading";
        loadingBubble.innerHTML = `<img src="${ASSET_PATH}loading-animation.gif" class="loading-gif" alt="Loading..." />`;
        chatbox.appendChild(loadingBubble);

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            });

            const contentType = response.headers.get("content-type");

            if (contentType && contentType.includes("text/event-stream")) {
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";
                let botMsgCreated = false;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const chunks = buffer.split("\n\n");
                    buffer = chunks.pop();

                    for (const chunk of chunks) {
                        if (chunk.startsWith("data: ")) {
                            const payloadText = chunk.slice(6);
                            try {
                                const payload = JSON.parse(payloadText);
                                if (payload.response && payload.response.trim() !== "") {
                                    loadingBubble.remove();
                                    if (!botMsgCreated) {
                                        addMessage(payload.response, "bot");
                                        botMsgCreated = true;
                                    } else {
                                        appendToLastBotMessage(payload.response);
                                    }
                                }
                            } catch {
                                loadingBubble.remove();
                            }
                        }
                    }
                }
            } else {
                const text = await response.text();
                try {
                    const data = JSON.parse(text);
                    loadingBubble.remove();
                    if (data && data.reply && data.reply.trim() !== "") {
                        addMessage(data.reply, "bot", data.options || [], data.link || {});
                    }
                    setTimeout(() => {
                        chatbox.scrollTop = chatbox.scrollHeight;
                    }, 50);;
                } catch {
                    loadingBubble.remove();
                    addMessage("❌ ပြန်လာတဲ့ဖော်မတ်မှာပြဿနာရှိပါတယ်။", "bot");
                }
            }
        } catch {
            loadingBubble.remove();
            addMessage("❌ Server သို့ ချိတ်ဆက်မှု မအောင်မြင်ပါ။", "bot");
        }
    }

    function appendToLastBotMessage(text) {
        const loadingMsg = document.querySelector('.bot-message.loading');
        if (loadingMsg) loadingMsg.remove();
        const messages = document.querySelectorAll(".bot-message");
        const lastBotMessage = messages[messages.length - 1];
        if (lastBotMessage) {
            lastBotMessage.innerHTML += marked.parse(text);
            setTimeout(() => {
                chatbox.scrollTop = chatbox.scrollHeight;
            }, 50);;
        }
    }

    userInput.addEventListener("input", () => {
        sendIcon.style.display = userInput.value.trim().length > 0 ? "inline" : "none";
        voiceIcon.style.display = userInput.value.trim().length == 0 ? "inline" : "none";
    });

    sendButton.addEventListener("click", () => sendMessage());
    micButton.addEventListener("click", () => alert("Mic button pressed — you can add speech-to-text here later."));
});
