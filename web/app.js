const ROUTE_LABELS = { plan: "学习规划", schedule: "日程安排", knowledge: "知识库问答" };
const RATING_LABELS = ["需要调整", "完成较少", "基本完成", "完成良好", "完全掌握"];
const PLAN_PALETTES = [
  { accent: "#28755f", soft: "#e7f1ed" },
  { accent: "#a86a19", soft: "#fbf0df" },
  { accent: "#c35a49", soft: "#fbeae6" },
  { accent: "#376da0", soft: "#e8f0f7" },
  { accent: "#7a5b99", soft: "#f0eaf5" },
  { accent: "#52716c", soft: "#e9efed" }
];

const now = new Date();
const state = {
  activeView: "chat", plan: null, reviewTaskId: null, rating: 0,
  calendarMonth: new Date(now.getFullYear(), now.getMonth(), 1), checkins: null,
  timer: { mode: "focus", duration: 1500, remaining: 1500, running: false, endAt: null, startedAt: null, interval: null }
};
const els = {
  chat: document.getElementById("chat"), emptyState: document.getElementById("emptyState"),
  todayView: document.getElementById("todayView"), todayEmpty: document.getElementById("todayEmpty"), todayCompleted: document.getElementById("todayCompleted"), todayProgress: document.getElementById("todayProgress"),
  checkinCalendar: document.getElementById("checkinCalendar"), calendarMonth: document.getElementById("calendarMonth"), checkinBtn: document.getElementById("checkinBtn"), checkinStatus: document.getElementById("checkinStatus"), streakCount: document.getElementById("streakCount"),
  timerRing: document.getElementById("timerRing"), timerDisplay: document.getElementById("timerDisplay"), timerModeLabel: document.getElementById("timerModeLabel"), timerStateLabel: document.getElementById("timerStateLabel"), focusTaskInput: document.getElementById("focusTaskInput"), timerStartBtn: document.getElementById("timerStartBtn"), timerPauseBtn: document.getElementById("timerPauseBtn"), timerFinishBtn: document.getElementById("timerFinishBtn"), focusTodayMinutes: document.getElementById("focusTodayMinutes"),
  focusHistoryList: document.getElementById("focusHistoryList"), focusHistoryEmpty: document.getElementById("focusHistoryEmpty"), focusHistorySummary: document.getElementById("focusHistorySummary"), refreshFocusHistoryBtn: document.getElementById("refreshFocusHistoryBtn"),
  customMinutesInput: document.getElementById("customMinutesInput"), applyCustomTimeBtn: document.getElementById("applyCustomTimeBtn"), customTimeHint: document.getElementById("customTimeHint"),
  focusChart: document.getElementById("focusChart"), statTodayFocus: document.getElementById("statTodayFocus"), statWeekFocus: document.getElementById("statWeekFocus"), statCompletion: document.getElementById("statCompletion"), statStreak: document.getElementById("statStreak"), statTotalSessions: document.getElementById("statTotalSessions"), statTotalFocus: document.getElementById("statTotalFocus"), statCompletedTasks: document.getElementById("statCompletedTasks"), statAverageRating: document.getElementById("statAverageRating"), statPlanCount: document.getElementById("statPlanCount"),
  composer: document.getElementById("composer"), input: document.getElementById("input"), sendBtn: document.getElementById("sendBtn"),
  toast: document.getElementById("toast"), docList: document.getElementById("docList"), availableDocList: document.getElementById("availableDocList"), docTotal: document.getElementById("docTotal"),
  knowledgeEmpty: document.getElementById("knowledgeEmpty"), availableKnowledgeEmpty: document.getElementById("availableKnowledgeEmpty"), knowledgeStatus: document.getElementById("knowledgeStatus"), availableKnowledgeStatus: document.getElementById("availableKnowledgeStatus"), clearKnowledgeBtn: document.getElementById("clearKnowledgeBtn"),
  todayList: document.getElementById("todayList"), taskCount: document.getElementById("taskCount"), taskTotal: document.getElementById("taskTotal"),
  planMeta: document.getElementById("planMeta"), fileInput: document.getElementById("fileInput"), uploader: document.getElementById("uploader"),
  reindexBtn: document.getElementById("reindexBtn"), clearBtn: document.getElementById("clearBtn"), newChatBtn: document.getElementById("newChatBtn"),
  sidebar: document.getElementById("sidebar"), scrim: document.getElementById("scrim"),
  confirmDialog: document.getElementById("confirmDialog"), confirmTitle: document.getElementById("confirmTitle"), confirmMessage: document.getElementById("confirmMessage"), confirmActionBtn: document.getElementById("confirmActionBtn"),
  topbarHeading: document.getElementById("topbarHeading"), topbarSubtitle: document.getElementById("topbarSubtitle"),
  planView: document.getElementById("planView"), planGoal: document.getElementById("planGoal"), planPeriod: document.getElementById("planPeriod"),
  planTimeline: document.getElementById("planTimeline"), planEmpty: document.getElementById("planEmpty"), planOverview: document.getElementById("planOverview"),
  planProgressText: document.getElementById("planProgressText"), planProgressBar: document.getElementById("planProgressBar"),
  completedStat: document.getElementById("completedStat"), taskStat: document.getElementById("taskStat"), dayStat: document.getElementById("dayStat"),
  currentDayStat: document.getElementById("currentDayStat"), planProgressNav: document.getElementById("planProgressNav"),
  exportPlanBtn: document.getElementById("exportPlanBtn"), printPlanBtn: document.getElementById("printPlanBtn"),
  reviewDialog: document.getElementById("reviewDialog"), reviewForm: document.getElementById("reviewForm"),
  reviewTaskName: document.getElementById("reviewTaskName"), reviewInput: document.getElementById("reviewInput"),
  reviewError: document.getElementById("reviewError"), ratingHint: document.getElementById("ratingHint"),
  confirmReviewBtn: document.getElementById("confirmReviewBtn"),
  courseCount: document.getElementById("courseCount"), courseTotal: document.getElementById("courseTotal"),
  courseImportStatus: document.getElementById("courseImportStatus"),
  courseUrlInput: document.getElementById("courseUrlInput"), importCourseUrlBtn: document.getElementById("importCourseUrlBtn"),
  courseFileInput: document.getElementById("courseFileInput"), uploadCourseFileBtn: document.getElementById("uploadCourseFileBtn"),
  toggleCourseFormBtn: document.getElementById("toggleCourseFormBtn"), courseForm: document.getElementById("courseForm"),
  courseNameInput: document.getElementById("courseNameInput"), courseDayInput: document.getElementById("courseDayInput"),
  courseStartInput: document.getElementById("courseStartInput"), courseEndInput: document.getElementById("courseEndInput"),
  courseLocationInput: document.getElementById("courseLocationInput"), courseTeacherInput: document.getElementById("courseTeacherInput"),
  courseWeeksInput: document.getElementById("courseWeeksInput"),
  courseEmpty: document.getElementById("courseEmpty"), courseGridWrap: document.getElementById("courseGridWrap"),
  courseGridHeader: document.getElementById("courseGridHeader"), courseGridBody: document.getElementById("courseGridBody"),
  clearCoursesBtn: document.getElementById("clearCoursesBtn")
};

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
}

function cleanText(value) {
  if (typeof value !== "string" || !/[\u0080-\u00ff]/.test(value)) return value;
  const characters = Array.from(value);
  if (characters.some((character) => character.charCodeAt(0) > 255)) return value;
  try {
    const bytes = Uint8Array.from(characters, (character) => character.charCodeAt(0));
    const decoded = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return /[\u4e00-\u9fff]/.test(decoded) ? decoded : value;
  } catch (_) {
    return value;
  }
}

function showToast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("error", isError);
  els.toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => els.toast.classList.remove("show"), 2800);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = `请求失败（${response.status}）`;
    try {
      const data = await response.json();
      if (data.detail) detail = cleanText(data.detail);
    } catch (_) {
      // Keep the HTTP status when an upstream response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function formatDate(value) {
  if (!value) return "未设置";
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(parsed);
}

function planPalette(planId, fallbackIndex = 0) {
  const numericId = Number(planId);
  const paletteIndex = Number.isFinite(numericId) && numericId > 0 ? numericId - 1 : fallbackIndex;
  return PLAN_PALETTES[Math.abs(paletteIndex) % PLAN_PALETTES.length];
}

function applyPlanPalette(element, planId, fallbackIndex = 0) {
  const palette = planPalette(planId, fallbackIndex);
  element.style.setProperty("--plan-color", palette.accent);
  element.style.setProperty("--plan-soft", palette.soft);
}

function setDateAndGreeting() {
  const now = new Date();
  const hour = now.getHours();
  const greeting = hour < 6 ? "夜深了" : hour < 11 ? "早上好" : hour < 14 ? "中午好" : hour < 18 ? "下午好" : "晚上好";
  document.getElementById("greeting").textContent = `${greeting}，今天想推进什么？`;
  document.getElementById("currentDate").textContent = new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "short" }).format(now);
  document.getElementById("todayDateLabel").textContent = `${new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" }).format(now)} · 集中完成今天的任务`;
}

function scrollToBottom() { els.chat.scrollTop = els.chat.scrollHeight; }
function hideWelcome() { els.emptyState.hidden = true; }
function resizeInput() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 132)}px`;
}

function resetConversation() {
  els.chat.querySelectorAll(".msg").forEach((node) => node.remove());
  els.emptyState.hidden = false;
  els.input.value = "";
  resizeInput();
  els.input.focus();
}

function activateNav(name) {
  document.querySelectorAll("[data-nav]").forEach((item) => item.classList.toggle("active", item.dataset.nav === name));
}

function switchView(view) {
  state.activeView = view;
  document.querySelectorAll("[data-view]").forEach((node) => { node.hidden = node.dataset.view !== view; });
  activateNav(view);
  const isPlan = view === "plan";
  const headings = {
    chat: ["AI 助理", "把想法变成今天可以完成的行动"],
    today: ["今日安排", "在这里确认完成并记录学习评价"],
    focus: ["专注计时", "一次只做一件事，积累真正有效的学习时间"],
    stats: ["学习数据", "观察专注、任务和签到形成的长期趋势"],
    knowledge: ["我的知识库", "从候选文档中选择真正参与问答的资料"],
    plan: ["完整学习计划", "按计划、周和每日任务分级浏览"],
    courses: ["我的课表", "导入并查看每周课程安排"]
  };
  els.topbarHeading.textContent = headings[view][0];
  els.topbarSubtitle.textContent = headings[view][1];
  els.clearBtn.hidden = view !== "chat";
  closePanels();
  if (isPlan) loadPlan();
  if (view === "today") Promise.all([loadToday(), loadCheckins()]);
  if (view === "stats") loadStats();
  if (view === "focus") Promise.all([loadStats(), loadFocusSessions()]);
  if (view === "knowledge") loadStatus();
  if (view === "courses") loadCourses();
  else els.input.focus();
}

function createMessage(role) {
  const message = makeElement("div", `msg ${role}`);
  const avatar = makeElement("div", "avatar", role === "user" ? "我" : "知");
  const bubble = makeElement("div", "bubble");
  message.append(avatar, bubble);
  return { message, bubble };
}

function addUserMessage(text) {
  hideWelcome();
  const { message, bubble } = createMessage("user");
  bubble.textContent = text;
  els.chat.appendChild(message);
  scrollToBottom();
}

function addTyping() {
  hideWelcome();
  const { message, bubble } = createMessage("bot");
  message.id = "typingMsg";
  const typing = makeElement("div", "typing");
  typing.innerHTML = "<span></span><span></span><span></span>";
  bubble.appendChild(typing);
  els.chat.appendChild(message);
  scrollToBottom();
}

function removeTyping() { document.getElementById("typingMsg")?.remove(); }

function addBotMessage(data, elapsed) {
  const { message, bubble } = createMessage("bot");
  bubble.appendChild(makeElement("div", "route-tag", ROUTE_LABELS[data.route] || "智能助理"));
  bubble.appendChild(makeElement("div", "", cleanText(data.answer) || "暂时没有生成回复，请稍后再试。"));

  if (data.source) {
    const sources = makeElement("div", "sources");
    sources.appendChild(makeElement("h4", "", "回答来源"));
    const item = makeElement("div", "source-item");
    const sourceName = makeElement("b");
    const sourceValue = cleanText(data.source);
    const isNetwork = sourceValue === "网络";
    sourceName.textContent = isNetwork ? "网络" : "个人知识库";
    item.append(sourceName, document.createTextNode(` · ${isNetwork ? "大模型通用知识（知识库未命中）" : sourceValue}`));
    sources.appendChild(item);
    bubble.appendChild(sources);
  }

  if (Array.isArray(data.trace) && data.trace.length) {
    const details = makeElement("details", "trace");
    details.appendChild(makeElement("summary", "", `查看处理过程 · ${elapsed.toFixed(1)} 秒`));
    data.trace.forEach((step, index) => {
      const row = makeElement("div", "step");
      const body = makeElement("div");
      body.append(makeElement("div", "step-agent", cleanText(step.agent)), makeElement("div", "step-desc", cleanText(step.desc)));
      row.append(makeElement("div", "step-no", String(index + 1)), body);
      details.appendChild(row);
    });
    bubble.appendChild(details);
  }
  els.chat.appendChild(message);
  scrollToBottom();
}

function addErrorMessage(error) {
  const { message, bubble } = createMessage("bot");
  bubble.textContent = `暂时无法完成请求：${error.message}`;
  els.chat.appendChild(message);
  scrollToBottom();
}

async function sendMessage(text) {
  const message = (text || "").trim();
  if (!message || els.sendBtn.disabled) return;
  addUserMessage(message);
  els.input.value = "";
  resizeInput();
  els.sendBtn.disabled = true;
  els.input.disabled = true;
  addTyping();
  const startedAt = performance.now();
  try {
    const data = await api("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) });
    removeTyping();
    addBotMessage(data, (performance.now() - startedAt) / 1000);
    await Promise.all([loadStatus(), loadPlan(), loadCheckins()]);
  } catch (error) {
    removeTyping();
    addErrorMessage(error);
    showToast(error.message, true);
  } finally {
    els.sendBtn.disabled = false;
    els.input.disabled = false;
    els.input.focus();
  }
}

function createDocumentItem(name, imported) {
    const item = makeElement("li", "knowledge-doc-item");
    const displayName = cleanText(name);
    item.title = displayName;
    const iconWrap = makeElement("span", "knowledge-file-icon");
    const icon = document.createElement("i");
    icon.dataset.lucide = "file-text";
    iconWrap.appendChild(icon);
    const copy = makeElement("span", "knowledge-file-copy");
    copy.append(
      makeElement("strong", "", displayName),
      makeElement("small", "", `${displayName.split(".").pop().toUpperCase()} 文档 · ${imported ? "已用于知识问答" : "等待手动导入"}`)
    );
    const actions = makeElement("span", "knowledge-item-actions");
    const stateButton = makeElement("button", "secondary-btn action-btn knowledge-state-btn", imported ? "移出" : "导入");
    stateButton.type = "button";
    stateButton.title = imported ? `将 ${displayName} 移出知识库` : `将 ${displayName} 导入知识库`;
    stateButton.addEventListener("click", () => imported ? unimportDocument(name) : importDocument(name));
    const remove = makeElement("button", "icon-btn knowledge-delete-btn");
    remove.type = "button";
    remove.title = `永久删除 ${displayName}`;
    remove.setAttribute("aria-label", `永久删除 ${displayName}`);
    const removeIcon = document.createElement("i");
    removeIcon.dataset.lucide = "trash-2";
    remove.appendChild(removeIcon);
    remove.addEventListener("click", () => deleteDocument(name));
    actions.append(stateButton, remove);
    item.append(iconWrap, copy, actions);
    return item;
}

function renderDocuments(importedDocuments, availableDocuments) {
  els.docList.innerHTML = "";
  els.availableDocList.innerHTML = "";
  els.docTotal.textContent = String(importedDocuments.length);
  els.knowledgeEmpty.hidden = Boolean(importedDocuments.length);
  els.availableKnowledgeEmpty.hidden = Boolean(availableDocuments.length);
  els.clearKnowledgeBtn.disabled = !importedDocuments.length;
  els.reindexBtn.disabled = !importedDocuments.length;
  els.knowledgeStatus.textContent = importedDocuments.length
    ? `已导入 ${importedDocuments.length} 份资料，问答时会按相关性检索`
    : "当前没有文档参与知识问答";
  els.availableKnowledgeStatus.textContent = availableDocuments.length
    ? `${availableDocuments.length} 份文档等待选择，Markdown 不会自动导入`
    : "上传的文档不会自动进入知识库";
  availableDocuments.forEach((name) => els.availableDocList.appendChild(createDocumentItem(name, false)));
  importedDocuments.forEach((name) => els.docList.appendChild(createDocumentItem(name, true)));
  refreshIcons();
}

async function importDocument(name) {
  try {
    const data = await api(`/api/documents/${encodeURIComponent(name)}/import`, { method: "POST" });
    showToast(`已导入 ${cleanText(name)}，生成 ${data.chunks} 个知识片段`);
    await loadStatus();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function unimportDocument(name) {
  try {
    await api(`/api/documents/${encodeURIComponent(name)}/import`, { method: "DELETE" });
    showToast(`${cleanText(name)} 已移出知识库，源文件仍保留`);
    await loadStatus();
  } catch (error) {
    showToast(error.message, true);
  }
}

function confirmAction(title, message, actionLabel = "确认删除") {
  els.confirmTitle.textContent = title;
  els.confirmMessage.textContent = message;
  els.confirmActionBtn.textContent = actionLabel;
  els.confirmDialog.showModal();
  return new Promise((resolve) => {
    const finish = (answer) => {
      els.confirmActionBtn.removeEventListener("click", accept);
      document.getElementById("cancelConfirmBtn").removeEventListener("click", cancel);
      els.confirmDialog.removeEventListener("cancel", cancelEvent);
      if (els.confirmDialog.open) els.confirmDialog.close();
      resolve(answer);
    };
    const accept = () => finish(true);
    const cancel = () => finish(false);
    const cancelEvent = (event) => { event.preventDefault(); finish(false); };
    els.confirmActionBtn.addEventListener("click", accept);
    document.getElementById("cancelConfirmBtn").addEventListener("click", cancel);
    els.confirmDialog.addEventListener("cancel", cancelEvent);
  });
}

async function deleteDocument(name) {
  const confirmed = await confirmAction("永久删除这份文档？", `“${cleanText(name)}”的源文件和知识索引都会被删除，此操作无法撤销。`);
  if (!confirmed) return;
  try {
    await api(`/api/documents/${encodeURIComponent(name)}`, { method: "DELETE" });
    showToast(`已删除 ${cleanText(name)}`);
    await loadStatus();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function clearKnowledgeBase() {
  const confirmed = await confirmAction("清空已导入文档？", "所有文档会移出知识索引，但源文件会保留在“可导入文档”中。", "确认清空");
  if (!confirmed) return;
  els.clearKnowledgeBtn.disabled = true;
  try {
    const data = await api("/api/documents", { method: "DELETE" });
    showToast(`知识库已清空，${data.removed.length} 份文档仍可重新导入`);
    await loadStatus();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.clearKnowledgeBtn.disabled = Number(els.docTotal.textContent) === 0;
  }
}

function attachTaskToggle(checkbox, task) {
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) {
      checkbox.checked = false;
      openReview(task);
    } else {
      updateTaskStatus(task.id, false);
    }
  });
}

function renderTodayTasks(tasks, plan, followUpPlans = []) {
  els.taskCount.textContent = String(tasks.length);
  els.taskTotal.textContent = `${tasks.length} 项`;
  els.planMeta.innerHTML = "";
  const sourcePlanCount = new Set(tasks.map((task) => task.plan_id).filter(Boolean)).size;
  if (tasks.length) {
    const line = makeElement("span");
    line.append("今日任务来自 ", makeElement("strong", "", `${sourcePlanCount} 条学习计划`), document.createTextNode(" · 完成后请进行自我评价"));
    els.planMeta.appendChild(line);
  } else {
    els.planMeta.textContent = "还没有进行中的计划，可以让 AI 帮你制定。";
  }

  els.todayList.innerHTML = "";
  const completedCount = tasks.filter((task) => task.status === "completed").length;
  const continueMode = tasks.length > 0 && completedCount === tasks.length;
  els.todayCompleted.textContent = `${completedCount} 项`;
  els.todayProgress.textContent = tasks.length ? `${Math.round(completedCount * 100 / tasks.length)}%` : "0%";
  els.todayEmpty.hidden = Boolean(tasks.length);
  els.todayList.hidden = false;
  if (!tasks.length) {
    return;
  }
  const groups = new Map();
  if (continueMode) {
    const availablePlans = Array.isArray(followUpPlans) ? followUpPlans : [];
    if (!availablePlans.length) {
      const empty = makeElement("div", "today-empty continuation-empty");
      empty.append(makeElement("h2", "", "所有学习计划都已完成"), makeElement("p", "", "可以制定一个新的目标，继续保持学习节奏。"));
      els.todayList.appendChild(empty);
      return;
    }
    els.planMeta.innerHTML = "";
    const line = makeElement("span");
    line.append("今日任务已全部完成 · 下面可以继续推进 ", makeElement("strong", "", `${availablePlans.length} 条学习计划`));
    els.planMeta.appendChild(line);
    availablePlans.forEach((item) => {
      if (!item.next_task) return;
      groups.set(item.id, {
        id: item.id,
        goal: item.goal || "学习计划",
        tasks: [item.next_task],
        continuation: true
      });
    });
  } else {
    tasks.forEach((rawTask) => {
      const key = rawTask.plan_id || "default";
      if (!groups.has(key)) groups.set(key, { id: rawTask.plan_id, goal: rawTask.plan_goal || "学习计划", tasks: [], continuation: false });
      groups.get(key).tasks.push(rawTask);
    });
  }
  groups.forEach((group) => {
    const groupSection = makeElement("section", "today-task-group");
    applyPlanPalette(groupSection, group.id);
    const groupTitle = makeElement("h2", "today-group-title", cleanText(group.goal));
    if (group.continuation) groupTitle.appendChild(makeElement("span", "today-group-mode", "继续学习"));
    groupSection.appendChild(groupTitle);
    const list = makeElement("div", "today-group-list");
    group.tasks.forEach((rawTask) => {
    const task = { ...rawTask, topic: cleanText(rawTask.topic), content: cleanText(rawTask.content), review: cleanText(rawTask.review) };
    const item = makeElement("article", `today-task-card ${task.status === "completed" ? "completed" : ""}`);
    const row = makeElement("div", "today-task-row");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "mini-task-checkbox";
    checkbox.checked = task.status === "completed";
    checkbox.disabled = !task.id || task.status === "completed";
    checkbox.setAttribute("aria-label", `${checkbox.checked ? "已完成" : "完成并评价"}：${task.topic}`);
    if (!checkbox.disabled) attachTaskToggle(checkbox, task);
    const copy = makeElement("div", "today-task-copy");
    copy.append(makeElement("span", "today-task-day", `DAY ${task.day}`), makeElement("span", "topic", task.topic || `第 ${task.day} 天任务`), makeElement("span", "content", task.content || ""));
    if (task.rating) {
      const rating = makeElement("span", "mini-rating rating-readonly", `${"★".repeat(task.rating)} 已评价`);
      copy.appendChild(rating);
    }
    row.append(checkbox, copy);
    item.appendChild(row);
    list.appendChild(item);
    });
    groupSection.appendChild(list);
    els.todayList.appendChild(groupSection);
  });
}

async function loadStatus() {
  try {
    const data = await api("/api/status");
    renderDocuments(
      Array.isArray(data.imported_documents) ? data.imported_documents : (Array.isArray(data.documents) ? data.documents : []),
      Array.isArray(data.available_documents) ? data.available_documents : []
    );
    renderTodayTasks(Array.isArray(data.today_tasks) ? data.today_tasks : [], data.plan || {}, data.follow_up_plans || []);
    refreshIcons();
  } catch (error) {
    els.planMeta.textContent = "暂时无法读取今日安排";
    showToast(`状态加载失败：${error.message}`, true);
  }
}

async function loadToday() {
  try {
    const data = await api("/api/status");
    renderTodayTasks(Array.isArray(data.today_tasks) ? data.today_tasks : [], data.plan || {}, data.follow_up_plans || []);
    refreshIcons();
  } catch (error) {
    showToast(`今日安排加载失败：${error.message}`, true);
  }
}

function calendarMonthKey() {
  const year = state.calendarMonth.getFullYear();
  const month = String(state.calendarMonth.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function renderCheckinCalendar(data) {
  state.checkins = data;
  const year = state.calendarMonth.getFullYear();
  const monthIndex = state.calendarMonth.getMonth();
  els.calendarMonth.textContent = new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long" }).format(state.calendarMonth);
  els.streakCount.textContent = String(data.streak || 0);
  const checkedDates = new Set((data.records || []).map((record) => record.checkin_date));
  const firstOffset = (new Date(year, monthIndex, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
  els.checkinCalendar.innerHTML = "";
  for (let index = 0; index < firstOffset; index += 1) {
    els.checkinCalendar.appendChild(makeElement("span", "calendar-day placeholder"));
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateValue = `${year}-${String(monthIndex + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const classes = ["calendar-day"];
    if (dateValue === data.today) classes.push("today");
    if (checkedDates.has(dateValue)) classes.push("checked");
    const cell = makeElement("span", classes.join(" "), String(day));
    if (checkedDates.has(dateValue)) {
      const mark = document.createElement("i");
      mark.dataset.lucide = "check";
      cell.appendChild(mark);
      cell.title = `${dateValue} 已签到`;
    }
    els.checkinCalendar.appendChild(cell);
  }
  els.checkinBtn.disabled = !data.eligible || data.today_checked;
  const label = els.checkinBtn.querySelector("span");
  if (data.today_checked) {
    label.textContent = "今日已签到";
    els.checkinStatus.textContent = `今天已完成签到 · 连续 ${data.streak || 0} 天`;
  } else if (data.eligible) {
    label.textContent = "完成今日签到";
    els.checkinStatus.textContent = "今日任务已全部完成，可以签到";
  } else {
    label.textContent = "完成全部任务后签到";
    els.checkinStatus.textContent = `今日已完成 ${data.today_completed || 0}/${data.today_total || 0} 项任务`;
  }
  refreshIcons();
}

async function loadCheckins() {
  try {
    renderCheckinCalendar(await api(`/api/checkins?month=${calendarMonthKey()}`));
  } catch (error) {
    els.checkinStatus.textContent = "签到日历暂时无法加载";
    if (state.activeView === "today") showToast(`签到加载失败：${error.message}`, true);
  }
}

function formatTimer(seconds) {
  const value = Math.max(0, Math.round(seconds));
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
}

function persistTimer() {
  const timer = state.timer;
  localStorage.setItem("zhixu-focus-timer", JSON.stringify({
    mode: timer.mode, duration: timer.duration, remaining: timer.remaining,
    running: timer.running, endAt: timer.endAt, startedAt: timer.startedAt,
    taskName: els.focusTaskInput.value
  }));
}

function updateTimerUI() {
  const timer = state.timer;
  const elapsed = Math.max(0, timer.duration - timer.remaining);
  const progress = timer.duration ? elapsed * 100 / timer.duration : 0;
  els.timerRing.style.setProperty("--timer-progress", `${progress}%`);
  els.timerDisplay.textContent = formatTimer(timer.remaining);
  els.timerModeLabel.textContent = timer.mode === "break" ? "休息时间" : "专注时间";
  els.timerStateLabel.textContent = timer.running ? "正在计时" : elapsed > 0 ? "已暂停" : "准备开始";
  els.timerStartBtn.querySelector("span").textContent = timer.running ? "专注中" : elapsed > 0 ? "继续专注" : timer.mode === "break" ? "开始休息" : "开始专注";
  els.timerStartBtn.disabled = timer.running;
  els.timerPauseBtn.disabled = !timer.running;
  els.timerFinishBtn.disabled = elapsed < 60;
  document.querySelectorAll("[data-focus-minutes]").forEach((button) => {
    button.disabled = timer.running || elapsed > 0;
    button.classList.toggle("active", Number(button.dataset.focusMinutes) * 60 === timer.duration && button.dataset.focusMode === timer.mode);
  });
  els.customMinutesInput.disabled = timer.running || elapsed > 0;
  els.applyCustomTimeBtn.disabled = timer.running || elapsed > 0;
  els.customTimeHint.textContent = timer.mode === "break"
    ? `当前使用 ${Math.round(timer.duration / 60)} 分钟休息`
    : `当前使用 ${Math.round(timer.duration / 60)} 分钟专注`;
}

function clearTimerInterval() {
  if (state.timer.interval) clearInterval(state.timer.interval);
  state.timer.interval = null;
}

async function recordFocusSession(completed) {
  const timer = state.timer;
  const elapsed = Math.max(1, timer.duration - timer.remaining);
  clearTimerInterval();
  try {
    await api("/api/focus-sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        duration_seconds: elapsed, task_name: els.focusTaskInput.value.trim(),
        mode: timer.mode, completed, started_at: timer.startedAt
      })
    });
    showToast(timer.mode === "break" ? "休息记录已保存" : `已记录 ${Math.round(elapsed / 60)} 分钟专注`);
    resetTimer(false);
    await Promise.all([loadStats(), loadFocusSessions()]);
  } catch (error) {
    timer.running = false;
    timer.endAt = null;
    updateTimerUI();
    persistTimer();
    showToast(error.message, true);
  }
}

function tickTimer() {
  const timer = state.timer;
  if (!timer.running || !timer.endAt) return;
  timer.remaining = Math.max(0, Math.ceil((timer.endAt - Date.now()) / 1000));
  updateTimerUI();
  persistTimer();
  if (timer.remaining === 0) recordFocusSession(true);
}

function startTimer() {
  const timer = state.timer;
  if (timer.running) return;
  if (!timer.startedAt) timer.startedAt = new Date().toISOString();
  timer.running = true;
  timer.endAt = Date.now() + timer.remaining * 1000;
  clearTimerInterval();
  timer.interval = setInterval(tickTimer, 500);
  updateTimerUI();
  persistTimer();
}

function pauseTimer() {
  tickTimer();
  state.timer.running = false;
  state.timer.endAt = null;
  clearTimerInterval();
  updateTimerUI();
  persistTimer();
}

function resetTimer(clearTask = true) {
  const timer = state.timer;
  clearTimerInterval();
  timer.remaining = timer.duration;
  timer.running = false;
  timer.endAt = null;
  timer.startedAt = null;
  if (clearTask) els.focusTaskInput.value = "";
  localStorage.removeItem("zhixu-focus-timer");
  updateTimerUI();
}

function restoreTimer() {
  try {
    const saved = JSON.parse(localStorage.getItem("zhixu-focus-timer") || "null");
    if (!saved) return updateTimerUI();
    Object.assign(state.timer, {
      mode: saved.mode === "break" ? "break" : "focus",
      duration: Number(saved.duration) || 1500,
      remaining: Number(saved.remaining) || 1500,
      running: Boolean(saved.running), endAt: saved.endAt,
      startedAt: saved.startedAt || null
    });
    els.focusTaskInput.value = saved.taskName || "";
    if (![300, 1500, 3000].includes(state.timer.duration)) {
      els.customMinutesInput.value = String(Math.round(state.timer.duration / 60));
    }
    if (state.timer.running && state.timer.endAt) {
      state.timer.remaining = Math.max(0, Math.ceil((state.timer.endAt - Date.now()) / 1000));
      if (state.timer.remaining > 0) state.timer.interval = setInterval(tickTimer, 500);
      else recordFocusSession(true);
    }
  } catch (_) {
    localStorage.removeItem("zhixu-focus-timer");
  }
  updateTimerUI();
}

function applyCustomTime() {
  const minutes = Number(els.customMinutesInput.value);
  if (!Number.isInteger(minutes) || minutes < 1 || minutes > 480) {
    showToast("请输入 1–480 之间的整数分钟", true);
    els.customMinutesInput.focus();
    return;
  }
  state.timer.mode = "focus";
  state.timer.duration = minutes * 60;
  state.timer.remaining = state.timer.duration;
  state.timer.startedAt = null;
  updateTimerUI();
  persistTimer();
  showToast(`已设置 ${minutes} 分钟专注`);
}

function formatStudyDuration(seconds) {
  const minutes = Math.round(Number(seconds || 0) / 60);
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours} 小时 ${remainder} 分` : `${hours} 小时`;
}

function formatFocusMoment(value) {
  if (!value) return "时间未记录";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return cleanText(value);
  const today = new Date();
  const sameDay = parsed.getFullYear() === today.getFullYear()
    && parsed.getMonth() === today.getMonth()
    && parsed.getDate() === today.getDate();
  const time = new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(parsed);
  if (sameDay) return `今天 ${time}`;
  const date = new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(parsed);
  return `${date} ${time}`;
}

function renderFocusSessions(data) {
  const sessions = Array.isArray(data.sessions) ? data.sessions : [];
  els.focusHistoryList.innerHTML = "";
  els.focusHistoryEmpty.hidden = Boolean(sessions.length);
  if (!sessions.length) {
    els.focusHistorySummary.textContent = "还没有专注记录";
    refreshIcons();
    return;
  }
  const totalSeconds = sessions.reduce((sum, session) => sum + Number(session.duration_seconds || 0), 0);
  els.focusHistorySummary.textContent = `最近 ${sessions.length} 次 · 平均 ${formatStudyDuration(totalSeconds / sessions.length)}`;
  sessions.forEach((session, index) => {
    const item = makeElement("li", `focus-history-item ${session.completed ? "completed" : "partial"}`);
    const marker = makeElement("span", "focus-history-marker");
    marker.appendChild(makeElement("span", "", String(index + 1)));
    const copy = makeElement("div", "focus-history-copy");
    const taskName = cleanText(session.task_name) || "未填写专注事项";
    copy.append(
      makeElement("strong", session.task_name ? "" : "empty-task", taskName),
      makeElement("span", "focus-history-time", formatFocusMoment(session.started_at || session.created_at))
    );
    const meta = makeElement("div", "focus-history-meta");
    meta.append(
      makeElement("strong", "", formatStudyDuration(session.duration_seconds)),
      makeElement("span", session.completed ? "completed" : "partial", session.completed ? "按时完成" : "提前结束")
    );
    item.append(marker, copy, meta);
    els.focusHistoryList.appendChild(item);
  });
  refreshIcons();
}

async function loadFocusSessions() {
  try {
    renderFocusSessions(await api("/api/focus-sessions?limit=30"));
  } catch (error) {
    els.focusHistorySummary.textContent = "专注记录暂时无法加载";
    if (state.activeView === "focus") showToast(`专注记录加载失败：${error.message}`, true);
  }
}

function renderStats(data) {
  els.focusTodayMinutes.textContent = String(Math.round((data.today_focus_seconds || 0) / 60));
  els.statTodayFocus.textContent = formatStudyDuration(data.today_focus_seconds);
  els.statWeekFocus.textContent = formatStudyDuration(data.week_focus_seconds);
  els.statCompletion.textContent = `${data.task_completion || 0}%`;
  els.statStreak.textContent = `${data.checkin_streak || 0} 天`;
  els.statTotalSessions.textContent = `${data.total_sessions || 0} 次专注`;
  els.statTotalFocus.textContent = formatStudyDuration(data.total_focus_seconds);
  els.statCompletedTasks.textContent = String(data.completed_tasks || 0);
  els.statAverageRating.textContent = Number(data.average_rating || 0).toFixed(1);
  els.statPlanCount.textContent = String(data.plan_count || 0);
  const daily = Array.isArray(data.daily) ? data.daily : [];
  const maxSeconds = Math.max(...daily.map((item) => item.seconds || 0), 1);
  els.focusChart.innerHTML = "";
  daily.forEach((item) => {
    const column = makeElement("div", "chart-column");
    const value = makeElement("span", "chart-value", item.minutes ? `${item.minutes}m` : "0");
    const track = makeElement("div", "chart-track");
    const bar = makeElement("span", "chart-bar");
    bar.style.height = `${Math.max(item.seconds ? 8 : 0, item.seconds * 100 / maxSeconds)}%`;
    bar.title = `${item.date} · ${item.minutes} 分钟 · ${item.sessions} 次`;
    track.appendChild(bar);
    column.append(value, track, makeElement("span", "chart-label", item.label));
    els.focusChart.appendChild(column);
  });
}

async function loadStats() {
  try {
    renderStats(await api("/api/stats"));
  } catch (error) {
    if (state.activeView === "stats" || state.activeView === "focus") showToast(`学习数据加载失败：${error.message}`, true);
  }
}

function taskState(task, currentDay) {
  if (task.status === "completed") return { key: "completed", label: "已完成", className: "done" };
  if (task.day === currentDay) return { key: "today", label: "今日进行中", className: "" };
  if (currentDay > 0 && task.day < currentDay) return { key: "overdue", label: "待补做", className: "late" };
  return { key: "upcoming", label: "未开始", className: "" };
}

function buildPlanTask(rawTask, currentDay) {
  const task = { ...rawTask, topic: cleanText(rawTask.topic), content: cleanText(rawTask.content), review: cleanText(rawTask.review) };
  const status = taskState(task, currentDay);
  const article = makeElement("article", `plan-task ${status.key}`);
  const detail = makeElement("details", "plan-task-detail");
  if (task.day === currentDay) detail.open = true;
  const summary = document.createElement("summary");
  const day = makeElement("span", "task-day", `DAY ${task.day}`);
  const heading = makeElement("span", "task-heading");
  heading.append(makeElement("strong", "", task.topic), makeElement("span", "", formatDate(task.scheduled_date)));
  summary.append(day, heading, makeElement("span", `task-status ${status.className}`, status.label));
  detail.append(summary, makeElement("p", "task-description", task.content));

  if (task.status === "completed") {
    const review = makeElement("div", "task-review");
    const reviewCopy = makeElement("div", "review-summary");
    reviewCopy.append(makeElement("strong", "", "★".repeat(task.rating || 0)), document.createElement("br"), document.createTextNode(task.review || RATING_LABELS[(task.rating || 1) - 1]));
    const editReview = makeElement("button", "edit-review-btn", "修改评价");
    editReview.type = "button";
    editReview.addEventListener("click", () => openReview(task));
    review.append(reviewCopy, editReview);
    detail.appendChild(review);
  }
  article.append(detail);
  return article;
}

async function deleteLearningPlan(planId, goal) {
  const confirmed = await confirmAction(
    "删除这条学习计划？",
    `“${cleanText(goal) || "未命名计划"}”及其全部任务和评价都会被永久删除，此操作无法撤销。`,
    "确认删除计划"
  );
  if (!confirmed) return;
  try {
    await api(`/api/plans/${planId}`, { method: "DELETE" });
    showToast(`已删除学习计划：${cleanText(goal) || "未命名计划"}`);
    await Promise.all([loadPlan(), loadStatus(), loadCheckins(), loadStats()]);
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderPlan(plan) {
  state.plan = plan;
  const plans = Array.isArray(plan.plans) ? plan.plans : [];
  const progress = Number(plan.progress || 0);
  els.planProgressNav.textContent = String(plans.length);
  els.planGoal.textContent = "全部学习计划";
  els.planPeriod.textContent = plans.length ? `${plans.length} 条计划 · 按计划、周和每日任务分级浏览` : "尚未制定计划";
  els.planProgressText.textContent = `${progress}%`;
  els.planProgressBar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
  els.completedStat.textContent = String(plan.completed_tasks || 0);
  els.taskStat.textContent = String(plan.total_tasks || 0);
  els.dayStat.textContent = String(plans.length);
  els.currentDayStat.textContent = String(plans.filter((item) => item.current_day > 0 && item.current_day <= item.total_days).length);
  els.planTimeline.innerHTML = "";

  const hasPlan = plans.length > 0;
  els.planEmpty.hidden = hasPlan;
  els.planOverview.hidden = !hasPlan;
  els.exportPlanBtn.disabled = !hasPlan;
  els.printPlanBtn.disabled = !hasPlan;
  if (!hasPlan) { refreshIcons(); return; }

  plans.forEach((rawPlan, planIndex) => {
    const planItem = makeElement("details", "plan-directory");
    planItem.dataset.planId = String(rawPlan.id);
    planItem.id = `learning-plan-${rawPlan.id}`;
    applyPlanPalette(planItem, rawPlan.id, planIndex);
    planItem.open = planIndex === 0;
    const planSummary = document.createElement("summary");
    const planTitle = makeElement("span", "plan-directory-title");
    planTitle.append(makeElement("i", "plan-folder-icon", String(planIndex + 1)), makeElement("strong", "", cleanText(rawPlan.goal) || "未命名计划"));
    const planMeta = makeElement("span", "plan-directory-meta", `${rawPlan.completed_tasks}/${rawPlan.total_tasks} 完成 · ${formatDate(rawPlan.start_date)} - ${formatDate(rawPlan.end_date)}`);
    planSummary.append(planTitle, planMeta);
    const planBody = makeElement("div", "plan-directory-body");
    const planTools = makeElement("div", "plan-item-tools");
    const colorKey = makeElement("span", "plan-color-key", `${rawPlan.progress || 0}% 完成`);
    const deleteButton = makeElement("button", "secondary-btn action-btn danger-btn plan-delete-btn");
    deleteButton.type = "button";
    const deleteIcon = document.createElement("i");
    deleteIcon.dataset.lucide = "trash-2";
    deleteButton.append(deleteIcon, makeElement("span", "", "删除计划"));
    deleteButton.addEventListener("click", () => deleteLearningPlan(rawPlan.id, rawPlan.goal));
    planTools.append(colorKey, deleteButton);
    planBody.appendChild(planTools);
    if (rawPlan.source_prompt) {
      const prompt = makeElement("p", "plan-source-prompt");
      prompt.append(makeElement("strong", "", "规划提问："), document.createTextNode(cleanText(rawPlan.source_prompt)));
      planBody.appendChild(prompt);
    }
    const weeks = new Map();
    (rawPlan.tasks || []).forEach((task) => {
      const week = Math.floor((Number(task.day) - 1) / 7) + 1;
      if (!weeks.has(week)) weeks.set(week, []);
      weeks.get(week).push(task);
    });
    weeks.forEach((weekTasks, weekNumber) => {
      const section = makeElement("details", "plan-week");
      section.open = weekTasks.some((task) => task.day === rawPlan.current_day) || (weekNumber === 1 && rawPlan.current_day <= 0);
      const summary = document.createElement("summary");
      const title = makeElement("span", "week-title");
      title.append(makeElement("i", "", String(weekNumber)), document.createTextNode(`第 ${weekNumber} 周`));
      const done = weekTasks.filter((task) => task.status === "completed").length;
      const meta = makeElement("span", "week-meta");
      meta.append(document.createTextNode(`${done}/${weekTasks.length} 已完成`));
      const chevron = document.createElement("i");
      chevron.dataset.lucide = "chevron-down";
      meta.appendChild(chevron);
      summary.append(title, meta);
      const taskList = makeElement("div", "week-tasks");
      weekTasks.forEach((task) => taskList.appendChild(buildPlanTask(task, rawPlan.current_day)));
      section.append(summary, taskList);
      planBody.appendChild(section);
    });
    planItem.append(planSummary, planBody);
    els.planTimeline.appendChild(planItem);
  });
  refreshIcons();
}

async function loadPlan() {
  try {
    let data;
    try {
      data = await api("/api/plans");
    } catch (_) {
      data = await api("/api/plan");
    }
    if (!Array.isArray(data.plans) && Array.isArray(data.tasks)) {
      data = {
        plans: [data], plan_count: 1,
        total_tasks: data.total_tasks || data.tasks.length,
        completed_tasks: data.completed_tasks || 0,
        progress: data.progress || 0
      };
    }
    renderPlan(data);
  } catch (error) {
    if (state.activeView === "plan") showToast(`计划加载失败：${error.message}`, true);
  }
}

function setRating(rating) {
  state.rating = rating;
  document.querySelectorAll("[data-rating]").forEach((button) => button.classList.toggle("selected", Number(button.dataset.rating) <= rating));
  els.ratingHint.textContent = rating ? `${rating} 分 · ${RATING_LABELS[rating - 1]}` : "请选择 1-5 分";
  els.reviewError.textContent = "";
}

function openReview(task) {
  if (!task?.id) return;
  state.reviewTaskId = task.id;
  els.reviewTaskName.textContent = `Day ${task.day} · ${cleanText(task.topic)}`;
  els.reviewInput.value = cleanText(task.review) || "";
  setRating(Number(task.rating || 0));
  els.reviewDialog.showModal();
  refreshIcons();
}

function closeReview() {
  if (els.reviewDialog.open) els.reviewDialog.close();
  state.reviewTaskId = null;
  setRating(0);
}

async function updateTaskStatus(taskId, completed, rating = null, review = "") {
  try {
    await api(`/api/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ completed, rating, review })
    });
    await Promise.all([loadPlan(), loadStatus(), loadCheckins()]);
    showToast(completed ? "任务已完成，评价已保存" : "任务已恢复为未完成");
    return true;
  } catch (error) {
    showToast(error.message, true);
    await Promise.all([loadPlan(), loadStatus(), loadCheckins()]);
    return false;
  }
}

async function uploadFiles(files) {
  const selected = Array.from(files || []);
  if (!selected.length) return;
  const form = new FormData();
  selected.forEach((file) => form.append("files", file));
  showToast(`正在整理 ${selected.length} 份资料…`);
  try {
    const data = await api("/api/upload", { method: "POST", body: form });
    showToast(`已添加 ${data.saved.length} 份资料，请在“可导入文档”中手动导入`);
    await loadStatus();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.fileInput.value = "";
  }
}

function exportPlan() {
  const plan = state.plan;
  if (!plan?.plans?.length) return showToast("当前没有可导出的学习计划", true);
  const lines = ["# 全部学习计划", "", `- 计划数量：${plan.plan_count}`, `- 总体进度：${plan.completed_tasks}/${plan.total_tasks}（${plan.progress}%）`, ""];
  plan.plans.forEach((item) => {
    lines.push(`## ${cleanText(item.goal) || "未命名计划"}`, "");
    if (item.source_prompt) lines.push(`- 规划提问：${cleanText(item.source_prompt)}`);
    lines.push(`- 计划周期：${item.start_date} 至 ${item.end_date}`);
    lines.push(`- 完成进度：${item.completed_tasks}/${item.total_tasks}（${item.progress}%）`, "");
    let currentWeek = 0;
    item.tasks.forEach((task) => {
      const week = Math.floor((task.day - 1) / 7) + 1;
      if (week !== currentWeek) { currentWeek = week; lines.push(`### 第 ${week} 周`, ""); }
      lines.push(`- ${task.status === "completed" ? "[已完成]" : "[未完成]"} Day ${task.day}：${cleanText(task.topic)}`);
      lines.push(`  - 日期：${task.scheduled_date || "未设置"}`);
      lines.push(`  - 内容：${cleanText(task.content)}`, "");
    });
  });
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `全部学习计划-${new Date().toISOString().slice(0, 10)}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/* 我的课表 */
const COURSE_HOUR_HEIGHT = 46;
const COURSE_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];

function coursePaletteIndex(name) {
  let hash = 0;
  for (const char of name || "") hash = (hash * 31 + char.codePointAt(0)) >>> 0;
  return hash % PLAN_PALETTES.length;
}

function courseMinutes(time) {
  const [hour, minute] = String(time || "0:0").split(":").map(Number);
  return (hour || 0) * 60 + (minute || 0);
}

async function loadCourses() {
  try {
    applyCourseState(await api("/api/courses"));
  } catch (error) {
    els.courseImportStatus.textContent = `课表加载失败：${error.message}`;
  }
}

function applyCourseState(data) {
  state.courses = Array.isArray(data.courses) ? data.courses : [];
  const importUrl = data.import_url || "";
  if (importUrl && document.activeElement !== els.courseUrlInput) els.courseUrlInput.value = importUrl;
  els.courseImportStatus.textContent = importUrl
    ? `当前订阅：${importUrl}`
    : "支持学校教务系统的 iCalendar 订阅链接或 .ics 文件";
  renderCourseGrid();
}

function renderCourseGrid() {
  const courses = state.courses || [];
  els.courseTotal.textContent = courses.length;
  els.courseCount.textContent = courses.length;
  els.courseEmpty.hidden = courses.length > 0;
  els.courseGridWrap.hidden = courses.length === 0;
  if (!courses.length) return;

  const startHour = Math.max(0, Math.floor(Math.min(...courses.map((c) => courseMinutes(c.start_time))) / 60));
  const endHour = Math.min(24, Math.max(startHour + 1, Math.ceil(Math.max(...courses.map((c) => courseMinutes(c.end_time))) / 60)));
  const height = (endHour - startHour) * COURSE_HOUR_HEIGHT;
  const today = ((new Date().getDay() + 6) % 7) + 1;

  els.courseGridHeader.innerHTML = "";
  els.courseGridHeader.appendChild(makeElement("span", "course-gutter-cell", ""));
  COURSE_WEEKDAYS.forEach((label, index) => {
    els.courseGridHeader.appendChild(makeElement("span", index + 1 === today ? "today" : "", index + 1 === today ? `${label} · 今天` : label));
  });

  els.courseGridBody.innerHTML = "";
  const gutter = makeElement("div", "course-time-gutter");
  gutter.style.height = `${height}px`;
  for (let hour = startHour; hour <= endHour; hour += 1) {
    const label = makeElement("span", "course-time-label", `${String(hour).padStart(2, "0")}:00`);
    label.style.top = `${(hour - startHour) * COURSE_HOUR_HEIGHT}px`;
    gutter.appendChild(label);
  }
  els.courseGridBody.appendChild(gutter);

  for (let day = 1; day <= 7; day += 1) {
    const column = makeElement("div", "course-day-col");
    column.style.height = `${height}px`;
    if (day === today) column.classList.add("today");
    courses.filter((course) => Number(course.day_of_week) === day).forEach((course) => {
      const top = (courseMinutes(course.start_time) - startHour * 60) / 60 * COURSE_HOUR_HEIGHT;
      const blockHeight = Math.max((courseMinutes(course.end_time) - courseMinutes(course.start_time)) / 60 * COURSE_HOUR_HEIGHT, 20);
      const palette = PLAN_PALETTES[coursePaletteIndex(course.name)];
      const block = makeElement("div", "course-block");
      block.style.top = `${top}px`;
      block.style.height = `${blockHeight}px`;
      block.style.setProperty("--cb-color", palette.accent);
      block.style.setProperty("--cb-soft", palette.soft);
      block.append(makeElement("strong", "", course.name), makeElement("span", "", `${course.start_time}–${course.end_time}`));
      const meta = [course.location, course.teacher, course.weeks_text].filter(Boolean).join(" · ");
      if (meta && blockHeight >= 40) block.appendChild(makeElement("span", "course-block-meta", meta));
      const remove = makeElement("button", "course-del", "×");
      remove.type = "button";
      remove.title = "删除该课程";
      remove.setAttribute("aria-label", `删除${course.name}`);
      remove.addEventListener("click", (event) => { event.stopPropagation(); removeCourse(course); });
      block.appendChild(remove);
      column.appendChild(block);
    });
    els.courseGridBody.appendChild(column);
  }
}

async function importCourseFromUrl() {
  const url = els.courseUrlInput.value.trim();
  if (!url) { showToast("请先粘贴课表订阅链接", true); return; }
  els.importCourseUrlBtn.disabled = true;
  els.importCourseUrlBtn.classList.add("loading");
  try {
    const data = await api("/api/courses/import-url", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url })
    });
    applyCourseState(data);
    showToast(`已从链接导入 ${data.imported} 节课程`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.importCourseUrlBtn.disabled = false;
    els.importCourseUrlBtn.classList.remove("loading");
  }
}

async function uploadCourseFile() {
  const file = els.courseFileInput.files?.[0];
  els.courseFileInput.value = "";
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    const data = await api("/api/courses/import-file", { method: "POST", body: form });
    applyCourseState(data);
    showToast(`已从文件导入 ${data.imported} 节课程`);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function submitCourseForm(event) {
  event.preventDefault();
  const payload = {
    name: els.courseNameInput.value.trim(),
    day_of_week: Number(els.courseDayInput.value),
    start_time: els.courseStartInput.value,
    end_time: els.courseEndInput.value,
    location: els.courseLocationInput.value.trim(),
    teacher: els.courseTeacherInput.value.trim(),
    weeks_text: els.courseWeeksInput.value.trim()
  };
  if (!payload.name) { showToast("请填写课程名称", true); return; }
  try {
    const data = await api("/api/courses", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    });
    applyCourseState(data);
    els.courseForm.reset();
    showToast(`已添加「${payload.name}」`);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function removeCourse(course) {
  const dayLabel = COURSE_WEEKDAYS[(Number(course.day_of_week) || 1) - 1];
  const confirmed = await confirmAction("删除课程", `确定从课表中删除「${course.name}」（${dayLabel} ${course.start_time}）吗？`, "确认删除");
  if (!confirmed) return;
  try {
    applyCourseState(await api(`/api/courses/${course.id}`, { method: "DELETE" }));
    showToast("课程已删除");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function clearAllCourses() {
  if (!(state.courses || []).length) { showToast("课表已经是空的"); return; }
  const confirmed = await confirmAction("清空课表", "确定删除课表中的全部课程吗？该操作不可恢复。", "确认清空");
  if (!confirmed) return;
  try {
    applyCourseState(await api("/api/courses", { method: "DELETE" }));
    els.courseUrlInput.value = "";
    showToast("课表已清空");
  } catch (error) {
    showToast(error.message, true);
  }
}

function closePanels() {
  els.sidebar.classList.remove("open");
  els.scrim.hidden = true;
}
function openPanel(panel) { closePanels(); panel.classList.add("open"); els.scrim.hidden = false; }

els.composer.addEventListener("submit", (event) => { event.preventDefault(); sendMessage(els.input.value); });
els.input.addEventListener("input", resizeInput);
els.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); els.composer.requestSubmit(); }
});
document.querySelectorAll("[data-prompt]").forEach((button) => button.addEventListener("click", () => {
  switchView("chat");
  sendMessage(button.dataset.prompt);
}));
document.querySelectorAll("[data-fill-prompt]").forEach((button) => button.addEventListener("click", () => {
  switchView("chat");
  els.input.value = button.dataset.fillPrompt;
  resizeInput();
  els.input.focus();
  els.input.setSelectionRange(els.input.value.length, els.input.value.length);
}));
document.querySelectorAll("[data-nav]").forEach((button) => button.addEventListener("click", () => {
  const target = button.dataset.nav;
  if (["chat", "plan", "today", "courses", "focus", "stats", "knowledge"].includes(target)) { switchView(target); return; }
}));
document.querySelectorAll("[data-plan-chat]").forEach((button) => button.addEventListener("click", () => {
  switchView("chat");
  els.input.value = "帮我制定一份新的学习计划";
  resizeInput();
}));

els.clearBtn.addEventListener("click", () => { resetConversation(); showToast("对话已清空"); });
els.newChatBtn.addEventListener("click", () => { switchView("chat"); resetConversation(); });
document.getElementById("viewPlanBtn").addEventListener("click", () => switchView("plan"));
document.getElementById("attachBtn").addEventListener("click", () => els.fileInput.click());
els.fileInput.addEventListener("change", () => uploadFiles(els.fileInput.files));
["dragenter", "dragover"].forEach((name) => els.uploader.addEventListener(name, (event) => { event.preventDefault(); els.uploader.classList.add("dragover"); }));
["dragleave", "drop"].forEach((name) => els.uploader.addEventListener(name, (event) => { event.preventDefault(); els.uploader.classList.remove("dragover"); }));
els.uploader.addEventListener("drop", (event) => uploadFiles(event.dataTransfer.files));

els.reindexBtn.addEventListener("click", async () => {
  els.reindexBtn.disabled = true;
  els.reindexBtn.classList.add("loading");
  els.reindexBtn.querySelector("span").textContent = "正在重建索引";
  try {
    const data = await api("/api/documents/reimport", { method: "POST" });
    showToast(`已重建 ${data.imported_documents.length} 份文档，共 ${data.chunks} 个知识片段`);
    await loadStatus();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.reindexBtn.disabled = Number(els.docTotal.textContent) === 0;
    els.reindexBtn.classList.remove("loading");
    els.reindexBtn.querySelector("span").textContent = "重建已导入索引";
  }
});
els.clearKnowledgeBtn.addEventListener("click", clearKnowledgeBase);

els.importCourseUrlBtn.addEventListener("click", importCourseFromUrl);
els.courseUrlInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") { event.preventDefault(); importCourseFromUrl(); }
});
els.uploadCourseFileBtn.addEventListener("click", () => els.courseFileInput.click());
els.courseFileInput.addEventListener("change", uploadCourseFile);
els.toggleCourseFormBtn.addEventListener("click", () => {
  els.courseForm.hidden = !els.courseForm.hidden;
  if (!els.courseForm.hidden) els.courseNameInput.focus();
});
els.courseForm.addEventListener("submit", submitCourseForm);
els.clearCoursesBtn.addEventListener("click", clearAllCourses);

document.querySelectorAll("[data-rating]").forEach((button) => button.addEventListener("click", () => setRating(Number(button.dataset.rating))));
els.reviewForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.rating) { els.reviewError.textContent = "请先选择 1-5 分评价，再确认完成。"; return; }
  els.confirmReviewBtn.disabled = true;
  const saved = await updateTaskStatus(state.reviewTaskId, true, state.rating, els.reviewInput.value);
  els.confirmReviewBtn.disabled = false;
  if (saved) closeReview();
});
document.getElementById("closeReviewBtn").addEventListener("click", closeReview);
document.getElementById("cancelReviewBtn").addEventListener("click", closeReview);
els.reviewDialog.addEventListener("cancel", (event) => { event.preventDefault(); closeReview(); });
els.reviewDialog.addEventListener("click", (event) => { if (event.target === els.reviewDialog) closeReview(); });
els.exportPlanBtn.addEventListener("click", exportPlan);
els.printPlanBtn.addEventListener("click", () => window.print());
document.querySelectorAll("[data-focus-minutes]").forEach((button) => button.addEventListener("click", () => {
  state.timer.mode = button.dataset.focusMode;
  state.timer.duration = Number(button.dataset.focusMinutes) * 60;
  state.timer.remaining = state.timer.duration;
  state.timer.startedAt = null;
  updateTimerUI();
  persistTimer();
}));
els.applyCustomTimeBtn.addEventListener("click", applyCustomTime);
els.customMinutesInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    applyCustomTime();
  }
});
els.timerStartBtn.addEventListener("click", startTimer);
els.timerPauseBtn.addEventListener("click", pauseTimer);
els.timerFinishBtn.addEventListener("click", () => {
  if (state.timer.running) pauseTimer();
  recordFocusSession(false);
});
document.getElementById("timerResetBtn").addEventListener("click", () => resetTimer());
els.focusTaskInput.addEventListener("input", persistTimer);
document.getElementById("refreshStatsBtn").addEventListener("click", async () => {
  await loadStats();
  showToast("学习数据已刷新");
});
els.refreshFocusHistoryBtn.addEventListener("click", async () => {
  els.refreshFocusHistoryBtn.disabled = true;
  els.refreshFocusHistoryBtn.classList.add("loading");
  await loadFocusSessions();
  els.refreshFocusHistoryBtn.disabled = false;
  els.refreshFocusHistoryBtn.classList.remove("loading");
});
document.getElementById("prevMonthBtn").addEventListener("click", () => {
  state.calendarMonth = new Date(state.calendarMonth.getFullYear(), state.calendarMonth.getMonth() - 1, 1);
  loadCheckins();
});
document.getElementById("nextMonthBtn").addEventListener("click", () => {
  state.calendarMonth = new Date(state.calendarMonth.getFullYear(), state.calendarMonth.getMonth() + 1, 1);
  loadCheckins();
});
els.checkinBtn.addEventListener("click", async () => {
  els.checkinBtn.disabled = true;
  try {
    await api("/api/checkins", { method: "POST" });
    state.calendarMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    await loadCheckins();
    showToast("今日签到成功");
  } catch (error) {
    showToast(error.message, true);
    await loadCheckins();
  }
});

document.getElementById("menuBtn").addEventListener("click", () => openPanel(els.sidebar));
els.scrim.addEventListener("click", closePanels);
window.addEventListener("resize", () => { if (window.innerWidth > 920) closePanels(); });

setDateAndGreeting();
refreshIcons();
restoreTimer();
Promise.all([loadStatus(), loadPlan(), loadCheckins(), loadCourses()]);
els.input.focus();
