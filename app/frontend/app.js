const state = {
  currentStoryId: null,
  stories: [],
};

const el = {
  storyTitle: document.getElementById("story-title"),
  storyText: document.getElementById("story-text"),
  sceneText: document.getElementById("scene-text"),
  sceneQuestion: document.getElementById("scene-question"),
  stories: document.getElementById("stories"),
  currentStory: document.getElementById("current-story"),
  sessionHint: document.getElementById("session-hint"),
  messages: document.getElementById("messages"),
  pendingUpdates: document.getElementById("pending-updates"),
  observabilitySummary: document.getElementById("observability-summary"),
  recentTraces: document.getElementById("recent-traces"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function renderStories() {
  el.stories.innerHTML = "";
  state.stories.forEach((story) => {
    const li = document.createElement("li");
    li.className = story.story_id === state.currentStoryId ? "active" : "";
    li.innerHTML = `
      <strong>${story.title}</strong><br>
      <span class="muted">confirmed fragments: ${story.confirmed_fragment_count}, chunks: ${story.total_chunk_count}, pending: ${story.pending_update_count}</span>
    `;
    li.addEventListener("click", () => selectStory(story.story_id));
    el.stories.appendChild(li);
  });
}

function renderMessage(title, payload) {
  console.groupCollapsed(`[StoryConsistencyAgent] ${title}`);
  console.log("payload", payload);
  if (payload.debug) {
    console.log("debug", payload.debug);
  }
  console.groupEnd();
  const article = document.createElement("article");
  article.className = "message";
  const extractedCounts = payload.extracted_counts || {};
  const stagedCounts = payload.staged_item_counts || {};
  const debugMessages = payload.debug?.messages || [];
  const debugJson = payload.debug ? JSON.stringify(payload.debug, null, 2) : "";
  const extracted = payload.extracted_counts
    ? `Найдено: персонажей ${extractedCounts.characters || 0}, предметов ${extractedCounts.objects || 0}, событий ${extractedCounts.events || 0}, фактов ${extractedCounts.facts || 0}, связей ${extractedCounts.relations || 0}`
    : "";
  const staged = payload.staged_update_id
    ? `Подготовлено к сохранению: персонажей ${stagedCounts.entities || 0}, событий ${stagedCounts.events || 0}, фактов ${stagedCounts.facts || 0}, связей ${stagedCounts.relations || 0}`
    : "";
  article.innerHTML = `
    <div class="meta">${title}</div>
    <div><strong class="status ${payload.status || "none"}">${payload.status || "info"}</strong> · ${payload.issue_type || "n/a"} · stop: ${payload.stop_reason || "n/a"}</div>
    <p>${payload.explanation || ""}</p>
    <div class="muted">mode: ${payload.orchestrator_mode || "n/a"} · steps: ${payload.step_count || 0}</div>
    <div class="muted">${extracted}</div>
    <div class="muted">${staged}</div>
    <div class="muted">pending update: ${payload.staged_update_id || payload.pending_update_id || "n/a"}</div>
  `;
  if (debugMessages.length) {
    const logTitle = document.createElement("div");
    logTitle.className = "meta";
    logTitle.textContent = "Лог извлечения и памяти";
    article.appendChild(logTitle);

    const list = document.createElement("ul");
    list.className = "debug-log";
    debugMessages.forEach((message) => {
      const li = document.createElement("li");
      li.textContent = message;
      list.appendChild(li);
    });
    article.appendChild(list);
  }

  if (payload.debug) {
    const details = document.createElement("details");
    details.className = "debug-details";
    details.innerHTML = `
      <summary>Показать извлечённые объекты и контекст</summary>
      <pre class="code-block">${debugJson}</pre>
    `;
    article.appendChild(details);
  }
  el.messages.prepend(article);
}

function renderPendingUpdates(story) {
  el.pendingUpdates.innerHTML = "";
  const pending = (story.pending_updates || []).filter((item) => item.status === "pending");
  if (!pending.length) {
    el.pendingUpdates.innerHTML = `<div class="muted">Нет ожидающих подтверждения обновлений.</div>`;
    return;
  }

  pending.forEach((update) => {
    const card = document.createElement("div");
    card.className = "update-card";
    card.innerHTML = `
      <strong>${update.summary}</strong>
      <div class="muted">items: ${update.item_count}</div>
      <div class="stack horizontal">
        <button class="success" data-action="confirm">Confirm</button>
        <button class="danger" data-action="reject">Reject</button>
      </div>
    `;
    card.querySelector('[data-action="confirm"]').addEventListener("click", async () => {
      await api(`/stories/${state.currentStoryId}/pending-updates/${update.id}/confirm`, { method: "POST" });
      await refreshStoryDetails();
    });
    card.querySelector('[data-action="reject"]').addEventListener("click", async () => {
      await api(`/stories/${state.currentStoryId}/pending-updates/${update.id}/reject`, { method: "POST" });
      await refreshStoryDetails();
    });
    el.pendingUpdates.appendChild(card);
  });
}

async function refreshStories() {
  const payload = await api("/stories");
  state.stories = payload.stories;
  renderStories();
}

async function refreshObservability() {
  const summary = await api("/observability/summary");
  const traces = await api("/observability/traces");
  el.observabilitySummary.textContent = JSON.stringify(summary, null, 2);
  el.recentTraces.textContent = JSON.stringify(traces.traces.slice(-3), null, 2);
}

async function selectStory(storyId) {
  state.currentStoryId = storyId;
  const story = await api(`/stories/${storyId}`);
  el.currentStory.textContent = `${story.title} · ${story.story_id.slice(0, 8)}`;
  el.sessionHint.textContent = `confirmed fragments: ${story.confirmed_fragment_count}, pending fragments: ${story.pending_fragment_count}, chunks: ${story.total_chunk_count}, memory: ${JSON.stringify(story.memory_counts)}`;
  renderPendingUpdates(story);
  await refreshStories();
  await refreshObservability();
}

async function refreshStoryDetails() {
  if (!state.currentStoryId) return;
  await selectStory(state.currentStoryId);
}

async function ingestStory() {
  const payload = await api("/stories/ingest", {
    method: "POST",
    body: JSON.stringify({ title: el.storyTitle.value, text: el.storyText.value }),
  });
  state.currentStoryId = payload.story_id;
  renderMessage("История создана", {
    explanation: `История ${payload.title} создана. Исходный текст отправлен на анализ и подготовлен к подтверждению.`,
    status: payload.initial_analysis_status,
    issue_type: "none",
    stop_reason: payload.stop_reason || "ingested",
    orchestrator_mode: payload.orchestrator_mode,
    step_count: payload.step_count,
    pending_update_id: payload.pending_update_id,
    extracted_counts: payload.extracted_counts,
    staged_item_counts: payload.staged_item_counts,
    unresolved_references: payload.unresolved_references,
    debug: payload.debug,
  });
  await refreshStories();
  await selectStory(payload.story_id);
}

async function analyzeScene() {
  if (!state.currentStoryId) {
    alert("Сначала создайте или выберите историю.");
    return;
  }
  const payload = await api(`/stories/${state.currentStoryId}/analyze`, {
    method: "POST",
    body: JSON.stringify({
      scene_text: el.sceneText.value,
      question: el.sceneQuestion.value.trim() || null,
    }),
  });
  renderMessage("Ответ агента", payload);
  await refreshStoryDetails();
}

document.getElementById("refresh-stories").addEventListener("click", refreshStories);
document.getElementById("ingest-story").addEventListener("click", ingestStory);
document.getElementById("analyze-scene").addEventListener("click", analyzeScene);

refreshStories();
refreshObservability();
