const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function appendMessage(role, text) {
  const msg = document.createElement("div");
  msg.classList.add("message", role === "user" ? "user" : "assistant");

  const bubble = document.createElement("div");
  bubble.classList.add("bubble");
  bubble.textContent = text;

  msg.appendChild(bubble);
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendQuestion() {
  const question = userInput.value.trim();
  if (!question) return;

  appendMessage("user", question);
  userInput.value = "";

  appendMessage("assistant", "Searching for relevant information...");

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question: question }),
    });

    const data = await res.json();
    // remove the previous loading message
    const lastMsg = chatWindow.lastElementChild;
    if (lastMsg && lastMsg.classList.contains("assistant")) {
      chatWindow.removeChild(lastMsg);
    }

    if (data.error) {
      appendMessage("assistant", "Error: " + data.error);
      return;
    }

    appendMessage("assistant", data.answer);
  } catch (err) {
    const lastMsg = chatWindow.lastElementChild;
    if (lastMsg && lastMsg.classList.contains("assistant")) {
      chatWindow.removeChild(lastMsg);
    }
    appendMessage("assistant", "Request failed — please try again later");
  }
}

sendBtn.addEventListener("click", sendQuestion);
userInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    sendQuestion();
  }
});
