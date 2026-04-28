const messageEl = document.querySelector("#message");
const clientTypeEl = document.querySelector("#client-type");
const answerEl = document.querySelector("#answer");
const outputEl = document.querySelector("#json-output");
const ragHitsEl = document.querySelector("#rag-hits");
const healthDot = document.querySelector("#health-dot");
const healthText = document.querySelector("#health-text");

async function health() {
  const response = await fetch("/api/health");
  const data = await response.json();
  healthDot.classList.toggle("ok", data.status === "ok");
  healthText.textContent = `${data.model} · RAG: ${data.rag_documents}`;
}

function finalText(payload) {
  return payload.answer || payload.response_to_client || payload.customer_reply || "Ответ сформирован.";
}

function render(data) {
  answerEl.textContent = finalText(data.final.payload);
  outputEl.textContent = JSON.stringify(
    {
      classifier: data.classifier,
      files: data.files,
      final: data.final,
    },
    null,
    2,
  );
  ragHitsEl.innerHTML = "";
  for (const hit of data.rag_hits || []) {
    const node = document.createElement("article");
    node.className = "hit";
    node.innerHTML = `<strong>${hit.doc_id}: ${hit.title}</strong><p>${hit.content}</p>`;
    ragHitsEl.appendChild(node);
  }
}

async function run() {
  answerEl.textContent = "Обработка...";
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: messageEl.value,
      client_type_hint: clientTypeEl.value || null,
      attachments: [],
    }),
  });
  const data = await response.json();
  render(data);
}

document.querySelector("#send").addEventListener("click", run);
document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    messageEl.value = button.dataset.example;
    run();
  });
});

health().then(run).catch((error) => {
  healthText.textContent = error.message;
});
