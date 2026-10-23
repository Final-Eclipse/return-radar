/* Return Radar - customer questionnaire flow (backend-driven).
 *
 * The browser never contains the question tree. After each answer it asks the
 * Flask backend for the next question, so the adaptive logic lives in Python.
 * Accessibility: focus is moved to each new question, choices are operable by
 * keyboard, and a live region announces changes.
 */
(function () {
  "use strict";

  const state = {
    category: null,        // selected category id
    categoryName: null,    // human-readable name
    answers: {},           // question_id -> answer value
    currentQuestion: null, // the question object currently shown
    questionCount: 0,      // how many questions answered (for progress)
  };

  // Elements
  const categoryStep = document.getElementById("category-step");
  const questionStep = document.getElementById("question-step");
  const doneStep = document.getElementById("done-step");
  const questionContainer = document.getElementById("question-container");
  const nextBtn = document.getElementById("next-btn");
  const restartBtn = document.getElementById("restart-btn");
  const againBtn = document.getElementById("again-btn");
  const formStatus = document.getElementById("form-status");
  const progressText = document.getElementById("progress-text");
  const progressFill = document.getElementById("progress-fill");

  // ---- API helpers -------------------------------------------------------
  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || "Request failed");
    }
    return data;
  }

  function setStatus(message) {
    formStatus.textContent = message || "";
  }

  // ---- Category selection ------------------------------------------------
  document.querySelectorAll(".category-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".category-btn").forEach(function (b) {
        b.setAttribute("aria-pressed", "false");
      });
      btn.setAttribute("aria-pressed", "true");

      state.category = btn.dataset.categoryId;
      state.categoryName = btn.dataset.categoryName;
      state.answers = {};
      state.questionCount = 0;

      startQuestionnaire();
    });
  });

  async function startQuestionnaire() {
    categoryStep.classList.add("hidden");
    doneStep.classList.add("hidden");
    questionStep.classList.remove("hidden");
    await loadNextQuestion();
  }

  // ---- Question rendering ------------------------------------------------
  async function loadNextQuestion() {
    setStatus("");
    try {
      const data = await postJSON("/next-question", {
        category: state.category,
        answers: state.answers,
      });

      if (data.done) {
        await finish();
        return;
      }
      renderQuestion(data.question);
    } catch (err) {
      setStatus("Sorry, something went wrong loading the next question.");
    }
  }

  function renderQuestion(question) {
    state.currentQuestion = question;
    state.questionCount += 1;

    const helpId = "help-" + question.id;
    const hasHelp = Boolean(question.help);

    const fieldset = document.createElement("fieldset");
    fieldset.className = "question";
    fieldset.setAttribute("role", "radiogroup");
    fieldset.setAttribute("aria-labelledby", "legend-" + question.id);
    if (hasHelp) {
      fieldset.setAttribute("aria-describedby", helpId);
    }

    const legend = document.createElement("legend");
    legend.id = "legend-" + question.id;
    legend.textContent = question.text;
    fieldset.appendChild(legend);

    if (hasHelp) {
      const help = document.createElement("p");
      help.className = "question-help";
      help.id = helpId;
      help.textContent = question.help;
      fieldset.appendChild(help);
    }

    const optionsWrap = document.createElement("div");
    optionsWrap.className = "options";

    question.options.forEach(function (opt, idx) {
      const inputId = question.id + "-" + opt.value;
      const row = document.createElement("div");
      row.className = "option";

      const input = document.createElement("input");
      input.type = "radio";
      input.name = question.id;
      input.id = inputId;
      input.value = opt.value;
      // Pre-select if we already have an answer (e.g. after "start over" edge).
      if (state.answers[question.id] === opt.value) {
        input.checked = true;
      }
      input.addEventListener("change", function () {
        nextBtn.disabled = false;
      });

      const label = document.createElement("label");
      label.setAttribute("for", inputId);
      label.textContent = opt.label;

      row.appendChild(input);
      row.appendChild(label);
      optionsWrap.appendChild(row);
    });

    fieldset.appendChild(optionsWrap);

    // Swap content and move focus to the new question for screen-reader users.
    questionContainer.innerHTML = "";
    questionContainer.appendChild(fieldset);

    nextBtn.disabled = !state.answers[question.id];

    updateProgress();

    // Focus the legend/group so AT reads the new question.
    legend.setAttribute("tabindex", "-1");
    legend.focus();
  }

  function updateProgress() {
    progressText.textContent = "Question " + state.questionCount;
    // Soft progress heuristic: typical flow is ~3-4 questions.
    const pct = Math.min(100, Math.round((state.questionCount / 4) * 100));
    progressFill.style.width = pct + "%";
  }

  // ---- Next / submit -----------------------------------------------------
  nextBtn.addEventListener("click", function () {
    const q = state.currentQuestion;
    if (!q) return;
    const checked = questionContainer.querySelector(
      'input[name="' + CSS.escape(q.id) + '"]:checked'
    );
    if (!checked) {
      setStatus("Please choose an option before continuing.");
      return;
    }
    state.answers[q.id] = checked.value;
    loadNextQuestion();
  });

  async function finish() {
    try {
      await postJSON("/submit", {
        category: state.category,
        answers: state.answers,
      });
      questionStep.classList.add("hidden");
      doneStep.classList.remove("hidden");
      doneStep.focus();
      progressFill.style.width = "100%";
    } catch (err) {
      setStatus("We couldn't save your feedback. Please try again.");
    }
  }

  // ---- Restart -----------------------------------------------------------
  function resetToStart() {
    state.category = null;
    state.categoryName = null;
    state.answers = {};
    state.currentQuestion = null;
    state.questionCount = 0;
    questionContainer.innerHTML = "";
    progressFill.style.width = "0%";
    nextBtn.disabled = true;

    document.querySelectorAll(".category-btn").forEach(function (b) {
      b.setAttribute("aria-pressed", "false");
    });

    questionStep.classList.add("hidden");
    doneStep.classList.add("hidden");
    categoryStep.classList.remove("hidden");
  }

  restartBtn.addEventListener("click", resetToStart);
  againBtn.addEventListener("click", resetToStart);
})();
