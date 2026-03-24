const storage = {
  get(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  },
};

const state = {
  sampleResume: "",
  interviewStartedAt: Date.now(),
  questionStartedAt: Date.now(),
  lastClipboardEventAt: 0,
};

// Sends browser behavior events to the backend for cheating detection.
async function sendBehaviorEvent(eventType, details = {}) {
  try {
    await fetch("/behavior-event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_type: eventType, details }),
    });
  } catch {
    // Ignore telemetry failures in the demo flow.
  }
}


// Loads demo metadata such as the sample resume and active coding problem.
async function loadDemoData() {
  const response = await fetch("/demo-data");
  if (!response.ok) {
    throw new Error("Failed to load demo data");
  }
  return response.json();
}


// Starts the interview by generating questions from resume input.
async function startInterview() {
  const resumeText = document.querySelector("#resume-text").value.trim();
  const resumePdf = document.querySelector("#resume-pdf").files?.[0];
  const status = document.querySelector("#status");

  status.textContent = "Generating questions...";

  let response;
  if (resumePdf) {
    const form = new FormData();
    form.append("file", resumePdf);
    response = await fetch("/generate-questions-pdf", {
      method: "POST",
      body: form,
    });
  } else {
    if (!resumeText) {
      status.textContent = "Provide resume text or upload a PDF.";
      return;
    }
    response = await fetch("/generate-questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_text: resumeText }),
    });
  }

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    status.textContent = errorPayload.detail || "Failed to generate questions.";
    return;
  }

  const data = await response.json();
  storage.set("resumeText", resumeText);
  storage.set("questions", data.questions);
  storage.set("answers", []);
  storage.set("questionIndex", 0);
  storage.set("latestFeedback", null);
  storage.set("codingResult", null);
  window.location.href = "/interview";
}


// Renders the current interview question and prior evaluation state.
function renderInterview() {
  const questions = storage.get("questions", []);
  const questionIndex = storage.get("questionIndex", 0);
  const latestFeedback = storage.get("latestFeedback", null);
  const question = questions[questionIndex];

  if (!question) {
    window.location.href = "/coding";
    return;
  }

  document.querySelector("#question-heading").textContent = `Question ${questionIndex + 1}`;
  document.querySelector("#question-text").textContent = question;
  document.querySelector("#question-count").textContent = `${questionIndex + 1} / ${questions.length}`;
  document.querySelector("#difficulty-level").textContent = questionIndex < 2 ? "Difficulty: Medium" : "Adaptive";

  if (latestFeedback) {
    document.querySelector("#latest-feedback").innerHTML = `
      <strong>Latest Score: ${latestFeedback.score}</strong>
      <p><strong>Strengths:</strong> ${latestFeedback.strengths}</p>
      <p><strong>Weaknesses:</strong> ${latestFeedback.weaknesses}</p>
      <p>${latestFeedback.feedback}</p>
    `;
  } else {
    document.querySelector("#latest-feedback").textContent = "Submit an answer to receive AI feedback and adaptive scoring.";
  }
}


// Submits the current interview answer and advances the flow.
async function submitInterviewAnswer() {
  const answerText = document.querySelector("#answer-text").value.trim();
  const status = document.querySelector("#interview-status");
  const questions = storage.get("questions", []);
  const questionIndex = storage.get("questionIndex", 0);
  const answers = storage.get("answers", []);

  if (!answerText) {
    status.textContent = "Answer text is required.";
    return;
  }

  status.textContent = "Evaluating answer...";
  const elapsedSeconds = Math.round((Date.now() - state.questionStartedAt) / 1000);
  const response = await fetch("/evaluate-answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: questions[questionIndex],
      answer: answerText,
      elapsed_seconds: elapsedSeconds,
    }),
  });

  const result = await response.json();
  answers.push({ question: questions[questionIndex], answer: answerText, ...result });
  storage.set("answers", answers);
  storage.set("latestFeedback", result);
  storage.set("questionIndex", questionIndex + 1);
  document.querySelector("#answer-text").value = "";
  status.textContent = `Answer scored ${result.score}/100.`;
  state.questionStartedAt = Date.now();

  if (questionIndex + 1 >= questions.length) {
    document.querySelector("#go-coding").classList.remove("hidden");
    document.querySelector("#submit-answer").classList.add("hidden");
    status.textContent = `Interview complete. Last score: ${result.score}/100.`;
  }

  renderInterview();
}


// Loads the active coding prompt for the candidate.
async function renderCoding() {
  const data = await loadDemoData();
  document.querySelector("#coding-title").textContent = data.coding_problem.title;
  document.querySelector("#coding-prompt").textContent = data.coding_problem.prompt;
}


// Executes the coding submission through the backend sandbox.
async function submitCode() {
  const code = document.querySelector("#code-input").value;
  const resultNode = document.querySelector("#code-result");
  const elapsedSeconds = Math.round((Date.now() - state.interviewStartedAt) / 1000);

  resultNode.textContent = "Running tests...";
  const response = await fetch("/run-code", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, elapsed_seconds: elapsedSeconds }),
  });

  const result = await response.json();
  storage.set("codingResult", result);
  resultNode.textContent = JSON.stringify(result, null, 2);
  document.querySelector("#show-report").classList.remove("hidden");
}


// Renders the final candidate report returned by the backend.
async function renderReport() {
  const response = await fetch("/report");
  const report = await response.json();

  document.querySelector("#recommendation-text").textContent = `Recommendation: ${report.recommendation}`;
  document.querySelector("#overall-score").textContent = report.overall_score;
  document.querySelector("#interview-score").textContent = report.interview_score;
  document.querySelector("#coding-score").textContent = report.coding_score;
  document.querySelector("#behavior-score").textContent = report.behavior_score;

  populateList("#strengths-list", report.strengths);
  populateList("#weaknesses-list", report.weaknesses);
  populateList("#skills-list", report.extracted_skills);
  populateList("#flags-list", report.behavior_flags.length ? report.behavior_flags : ["No suspicious events recorded"]);
  populateList("#resume-source-list", [formatResumeSource(report.resume_source)]);
  populateList("#behavior-breakdown-list", formatBehaviorBreakdown(report.behavior_breakdown));

  const feedbackList = document.querySelector("#feedback-list");
  feedbackList.innerHTML = "";
  report.interview_feedback.forEach((item) => {
    const card = document.createElement("article");
    card.className = "feedback-card";
    card.innerHTML = `
      <strong>${item.question}</strong>
      <p>Score: ${item.score}</p>
      <p>${item.feedback}</p>
    `;
    feedbackList.appendChild(card);
  });
}


// Populates a list node with string values.
function populateList(selector, values) {
  const node = document.querySelector(selector);
  node.innerHTML = "";
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    node.appendChild(item);
  });
}


// Converts backend resume source labels into user-friendly text.
function formatResumeSource(source) {
  if (source === "pdf_ocr") {
    return "PDF upload (OCR fallback used)";
  }
  if (source === "pdf_text") {
    return "PDF upload (text layer)";
  }
  return "Pasted text";
}


// Formats behavior penalty details from the report into readable lines.
function formatBehaviorBreakdown(breakdown) {
  if (!breakdown || typeof breakdown !== "object") {
    return ["No behavior details available"];
  }
  return [
    `Tab switches: ${breakdown.tab_switch_count} (penalty: ${breakdown.tab_penalty})`,
    `Paste events: ${breakdown.paste_count}, Copy/Cut events: ${breakdown.copy_cut_count} (penalty: ${breakdown.clipboard_penalty})`,
    `Rapid submits: ${breakdown.rapid_submit_count} (penalty: ${breakdown.rapid_penalty})`,
    `High submission penalty: ${breakdown.high_submission_penalty}`,
    `Total behavior penalty: ${breakdown.total_penalty}`,
  ];
}


// Registers browser-level suspicious behavior listeners.
function registerBehaviorListeners() {
  const sendClipboardEvent = (action, source) => {
    const now = Date.now();
    if (now - state.lastClipboardEventAt < 500) {
      return;
    }
    state.lastClipboardEventAt = now;
    sendBehaviorEvent("copy_paste", { page: document.body.dataset.page, action, source });
  };

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      sendBehaviorEvent("tab_switch", { page: document.body.dataset.page });
    }
  });

  document.addEventListener("paste", () => {
    sendClipboardEvent("paste", "event");
  });

  document.addEventListener("copy", () => {
    sendClipboardEvent("copy", "event");
  });

  document.addEventListener("cut", () => {
    sendClipboardEvent("cut", "event");
  });

  document.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    const commandPressed = event.ctrlKey || event.metaKey;
    if (!commandPressed) {
      return;
    }
    if (key === "v") {
      sendClipboardEvent("paste", "shortcut");
    }
    if (key === "c") {
      sendClipboardEvent("copy", "shortcut");
    }
    if (key === "x") {
      sendClipboardEvent("cut", "shortcut");
    }
  });

  document.addEventListener("beforeinput", (event) => {
    if (event.inputType === "insertFromPaste") {
      sendClipboardEvent("paste", "beforeinput");
    }
  });
}


// Boots the correct page controller for the current HTML page.
async function init() {
  registerBehaviorListeners();
  const page = document.body.dataset.page;

  if (page === "index") {
    const sample = await loadDemoData();
    state.sampleResume = sample.sample_resume;
    document.querySelector("#sample-preview").textContent = sample.sample_resume;
    document.querySelector("#load-sample").addEventListener("click", () => {
      document.querySelector("#resume-text").value = state.sampleResume;
    });
    document.querySelector("#start-interview").addEventListener("click", startInterview);
  }

  if (page === "interview") {
    state.questionStartedAt = Date.now();
    renderInterview();
    document.querySelector("#submit-answer").addEventListener("click", submitInterviewAnswer);
    document.querySelector("#go-coding").addEventListener("click", () => {
      window.location.href = "/coding";
    });
  }

  if (page === "coding") {
    state.interviewStartedAt = Date.now();
    await renderCoding();
    document.querySelector("#submit-code").addEventListener("click", submitCode);
    document.querySelector("#show-report").addEventListener("click", () => {
      window.location.href = "/report-page";
    });
  }

  if (page === "report") {
    await renderReport();
  }
}

init();