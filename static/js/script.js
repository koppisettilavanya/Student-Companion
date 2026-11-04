/**
 * AI Student Companion - Vanilla JavaScript Application Engine
 * Pure ES6+, Fetch API, Robust Error Handling, Markdown & Code Highlighting
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Application State
  // ---------------------------------------------------------------------------
  const state = {
    activeView: 'chat', // 'chat' | 'dashboard' | 'explainer' | 'interview' | 'quiz' | 'history'
    currentConversationId: null,
    conversations: [],
    isGenerating: false,
    abortController: null,
    theme: localStorage.getItem('groqchat_theme') || 'dark',
    activeModel: localStorage.getItem('groqchat_model') || 'qwen/qwen3.8-27b',
    userApiKey: localStorage.getItem('groqchat_api_key') || '',
    supportedModels: [],
    systemConfigured: false,
    deleteTarget: null, // { type: 'conversation'|'explanation'|'interview'|'quiz', id: string }

    // User Authentication State
    currentUser: null, // { id, username, email, full_name, study_streak }

    // File Upload State inside Chat
    attachedFile: null, // { id, filename, file_type, file_size, char_count, word_count }

    // Active Quiz State
    currentQuiz: null, // { quiz_id, topic, questions, userAnswers: {} }

    // Active Explainer State
    currentExplanation: null,
  };

  // ---------------------------------------------------------------------------
  // DOM Elements
  // ---------------------------------------------------------------------------
  const elements = {
    app: document.getElementById('app'),
    sidebar: document.getElementById('sidebar'),
    sidebarBackdrop: document.getElementById('sidebar-backdrop'),
    btnToggleSidebar: document.getElementById('btn-toggle-sidebar'),
    btnCollapseSidebar: document.getElementById('btn-collapse-sidebar'),
    btnNewChat: document.getElementById('btn-new-chat'),
    btnNewChatTop: document.getElementById('btn-new-chat-top'),
    btnClearChat: document.getElementById('btn-clear-chat'),
    searchInput: document.getElementById('search-conversations'),
    searchClear: document.getElementById('search-clear'),
    conversationList: document.getElementById('conversation-list'),
    activeChatTitle: document.getElementById('active-chat-title'),
    btnThemeToggle: document.getElementById('btn-theme-toggle'),
    themeIcon: document.getElementById('theme-icon'),
    btnSettings: document.getElementById('btn-settings'),
    statusDot: document.getElementById('status-dot'),
    modelBadge: document.getElementById('model-badge'),
    topModelSelector: document.getElementById('top-model-selector'),
    toastContainer: document.getElementById('toast-container'),

    // Navigation Items
    navItems: document.querySelectorAll('.nav-item'),
    viewPanels: document.querySelectorAll('.view-panel'),
    chatSidebarActions: document.getElementById('chat-sidebar-actions'),
    historyCategoryLabel: document.getElementById('history-category-label'),

    // Auth Slot & Modal
    userAuthSlot: document.getElementById('user-auth-slot'),
    authModal: document.getElementById('auth-modal'),
    btnCloseAuth: document.getElementById('btn-close-auth'),
    tabLogin: document.getElementById('tab-login'),
    tabSignup: document.getElementById('tab-signup'),
    formLogin: document.getElementById('form-login'),
    formSignup: document.getElementById('form-signup'),
    authAlert: document.getElementById('auth-alert'),

    // Chat View
    chatMessages: document.getElementById('chat-messages'),
    chatInner: document.getElementById('chat-inner'),
    welcomeScreen: document.getElementById('welcome-screen'),
    chatComposer: document.getElementById('chat-composer'),
    messageInput: document.getElementById('message-input'),
    btnSend: document.getElementById('btn-send'),
    btnStop: document.getElementById('btn-stop'),
    charCounter: document.getElementById('char-counter'),

    // File Upload elements inside Chat
    btnUploadFile: document.getElementById('btn-upload-file'),
    fileUploadInput: document.getElementById('file-upload-input'),
    composerFilePreview: document.getElementById('composer-file-preview'),
    fileNameBadge: document.getElementById('file-name-badge'),
    fileStatusBadge: document.getElementById('file-status-badge'),
    fileIconBadge: document.getElementById('file-icon-badge'),
    btnRemoveFile: document.getElementById('btn-remove-file'),
    filePillsRow: document.getElementById('file-pills-row'),
    pillSummarize: document.getElementById('pill-summarize'),
    pillQuestions: document.getElementById('pill-questions'),
    pillMcq: document.getElementById('pill-mcq'),

    // Dashboard View
    dashboardWelcomeMsg: document.getElementById('dashboard-welcome-msg'),
    dashStreakTitle: document.getElementById('dash-streak-title'),
    dashStreakCount: document.getElementById('dash-streak-count'),
    dashStatSessions: document.getElementById('dash-stat-sessions'),
    dashStatQuizzes: document.getElementById('dash-stat-quizzes'),
    dashStatAvgScore: document.getElementById('dash-stat-avg-score'),
    dashStatTopics: document.getElementById('dash-stat-topics'),
    dashboardRecentActivities: document.getElementById('dashboard-recent-activities'),
    dashboardRecentQuizzes: document.getElementById('dashboard-recent-quizzes'),

    // Explainer View
    explainerTopicInput: document.getElementById('explainer-topic-input'),
    explainerSubjectSelect: document.getElementById('explainer-subject-select'),
    explainerLevelSelect: document.getElementById('explainer-level-select'),
    btnGenerateExplanation: document.getElementById('btn-generate-explanation'),
    explainerResultsArea: document.getElementById('explainer-results-area'),
    explainerResultTitle: document.getElementById('explainer-result-title'),
    explainerResultBadge: document.getElementById('explainer-result-badge'),
    btnSaveExplanation: document.getElementById('btn-save-explanation'),
    btnAskChatFollowup: document.getElementById('btn-ask-chat-followup'),
    explainerSectionSummary: document.getElementById('explainer-section-summary'),
    explainerSectionDetail: document.getElementById('explainer-section-detail'),
    explainerSectionExamples: document.getElementById('explainer-section-examples'),
    explainerSectionCode: document.getElementById('explainer-section-code'),
    explainerSectionTips: document.getElementById('explainer-section-tips'),
    savedExplanationsList: document.getElementById('saved-explanations-list'),

    // Interview View
    interviewSubjectInput: document.getElementById('interview-subject-input'),
    interviewRoleInput: document.getElementById('interview-role-input'),
    interviewDiffSelect: document.getElementById('interview-diff-select'),
    btnGenerateInterview: document.getElementById('btn-generate-interview'),
    interviewResultsArea: document.getElementById('interview-results-area'),
    interviewResultRole: document.getElementById('interview-result-role'),
    interviewResultBadge: document.getElementById('interview-result-badge'),
    interviewTipsList: document.getElementById('interview-tips-list'),
    interviewQuestionsAccordion: document.getElementById('interview-questions-accordion'),
    pastInterviewSessionsList: document.getElementById('past-interview-sessions-list'),

    // Quiz View
    quizTopicInput: document.getElementById('quiz-topic-input'),
    quizCountSelect: document.getElementById('quiz-count-select'),
    quizDiffSelect: document.getElementById('quiz-diff-select'),
    btnGenerateQuiz: document.getElementById('btn-generate-quiz'),
    quizActiveArea: document.getElementById('quiz-active-area'),
    quizActiveTitle: document.getElementById('quiz-active-title'),
    quizActiveBadge: document.getElementById('quiz-active-badge'),
    quizQuestionsList: document.getElementById('quiz-questions-list'),
    btnSubmitQuiz: document.getElementById('btn-submit-quiz'),
    quizResultsBanner: document.getElementById('quiz-results-banner'),
    quizScoreIcon: document.getElementById('quiz-score-icon'),
    quizScoreText: document.getElementById('quiz-score-text'),
    quizFeedbackText: document.getElementById('quiz-feedback-text'),
    btnRetakeQuiz: document.getElementById('btn-retake-quiz'),
    btnNewQuizGen: document.getElementById('btn-new-quiz-gen'),
    pastQuizzesList: document.getElementById('past-quizzes-list'),

    // History View
    historySearchInput: document.getElementById('history-search-input'),
    historyFilterBtns: document.querySelectorAll('.history-filter-btn'),
    historyItemsContainer: document.getElementById('history-items-container'),

    // Modals
    clearChatModal: document.getElementById('clear-chat-modal'),
    btnCancelClear: document.getElementById('btn-cancel-clear'),
    btnConfirmClear: document.getElementById('btn-confirm-clear'),

    deleteModal: document.getElementById('delete-modal'),
    deleteModalTitle: document.getElementById('delete-modal-title'),
    deleteModalBody: document.getElementById('delete-modal-body'),
    btnCancelDelete: document.getElementById('btn-cancel-delete'),
    btnConfirmDelete: document.getElementById('btn-confirm-delete'),

    settingsModal: document.getElementById('settings-modal'),
    btnCloseSettings: document.getElementById('btn-close-settings'),
    btnSaveSettings: document.getElementById('btn-save-settings'),
    btnTestKey: document.getElementById('btn-test-key'),
    inputApiKey: document.getElementById('input-api-key'),
    selectModel: document.getElementById('select-model'),
    keyValidationResult: document.getElementById('key-validation-result'),
  };

  // ---------------------------------------------------------------------------
  // Utility Functions
  // ---------------------------------------------------------------------------
  function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise((resolve, reject) => {
      try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const successful = document.execCommand('copy');
        textArea.remove();
        if (successful) resolve();
        else reject(new Error('execCommand copy failed'));
      } catch (err) {
        reject(err);
      }
    });
  }

  function showToast(message, type = 'info') {
    if (!elements.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === 'error') {
      iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    } else {
      iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.2s ease';
      setTimeout(() => toast.remove(), 200);
    }, 3200);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  function renderMarkdown(content) {
    if (typeof window.marked !== 'undefined' && window.marked.parse) {
      try {
        const rawHtml = window.marked.parse(content, { breaks: true, gfm: true });
        if (typeof window.DOMPurify !== 'undefined' && window.DOMPurify.sanitize) {
          return window.DOMPurify.sanitize(rawHtml);
        }
        return rawHtml;
      } catch (e) {
        console.error('Markdown parse error:', e);
      }
    }
    return `<p>${escapeHtml(content).replace(/\n/g, '<br/>')}</p>`;
  }

  function applySyntaxHighlighting(container) {
    const preBlocks = container.querySelectorAll('pre');
    preBlocks.forEach((pre) => {
      if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrapper')) {
        return;
      }

      const codeElement = pre.querySelector('code');
      let language = 'text';
      if (codeElement) {
        const langClass = Array.from(codeElement.classList).find((cls) => cls.startsWith('language-'));
        if (langClass) language = langClass.replace('language-', '');
        if (typeof window.hljs !== 'undefined' && window.hljs.highlightElement) {
          window.hljs.highlightElement(codeElement);
        }
      }

      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';

      const header = document.createElement('div');
      header.className = 'code-header';
      header.innerHTML = `
        <span class="code-lang">${escapeHtml(language)}</span>
        <button class="copy-code-btn" type="button" aria-label="Copy code">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          <span>Copy</span>
        </button>
      `;

      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(header);
      wrapper.appendChild(pre);

      const copyBtn = header.querySelector('.copy-code-btn');
      copyBtn.addEventListener('click', () => {
        const codeText = codeElement ? codeElement.innerText : pre.innerText;
        copyToClipboard(codeText).then(() => {
          copyBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
            <span style="color:#10b981">Copied!</span>
          `;
          setTimeout(() => {
            copyBtn.innerHTML = `
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              <span>Copy</span>
            `;
          }, 2000);
        });
      });
    });
  }

  function scrollToBottom() {
    if (elements.chatMessages) {
      elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }
  }

  // ---------------------------------------------------------------------------
  // API Fetch Helper
  // ---------------------------------------------------------------------------
  async function apiFetch(endpoint, options = {}) {
    const isFormData = options.body instanceof FormData;
    const defaultHeaders = {
      'X-CSRFToken': getCsrfToken(),
    };

    if (!isFormData) {
      defaultHeaders['Content-Type'] = 'application/json';
    }

    if (state.userApiKey) {
      defaultHeaders['X-Groq-Api-Key'] = state.userApiKey;
    }

    if (state.activeModel) {
      defaultHeaders['X-Groq-Model'] = state.activeModel;
    }

    const mergedOptions = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {}),
      },
    };

    return await fetch(endpoint, mergedOptions);
  }

  // ---------------------------------------------------------------------------
  // Feature 1: Authentication & User Profile
  // ---------------------------------------------------------------------------
  async function checkAuthStatus() {
    try {
      const res = await apiFetch('/api/auth/status/');
      if (res.ok) {
        const data = await res.json();
        if (data.authenticated && data.user) {
          state.currentUser = data.user;
          renderUserSlot();
        } else {
          state.currentUser = null;
          renderUserSlot();
        }
      }
    } catch (err) {
      console.warn('Auth status check error:', err);
    }
  }

  function renderUserSlot() {
    if (!elements.userAuthSlot) return;

    if (state.currentUser) {
      const user = state.currentUser;
      const initials = (user.full_name || user.username)
        .split(' ')
        .map((p) => p[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);

      elements.userAuthSlot.innerHTML = `
        <div class="user-profile-bar">
          <div class="user-avatar">${escapeHtml(initials)}</div>
          <div class="user-details">
            <div class="user-name">${escapeHtml(user.full_name || user.username)}</div>
            <div class="user-streak">🔥 ${user.study_streak} day streak</div>
          </div>
          <button class="icon-btn" id="btn-logout" title="Sign out" aria-label="Sign out">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>
      `;

      const btnLogout = document.getElementById('btn-logout');
      if (btnLogout) {
        btnLogout.addEventListener('click', handleLogout);
      }
    } else {
      elements.userAuthSlot.innerHTML = `
        <button class="login-prompt-btn" id="btn-open-auth" type="button">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
            <polyline points="10 17 15 12 10 7"></polyline>
            <line x1="15" y1="12" x2="3" y2="12"></line>
          </svg>
          <span>Sign In / Sign Up</span>
        </button>
      `;

      const btnOpenAuth = document.getElementById('btn-open-auth');
      if (btnOpenAuth) {
        btnOpenAuth.addEventListener('click', () => openAuthModal('login'));
      }
    }
  }

  function openAuthModal(defaultTab = 'login') {
    if (!elements.authModal) return;
    elements.authModal.classList.add('active');
    switchAuthTab(defaultTab);
  }

  function closeAuthModal() {
    if (!elements.authModal) return;
    elements.authModal.classList.remove('active');
    clearAuthAlert();
  }

  function switchAuthTab(tab) {
    clearAuthAlert();
    if (tab === 'signup') {
      elements.tabSignup.classList.add('active');
      elements.tabLogin.classList.remove('active');
      elements.formSignup.style.display = 'block';
      elements.formLogin.style.display = 'none';
      document.getElementById('auth-modal-title').textContent = 'Create Student Account';
    } else {
      elements.tabLogin.classList.add('active');
      elements.tabSignup.classList.remove('active');
      elements.formLogin.style.display = 'block';
      elements.formSignup.style.display = 'none';
      document.getElementById('auth-modal-title').textContent = 'Sign In to Student Account';
    }
  }

  function showAuthAlert(msg, isSuccess = false) {
    if (!elements.authAlert) return;
    elements.authAlert.className = `auth-alert-box ${isSuccess ? 'success' : 'error'}`;
    elements.authAlert.textContent = msg;
  }

  function clearAuthAlert() {
    if (!elements.authAlert) return;
    elements.authAlert.className = 'auth-alert-box';
    elements.authAlert.textContent = '';
  }

  async function handleLogin(e) {
    e.preventDefault();
    clearAuthAlert();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
      showAuthAlert('Please enter both username/email and password.');
      return;
    }

    try {
      const res = await apiFetch('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        state.currentUser = data.user;
        renderUserSlot();
        closeAuthModal();
        showToast(data.message || 'Signed in successfully!', 'success');
        fetchConversations();
        if (state.activeView === 'dashboard') loadDashboardData();
      } else {
        showAuthAlert(data.error || 'Failed to sign in. Verify your credentials.');
      }
    } catch (err) {
      showAuthAlert('Server connection error. Please try again.');
    }
  }

  async function handleSignup(e) {
    e.preventDefault();
    clearAuthAlert();
    const fullName = document.getElementById('signup-name').value.trim();
    const username = document.getElementById('signup-username').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const confirmPassword = document.getElementById('signup-confirm-password').value;

    if (!username || !email || !password) {
      showAuthAlert('Please fill out all required fields.');
      return;
    }

    if (password !== confirmPassword) {
      showAuthAlert('Passwords do not match.');
      return;
    }

    try {
      const res = await apiFetch('/api/auth/signup/', {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName,
          username,
          email,
          password,
          confirm_password: confirmPassword,
        }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        state.currentUser = data.user;
        renderUserSlot();
        closeAuthModal();
        showToast('Account created successfully! Welcome aboard.', 'success');
        fetchConversations();
        if (state.activeView === 'dashboard') loadDashboardData();
      } else {
        showAuthAlert(data.error || 'Failed to create account.');
      }
    } catch (err) {
      showAuthAlert('Server connection error. Please try again.');
    }
  }

  async function handleLogout() {
    try {
      await apiFetch('/api/auth/logout/', { method: 'POST' });
      state.currentUser = null;
      renderUserSlot();
      showToast('Signed out successfully.', 'info');
      fetchConversations();
      if (state.activeView === 'dashboard') {
        switchView('chat');
      }
    } catch (err) {
      showToast('Error signing out', 'error');
    }
  }

  // ---------------------------------------------------------------------------
  // Navigation & View Switching
  // ---------------------------------------------------------------------------
  function switchView(viewName) {
    state.activeView = viewName;

    // 1. Update navigation button styles
    const allNavBtns = document.querySelectorAll('.nav-item');
    allNavBtns.forEach((btn) => {
      if (btn.getAttribute('data-view') === viewName) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // 2. Hide ALL view panels explicitly to prevent any overlap
    const panels = ['chat', 'dashboard', 'explainer', 'interview', 'quiz', 'history'];
    panels.forEach((p) => {
      const el = document.getElementById(`view-${p}`);
      if (el) {
        el.classList.remove('active');
        el.style.display = 'none';
      }
    });

    // 3. Show ONLY the active view panel
    const targetPanel = document.getElementById(`view-${viewName}`);
    if (targetPanel) {
      targetPanel.classList.add('active');
      targetPanel.style.display = 'flex';
    }

    // 4. Update title in top navbar
    const titles = {
      chat: 'AI Study Chat',
      dashboard: 'Student Dashboard',
      explainer: 'Topic Explainer',
      interview: 'Interview Preparation',
      quiz: 'MCQ Quiz Generator',
      history: 'Learning History',
    };
    if (elements.activeChatTitle) {
      elements.activeChatTitle.textContent = titles[viewName] || 'AI Student Companion';
    }

    // 5. Toggle chat-specific actions
    if (elements.btnClearChat) {
      elements.btnClearChat.style.display = viewName === 'chat' ? 'inline-flex' : 'none';
    }
    if (elements.btnNewChatTop) {
      elements.btnNewChatTop.style.display = viewName === 'chat' ? 'inline-flex' : 'none';
    }

    closeMobileSidebar();

    // 6. Trigger data loaders for specific views
    if (viewName === 'dashboard') {
      loadDashboardData();
    } else if (viewName === 'explainer') {
      loadSavedExplanations();
    } else if (viewName === 'interview') {
      loadInterviewHistory();
    } else if (viewName === 'quiz') {
      loadQuizHistory();
    } else if (viewName === 'history') {
      loadLearningHistory();
    } else if (viewName === 'chat') {
      scrollToBottom();
      if (elements.messageInput) elements.messageInput.focus();
    }
  }

  // ---------------------------------------------------------------------------
  // Feature 2: Student Dashboard
  // ---------------------------------------------------------------------------
  async function loadDashboardData() {
    if (!state.currentUser) {
      elements.dashboardWelcomeMsg.textContent = 'Sign in to track your study sessions, streak, and quiz scores!';
      elements.dashStreakTitle.textContent = '🔥 Start Your Study Streak';
      elements.dashStreakCount.textContent = '0 Days';
      elements.dashStatSessions.textContent = '0';
      elements.dashStatQuizzes.textContent = '0';
      elements.dashStatAvgScore.textContent = '0%';
      elements.dashStatTopics.textContent = '0';
      elements.dashboardRecentActivities.innerHTML = `
        <div class="card-box" style="text-align:center; padding:24px;">
          <p style="margin-bottom:12px; color:var(--text-muted); font-size:13px;">Please sign in to view your learning activity feed.</p>
          <button class="btn btn-primary" onclick="window.AIStudentCompanion.openAuth('login')" style="font-size:12px;">Sign In</button>
        </div>
      `;
      return;
    }

    try {
      const res = await apiFetch('/api/dashboard/');
      if (res.ok) {
        const data = await res.json();
        const user = data.user;
        const metrics = data.metrics;

        elements.dashboardWelcomeMsg.textContent = `Welcome back, ${user.full_name || user.username}! Ready to master your subjects?`;
        elements.dashStreakTitle.textContent = `🔥 ${metrics.study_streak} Day Study Streak`;
        elements.dashStreakCount.textContent = `${metrics.study_streak} Days`;
        elements.dashStatSessions.textContent = metrics.study_sessions;
        elements.dashStatQuizzes.textContent = metrics.completed_quizzes;
        elements.dashStatAvgScore.textContent = `${metrics.average_score}%`;
        elements.dashStatTopics.textContent = metrics.saved_topics_count;

        // Render Recent Activities
        if (data.recent_activities && data.recent_activities.length > 0) {
          const typeIcons = {
            chat: '💬',
            quiz: '📝',
            explanation: '💡',
            interview: '🎯',
            upload: '📄',
          };
          elements.dashboardRecentActivities.innerHTML = data.recent_activities
            .map(
              (act) => `
            <div class="activity-item">
              <span class="activity-item-icon">${typeIcons[act.activity_type] || '📌'}</span>
              <div class="activity-item-content">
                <div class="activity-item-title">${escapeHtml(act.title)}</div>
                ${act.description ? `<div class="activity-item-desc">${escapeHtml(act.description)}</div>` : ''}
              </div>
              <span class="activity-item-time">${formatDate(act.created_at)}</span>
            </div>
          `
            )
            .join('');
        } else {
          elements.dashboardRecentActivities.innerHTML = `
            <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
              No activities logged yet. Start a chat or take an MCQ quiz!
            </div>
          `;
        }

        // Render Recent Quizzes
        if (data.recent_quizzes && data.recent_quizzes.length > 0) {
          elements.dashboardRecentQuizzes.innerHTML = data.recent_quizzes
            .map(
              (q) => `
            <div class="activity-item">
              <span class="activity-item-icon">📝</span>
              <div class="activity-item-content">
                <div class="activity-item-title">${escapeHtml(q.topic)}</div>
                <div class="activity-item-desc">Score: ${q.score}/${q.total_questions} (${q.percentage}%) • ${q.difficulty}</div>
              </div>
              <span class="activity-item-time">${formatDate(q.created_at)}</span>
            </div>
          `
            )
            .join('');
        } else {
          elements.dashboardRecentQuizzes.innerHTML = `
            <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
              No quizzes completed yet.
            </div>
          `;
        }
      }
    } catch (err) {
      console.warn('Dashboard fetch error:', err);
    }
  }

  // ---------------------------------------------------------------------------
  // Feature 3: AI Topic Explainer
  // ---------------------------------------------------------------------------
  async function handleGenerateExplanation() {
    const topic = elements.explainerTopicInput.value.trim();
    if (!topic) {
      showToast('Please enter a topic to explain', 'error');
      elements.explainerTopicInput.focus();
      return;
    }

    const subject = elements.explainerSubjectSelect.value;
    const level = elements.explainerLevelSelect.value;

    elements.btnGenerateExplanation.disabled = true;
    elements.btnGenerateExplanation.innerHTML = `<span>Thinking...</span>`;

    try {
      const res = await apiFetch('/api/tools/explain/', {
        method: 'POST',
        body: JSON.stringify({ topic, subject, level }),
      });

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        state.currentExplanation = data.explanation;
        renderExplanationResult(data.explanation);
        showToast(`Topic explanation generated for '${topic}'!`, 'success');
      } else {
        const isRateLimit = res.status === 429 || data.error_code === 'RATE_LIMITED';
        const msg = data.error || (isRateLimit ? '⚡ Groq API rate limit reached. Please wait a few seconds and try again.' : 'Failed to explain topic');
        showToast(msg, isRateLimit ? 'warning' : 'error');
      }
    } catch (err) {
      showToast('Network error while generating explanation', 'error');
    } finally {
      elements.btnGenerateExplanation.disabled = false;
      elements.btnGenerateExplanation.innerHTML = `<span>Explain Topic</span>`;
    }
  }

  function renderExplanationResult(exp) {
    if (!elements.explainerResultsArea) return;
    elements.explainerResultsArea.style.display = 'block';

    elements.explainerResultTitle.textContent = exp.topic;
    elements.explainerResultBadge.textContent = `${exp.subject} • ${exp.level}`;

    elements.explainerSectionSummary.innerHTML = renderMarkdown(exp.summary || 'Summary unavailable.');
    elements.explainerSectionDetail.innerHTML = renderMarkdown(exp.detailed_explanation || 'Explanation unavailable.');
    elements.explainerSectionExamples.innerHTML = renderMarkdown(exp.examples || 'No examples provided.');
    elements.explainerSectionCode.innerHTML = renderMarkdown(exp.code_snippets || 'No code snippets required.');
    elements.explainerSectionTips.innerHTML = renderMarkdown(exp.interview_tips || 'No tips provided.');

    applySyntaxHighlighting(elements.explainerResultsArea);
    elements.explainerResultsArea.scrollIntoView({ behavior: 'smooth' });
  }

  async function handleSaveExplanation() {
    if (!state.currentExplanation) return;
    if (!state.currentUser) {
      showToast('Please sign in to bookmark explanations', 'info');
      openAuthModal('login');
      return;
    }

    try {
      const res = await apiFetch('/api/tools/save-explanation/', {
        method: 'POST',
        body: JSON.stringify(state.currentExplanation),
      });
      const data = await res.json();
      if (res.ok) {
        showToast('Explanation saved to your study profile!', 'success');
        loadSavedExplanations();
      } else {
        showToast(data.error || 'Could not save explanation', 'error');
      }
    } catch (err) {
      showToast('Error saving explanation', 'error');
    }
  }

  async function loadSavedExplanations() {
    if (!elements.savedExplanationsList) return;
    if (!state.currentUser) {
      elements.savedExplanationsList.innerHTML = `
        <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
          Sign in to view your saved explanations.
        </div>
      `;
      return;
    }

    try {
      const res = await apiFetch('/api/tools/explanations/');
      if (res.ok) {
        const data = await res.json();
        const list = data.explanations || [];
        if (list.length === 0) {
          elements.savedExplanationsList.innerHTML = `
            <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
              No saved explanations yet.
            </div>
          `;
          return;
        }

        elements.savedExplanationsList.innerHTML = list
          .map(
            (item) => `
          <div class="activity-item" style="justify-content:space-between; align-items:center;">
            <div style="min-width:0; flex:1;">
              <div class="activity-item-title">${escapeHtml(item.topic)}</div>
              <div class="activity-item-desc">${escapeHtml(item.subject)} • ${formatDate(item.created_at)}</div>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-secondary" onclick="window.AIStudentCompanion.viewSavedExp('${item.id}')" style="font-size:12px; padding:4px 10px;">View</button>
              <button class="icon-btn" onclick="window.AIStudentCompanion.confirmDelete('explanation', '${item.id}')" title="Delete">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </div>
        `
          )
          .join('');
      }
    } catch (err) {
      console.warn('Explanations list load error:', err);
    }
  }

  // ---------------------------------------------------------------------------
  // Feature 4: Interview Preparation
  // ---------------------------------------------------------------------------
  async function handleGenerateInterview() {
    const subject = elements.interviewSubjectInput.value.trim();
    const role = elements.interviewRoleInput.value.trim();
    if (!subject || !role) {
      showToast('Please specify both subject and target role', 'error');
      return;
    }

    const difficulty = elements.interviewDiffSelect.value;

    elements.btnGenerateInterview.disabled = true;
    elements.btnGenerateInterview.innerHTML = `<span>Preparing Questions...</span>`;

    try {
      const res = await apiFetch('/api/tools/interview-prep/', {
        method: 'POST',
        body: JSON.stringify({ subject, role, difficulty, count: 5 }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        renderInterviewResult(data.interview);
        showToast('Technical interview questions ready!', 'success');
        loadInterviewHistory();
      } else {
        const isRateLimit = res.status === 429 || data.error_code === 'RATE_LIMITED';
        const msg = data.error || (isRateLimit ? '⚡ Groq API rate limit reached. Please wait a few seconds and try again.' : 'Failed to generate interview prep');
        showToast(msg, isRateLimit ? 'warning' : 'error');
      }
    } catch (err) {
      showToast('Network error while generating interview prep', 'error');
    } finally {
      elements.btnGenerateInterview.disabled = false;
      elements.btnGenerateInterview.innerHTML = `<span>Generate Questions</span>`;
    }
  }

  function renderInterviewResult(prep) {
    if (!elements.interviewResultsArea) return;
    elements.interviewResultsArea.style.display = 'block';

    elements.interviewResultRole.textContent = `${prep.role} • ${prep.subject}`;
    elements.interviewResultBadge.textContent = prep.difficulty;

    // Preparation Tips
    const tips = prep.preparation_tips || [];
    elements.interviewTipsList.innerHTML = tips.map((t) => `<li>${escapeHtml(t)}</li>`).join('');

    // Questions Accordion
    const questions = prep.questions || [];
    elements.interviewQuestionsAccordion.innerHTML = questions
      .map(
        (q, idx) => `
      <div class="interview-item" id="interview-item-${idx}">
        <div class="interview-question-header" onclick="window.AIStudentCompanion.toggleInterviewAccordion(${idx})">
          <span>Q${idx + 1}: ${escapeHtml(q.question)}</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
        <div class="interview-answer-body">
          <div class="markdown-body">${renderMarkdown(q.answer || '')}</div>
          ${
            q.key_talking_points && q.key_talking_points.length > 0
              ? `<div style="margin-top:14px; font-weight:600; color:var(--text-primary); font-size:12px;">KEY TALKING POINTS:</div>
                 <ul class="talking-points-list">${q.key_talking_points.map((pt) => `<li>${escapeHtml(pt)}</li>`).join('')}</ul>`
              : ''
          }
          ${
            q.follow_up_questions && q.follow_up_questions.length > 0
              ? `<div style="margin-top:14px; font-weight:600; color:var(--text-primary); font-size:12px;">POTENTIAL FOLLOW-UPS:</div>
                 <ul class="talking-points-list">${q.follow_up_questions.map((f) => `<li>${escapeHtml(f)}</li>`).join('')}</ul>`
              : ''
          }
        </div>
      </div>
    `
      )
      .join('');

    applySyntaxHighlighting(elements.interviewQuestionsAccordion);
    elements.interviewResultsArea.scrollIntoView({ behavior: 'smooth' });
  }

  function toggleInterviewAccordion(idx) {
    const item = document.getElementById(`interview-item-${idx}`);
    if (item) {
      item.classList.toggle('open');
    }
  }

  async function loadInterviewHistory() {
    if (!elements.pastInterviewSessionsList) return;
    if (!state.currentUser) {
      elements.pastInterviewSessionsList.innerHTML = `
        <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
          Sign in to view your interview preparation history.
        </div>
      `;
      return;
    }

    try {
      const res = await apiFetch('/api/tools/interview-sessions/');
      if (res.ok) {
        const data = await res.json();
        const list = data.sessions || [];
        if (list.length === 0) {
          elements.pastInterviewSessionsList.innerHTML = `
            <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
              No interview sessions recorded yet.
            </div>
          `;
          return;
        }

        elements.pastInterviewSessionsList.innerHTML = list
          .map(
            (item) => `
          <div class="activity-item" style="justify-content:space-between; align-items:center;">
            <div style="min-width:0; flex:1;">
              <div class="activity-item-title">${escapeHtml(item.role)} - ${escapeHtml(item.subject)}</div>
              <div class="activity-item-desc">${item.question_count} questions • ${item.difficulty} • ${formatDate(item.created_at)}</div>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-secondary" onclick="window.AIStudentCompanion.viewInterviewSession('${item.id}')" style="font-size:12px; padding:4px 10px;">Review</button>
              <button class="icon-btn" onclick="window.AIStudentCompanion.confirmDelete('interview', '${item.id}')" title="Delete">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </div>
        `
          )
          .join('');
      }
    } catch (err) {
      console.warn('Interview history load error:', err);
    }
  }

  // ---------------------------------------------------------------------------
  // Feature 5: MCQ Quiz Generator
  // ---------------------------------------------------------------------------
  async function handleGenerateQuiz(customTopic = null, fileId = null) {
    const topic = customTopic || elements.quizTopicInput.value.trim();
    if (!topic) {
      showToast('Please enter a quiz topic', 'error');
      elements.quizTopicInput.focus();
      return;
    }

    const numQuestions = elements.quizCountSelect ? elements.quizCountSelect.value : 5;
    const difficulty = elements.quizDiffSelect ? elements.quizDiffSelect.value : 'Medium';

    elements.btnGenerateQuiz.disabled = true;
    elements.btnGenerateQuiz.innerHTML = `<span>Creating Quiz...</span>`;

    // Hide any previous results
    elements.quizResultsBanner.style.display = 'none';

    try {
      const payload = {
        topic,
        num_questions: parseInt(numQuestions, 10),
        difficulty,
      };
      if (fileId) payload.file_id = fileId;

      const res = await apiFetch('/api/quiz/generate/', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        state.currentQuiz = {
          quiz_id: data.quiz_id,
          topic: data.quiz.topic,
          difficulty: data.quiz.difficulty,
          questions: data.quiz.questions,
          userAnswers: {},
        };
        renderActiveQuiz(state.currentQuiz);
        showToast(`Quiz generated: ${data.quiz.total_questions} questions ready!`, 'success');
      } else {
        const isRateLimit = res.status === 429 || data.error_code === 'RATE_LIMITED';
        const msg = data.error || (isRateLimit ? '⚡ Groq API rate limit reached. Please wait a few seconds and try again.' : 'Failed to generate quiz');
        showToast(msg, isRateLimit ? 'warning' : 'error');
      }
    } catch (err) {
      showToast('Network error while generating quiz', 'error');
    } finally {
      elements.btnGenerateQuiz.disabled = false;
      elements.btnGenerateQuiz.innerHTML = `<span>Generate Quiz</span>`;
    }
  }

  function renderActiveQuiz(quiz) {
    if (!elements.quizActiveArea) return;
    elements.quizActiveArea.style.display = 'block';
    elements.quizActiveTitle.textContent = quiz.topic;
    elements.quizActiveBadge.textContent = `${quiz.difficulty} • ${quiz.questions.length} Questions`;

    const letters = ['A', 'B', 'C', 'D'];
    elements.quizQuestionsList.innerHTML = quiz.questions
      .map(
        (q, qIdx) => `
      <div class="card-box" id="quiz-card-${q.id}" style="margin-bottom:16px;">
        <div style="font-size:15px; font-weight:600; color:var(--text-primary); margin-bottom:12px;">
          ${qIdx + 1}. ${escapeHtml(q.question)}
        </div>
        <div class="quiz-options-container">
          ${q.options
            .map(
              (opt, optIdx) => `
            <div class="quiz-option-label" id="opt-label-${q.id}-${letters[optIdx]}" onclick="window.AIStudentCompanion.selectQuizOption(${q.id}, '${letters[optIdx]}')">
              <span class="quiz-opt-letter">${letters[optIdx]}</span>
              <span style="flex:1;">${escapeHtml(opt)}</span>
            </div>
          `
            )
            .join('')}
        </div>
        <div id="quiz-explanation-${q.id}" style="display:none;"></div>
      </div>
    `
      )
      .join('');

    elements.quizActiveArea.scrollIntoView({ behavior: 'smooth' });
  }

  function selectQuizOption(questionId, letter) {
    if (!state.currentQuiz) return;
    state.currentQuiz.userAnswers[questionId] = letter;

    // Update styling for this question
    ['A', 'B', 'C', 'D'].forEach((l) => {
      const el = document.getElementById(`opt-label-${questionId}-${l}`);
      if (el) {
        if (l === letter) el.classList.add('selected');
        else el.classList.remove('selected');
      }
    });
  }

  async function handleSubmitQuiz() {
    if (!state.currentQuiz) return;
    const totalQ = state.currentQuiz.questions.length;
    const answeredCount = Object.keys(state.currentQuiz.userAnswers).length;

    if (answeredCount < totalQ) {
      const confirmIncomplete = confirm(
        `You have answered ${answeredCount} of ${totalQ} questions. Are you sure you want to submit?`
      );
      if (!confirmIncomplete) return;
    }

    elements.btnSubmitQuiz.disabled = true;
    elements.btnSubmitQuiz.innerHTML = `<span>Grading Quiz...</span>`;

    try {
      const res = await apiFetch('/api/quiz/submit/', {
        method: 'POST',
        body: JSON.stringify({
          quiz_id: state.currentQuiz.quiz_id,
          answers: state.currentQuiz.userAnswers,
          questions: state.currentQuiz.questions,
        }),
      });

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        renderQuizResults(data);
        showToast(`Quiz Completed! You scored ${data.score}/${data.total_questions} (${data.percentage}%)`, 'success');
        loadQuizHistory();
      } else {
        showToast(data.error || 'Failed to submit quiz', 'error');
      }
    } catch (err) {
      showToast('Network error while grading quiz', 'error');
    } finally {
      elements.btnSubmitQuiz.disabled = false;
      elements.btnSubmitQuiz.innerHTML = `<span>Submit Quiz for Scoring</span>`;
    }
  }

  function renderQuizResults(data) {
    if (!elements.quizResultsBanner) return;

    elements.quizResultsBanner.style.display = 'block';
    elements.quizScoreText.textContent = `Score: ${data.score} / ${data.total_questions} (${data.percentage}%)`;

    if (data.percentage >= 80) {
      elements.quizScoreIcon.textContent = '🌟';
      elements.quizFeedbackText.textContent = 'Mastery achieved! Outstanding work on this topic.';
    } else if (data.percentage >= 60) {
      elements.quizScoreIcon.textContent = '👍';
      elements.quizFeedbackText.textContent = 'Good job! A solid score, review the explanations below to polish weak areas.';
    } else {
      elements.quizScoreIcon.textContent = '📚';
      elements.quizFeedbackText.textContent = 'Keep practicing! Review the detailed solutions below to master this concept.';
    }

    // Highlight each question's result
    const results = data.results || [];
    results.forEach((r) => {
      const correctLetter = r.correct_answer;
      const userLetter = r.user_answer;

      ['A', 'B', 'C', 'D'].forEach((l) => {
        const optEl = document.getElementById(`opt-label-${r.id}-${l}`);
        if (optEl) {
          optEl.onclick = null; // disable further clicks
          optEl.classList.remove('selected');
          if (l === correctLetter) {
            optEl.classList.add('correct');
          } else if (l === userLetter && !r.is_correct) {
            optEl.classList.add('wrong');
          }
        }
      });

      // Show explanation
      const expBox = document.getElementById(`quiz-explanation-${r.id}`);
      if (expBox) {
        expBox.style.display = 'block';
        expBox.className = 'quiz-explanation-box';
        expBox.innerHTML = `<strong>Explanation:</strong> ${escapeHtml(r.explanation)}`;
      }
    });

    elements.btnSubmitQuiz.style.display = 'none';
    elements.quizResultsBanner.scrollIntoView({ behavior: 'smooth' });
  }

  async function loadQuizHistory() {
    if (!elements.pastQuizzesList) return;
    if (!state.currentUser) {
      elements.pastQuizzesList.innerHTML = `
        <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
          Sign in to view your quiz history and score analytics.
        </div>
      `;
      return;
    }

    try {
      const res = await apiFetch('/api/quiz/history/');
      if (res.ok) {
        const data = await res.json();
        const list = data.history || [];
        if (list.length === 0) {
          elements.pastQuizzesList.innerHTML = `
            <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
              No quiz records yet. Test your knowledge above!
            </div>
          `;
          return;
        }

        elements.pastQuizzesList.innerHTML = list
          .map(
            (item) => `
          <div class="activity-item" style="justify-content:space-between; align-items:center;">
            <div style="min-width:0; flex:1;">
              <div class="activity-item-title">${escapeHtml(item.topic)}</div>
              <div class="activity-item-desc">Score: ${item.score}/${item.total_questions} (${item.percentage}%) • ${item.difficulty} • ${formatDate(item.created_at)}</div>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-secondary" onclick="window.AIStudentCompanion.reviewPastQuiz('${item.id}')" style="font-size:12px; padding:4px 10px;">Review</button>
              <button class="icon-btn" onclick="window.AIStudentCompanion.confirmDelete('quiz', '${item.id}')" title="Delete">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </div>
        `
          )
          .join('');
      }
    } catch (err) {
      console.warn('Quiz history load error:', err);
    }
  }

  // ---------------------------------------------------------------------------
  // Feature 7: File Upload inside AI Chat
  // ---------------------------------------------------------------------------
  async function handleFileUpload(file) {
    if (!file) return;

    // Validate extension
    const allowed = ['pdf', 'docx', 'txt', 'jpg', 'jpeg', 'png'];
    const ext = file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      showToast(`Unsupported format .${ext}. Please upload PDF, Word, TXT, or Image files.`, 'error');
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      showToast('File exceeds 20MB limit', 'error');
      return;
    }

    // Show preview bar with loading status
    elements.composerFilePreview.classList.add('active');
    elements.fileNameBadge.textContent = file.name;
    elements.fileStatusBadge.textContent = 'Extracting document text & running OCR...';
    elements.fileIconBadge.textContent = ['jpg', 'jpeg', 'png'].includes(ext) ? '🖼️' : '📄';

    const formData = new FormData();
    formData.append('file', file);
    if (state.currentConversationId) {
      formData.append('conversation_id', state.currentConversationId);
    }

    try {
      const res = await apiFetch('/api/chat/upload/', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        state.attachedFile = data.file;
        if (!state.currentConversationId && data.conversation_id) {
          state.currentConversationId = data.conversation_id;
        }

        elements.fileStatusBadge.textContent = `✓ ${data.extracted_info.word_count.toLocaleString()} words extracted`;
        elements.filePillsRow.style.display = 'flex';
        showToast(`Extracted ${data.extracted_info.word_count} words from '${file.name}'`, 'success');
      } else {
        showToast(data.error || 'Failed to extract file text', 'error');
        removeAttachedFile();
      }
    } catch (err) {
      showToast('Network error while uploading file', 'error');
      removeAttachedFile();
    }
  }

  function removeAttachedFile() {
    state.attachedFile = null;
    elements.composerFilePreview.classList.remove('active');
    elements.filePillsRow.style.display = 'none';
    if (elements.fileUploadInput) elements.fileUploadInput.value = '';
  }

  async function handleFileQuickAction(action) {
    if (!state.attachedFile) {
      showToast('Please attach a document first', 'error');
      return;
    }

    if (action === 'mcq') {
      // Navigate to Quiz View and trigger generation from document
      switchView('quiz');
      handleGenerateQuiz(`Material from ${state.attachedFile.filename}`, state.attachedFile.id);
      return;
    }

    let promptText = '';
    if (action === 'summary') {
      promptText = `Please provide a comprehensive study summary of the uploaded document '${state.attachedFile.filename}'.`;
    } else if (action === 'important_questions') {
      promptText = `Extract the most important study and exam questions with comprehensive answers based on '${state.attachedFile.filename}'.`;
    }

    if (promptText) {
      sendMessage(promptText);
    }
  }

  // ---------------------------------------------------------------------------
  // Feature 8: Unified Learning History
  // ---------------------------------------------------------------------------
  async function loadLearningHistory(type = 'all', searchQuery = '') {
    if (!elements.historyItemsContainer) return;
    if (!state.currentUser) {
      elements.historyItemsContainer.innerHTML = `
        <div class="card-box" style="text-align:center; padding:32px;">
          <p style="margin-bottom:14px; color:var(--text-muted); font-size:14px;">Sign in to view and manage your complete learning history.</p>
          <button class="btn btn-primary" onclick="window.AIStudentCompanion.openAuth('login')">Sign In</button>
        </div>
      `;
      return;
    }

    elements.historyItemsContainer.innerHTML = `
      <div class="card-box" style="text-align:center; color:var(--text-muted); font-size:13px;">
        Searching your learning history...
      </div>
    `;

    try {
      const url = `/api/history/?type=${encodeURIComponent(type)}&q=${encodeURIComponent(searchQuery)}`;
      const res = await apiFetch(url);
      if (res.ok) {
        const data = await res.json();
        renderLearningHistoryItems(data);
      }
    } catch (err) {
      console.warn('Learning history load error:', err);
    }
  }

  function renderLearningHistoryItems(data) {
    const allItems = [];

    // Chats
    (data.chats || []).forEach((c) => {
      allItems.push({
        kind: 'chat',
        id: c.id,
        icon: '💬',
        badge: 'Chat',
        title: c.title,
        snippet: c.snippet || 'Chat conversation',
        date: c.updated_at || c.created_at,
      });
    });

    // Explanations
    (data.explanations || []).forEach((e) => {
      allItems.push({
        kind: 'explanation',
        id: e.id,
        icon: '💡',
        badge: 'Explanation',
        title: e.title,
        snippet: `${e.subject} • ${e.snippet}`,
        date: e.created_at,
      });
    });

    // Interviews
    (data.interviews || []).forEach((i) => {
      allItems.push({
        kind: 'interview',
        id: i.id,
        icon: '🎯',
        badge: 'Interview',
        title: i.title,
        snippet: `${i.question_count} questions • ${i.difficulty}`,
        date: i.created_at,
      });
    });

    // Quizzes
    (data.quizzes || []).forEach((q) => {
      allItems.push({
        kind: 'quiz',
        id: q.id,
        icon: '📝',
        badge: 'Quiz',
        title: q.title,
        snippet: `Score: ${q.score}/${q.total_questions} (${q.percentage}%) • ${q.difficulty}`,
        date: q.created_at,
      });
    });

    // Sort by date descending
    allItems.sort((a, b) => new Date(b.date) - new Date(a.date));

    if (allItems.length === 0) {
      elements.historyItemsContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📜</div>
          <div class="empty-state-title">No matching records found</div>
          <div class="empty-state-desc">Your chats, saved explanations, interview sessions, and quizzes will appear here.</div>
        </div>
      `;
      return;
    }

    elements.historyItemsContainer.innerHTML = allItems
      .map(
        (item) => `
      <div class="history-card">
        <div class="history-card-left">
          <span class="history-card-icon">${item.icon}</span>
          <div class="history-card-info">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="history-card-title">${escapeHtml(item.title)}</span>
              <span class="badge-pill" style="font-size:10px;">${item.badge}</span>
            </div>
            <div class="history-card-snippet">${escapeHtml(item.snippet)}</div>
            <div class="history-card-meta">${formatDate(item.date)}</div>
          </div>
        </div>
        <div class="history-card-actions">
          <button class="btn btn-secondary" onclick="window.AIStudentCompanion.reopenHistoryItem('${item.kind}', '${item.id}')" style="font-size:12px; padding:5px 12px;">Reopen</button>
          <button class="icon-btn" onclick="window.AIStudentCompanion.confirmDelete('${item.kind}', '${item.id}')" title="Delete">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      </div>
    `
      )
      .join('');
  }

  async function reopenHistoryItem(kind, id) {
    if (kind === 'chat') {
      switchView('chat');
      loadConversation(id);
    } else if (kind === 'explanation') {
      try {
        const res = await apiFetch(`/api/tools/explanations/${id}/`);
        if (res.ok) {
          const data = await res.json();
          switchView('explainer');
          state.currentExplanation = data.explanation;
          renderExplanationResult(data.explanation);
        }
      } catch (err) {
        showToast('Error opening explanation', 'error');
      }
    } else if (kind === 'interview') {
      try {
        const res = await apiFetch(`/api/tools/interview-sessions/${id}/`);
        if (res.ok) {
          const data = await res.json();
          switchView('interview');
          renderInterviewResult(data.session.data);
        }
      } catch (err) {
        showToast('Error opening interview session', 'error');
      }
    } else if (kind === 'quiz') {
      try {
        const res = await apiFetch(`/api/quiz/${id}/`);
        if (res.ok) {
          const data = await res.json();
          switchView('quiz');
          renderQuizResults({
            score: data.quiz.score,
            total_questions: data.quiz.total_questions,
            percentage: data.quiz.percentage,
            results: data.quiz.questions_data,
          });
        }
      } catch (err) {
        showToast('Error opening quiz', 'error');
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Delete Dialog Handling
  // ---------------------------------------------------------------------------
  function confirmDelete(type, id) {
    state.deleteTarget = { type, id };
    const titles = {
      conversation: 'Delete conversation?',
      explanation: 'Delete saved explanation?',
      interview: 'Delete interview session?',
      quiz: 'Delete quiz result?',
    };
    if (elements.deleteModalTitle) {
      elements.deleteModalTitle.textContent = titles[type] || 'Delete item?';
    }
    if (elements.deleteModal) {
      elements.deleteModal.classList.add('active');
    }
  }

  async function executeDelete() {
    if (!state.deleteTarget) return;
    const { type, id } = state.deleteTarget;
    elements.deleteModal.classList.remove('active');

    try {
      let endpoint = '';
      if (type === 'conversation') endpoint = `/api/conversations/${id}/`;
      else if (type === 'explanation') endpoint = `/api/tools/explanations/${id}/`;
      else if (type === 'interview') endpoint = `/api/tools/interview-sessions/${id}/`;
      else if (type === 'quiz') endpoint = `/api/quiz/${id}/`;

      const res = await apiFetch(endpoint, { method: 'DELETE' });
      if (res.ok) {
        showToast('Item deleted successfully', 'success');
        if (type === 'conversation') {
          if (state.currentConversationId === id) createNewConversation();
          fetchConversations();
        } else if (type === 'explanation') {
          loadSavedExplanations();
        } else if (type === 'interview') {
          loadInterviewHistory();
        } else if (type === 'quiz') {
          loadQuizHistory();
        }

        if (state.activeView === 'history') {
          const activeFilter = document.querySelector('.history-filter-btn.active');
          loadLearningHistory(activeFilter ? activeFilter.getAttribute('data-type') : 'all');
        }
      } else {
        showToast('Failed to delete item', 'error');
      }
    } catch (err) {
      showToast('Error deleting item', 'error');
    } finally {
      state.deleteTarget = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Feature 6: AI Chat Clear & Management
  // ---------------------------------------------------------------------------
  async function handleClearChat() {
    if (!state.currentConversationId) {
      elements.chatInner.innerHTML = '';
      elements.welcomeScreen.style.display = 'flex';
      removeAttachedFile();
      return;
    }

    try {
      const res = await apiFetch(`/api/conversations/${state.currentConversationId}/clear/`, {
        method: 'POST',
      });
      if (res.ok) {
        elements.chatInner.innerHTML = '';
        elements.welcomeScreen.style.display = 'flex';
        elements.activeChatTitle.textContent = 'New Chat';
        removeAttachedFile();
        showToast('Conversation cleared', 'info');
        fetchConversations();
      } else {
        showToast('Failed to clear conversation', 'error');
      }
    } catch (err) {
      showToast('Error clearing chat', 'error');
    }
  }

  // ---------------------------------------------------------------------------
  // Message Rendering & Sending in AI Chat
  // ---------------------------------------------------------------------------
  function appendMessageRow(role, content, meta = {}) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;
    if (meta.messageId) row.setAttribute('data-message-id', meta.messageId);

    const isUser = role === 'user';
    const avatar = isUser
      ? `<div class="msg-avatar user">U</div>`
      : `<div class="msg-avatar ai"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg></div>`;

    const bodyHtml = isUser
      ? `<div class="message-text">${escapeHtml(content).replace(/\n/g, '<br/>')}</div>`
      : `<div class="markdown-body">${renderMarkdown(content)}</div>`;

    const actionsHtml = isUser
      ? ''
      : `
        <div class="message-actions">
          <button class="msg-action-btn btn-copy-msg" type="button" title="Copy response" aria-label="Copy response">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          </button>
          <button class="msg-action-btn btn-regenerate-msg" type="button" title="Regenerate response" aria-label="Regenerate response">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"></polyline><polyline points="23 20 23 14 17 14"></polyline><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"></path></svg>
          </button>
        </div>
      `;

    row.innerHTML = `
      ${avatar}
      <div class="message-bubble-wrapper">
        <div class="message-bubble">${bodyHtml}</div>
        ${actionsHtml}
      </div>
    `;

    elements.chatInner.appendChild(row);

    if (!isUser) {
      applySyntaxHighlighting(row);
      const copyBtn = row.querySelector('.btn-copy-msg');
      if (copyBtn) {
        copyBtn.addEventListener('click', () => {
          copyToClipboard(content).then(() => showToast('Response copied to clipboard', 'success'));
        });
      }
      const regenBtn = row.querySelector('.btn-regenerate-msg');
      if (regenBtn) {
        regenBtn.addEventListener('click', regenerateLastResponse);
      }
    }

    return row;
  }

  function appendTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'message-row assistant typing-indicator-row';
    row.innerHTML = `
      <div class="msg-avatar ai">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
      </div>
      <div class="message-bubble-wrapper">
        <div class="message-bubble">
          <div class="typing-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
      </div>
    `;
    elements.chatInner.appendChild(row);
    return row;
  }

  function appendErrorBanner(message, options = {}) {
    let isConfigError = false;
    let isRateLimit = false;
    let retryAfter = 0;
    let userText = '';

    if (typeof options === 'boolean') {
      isConfigError = options;
    } else if (typeof options === 'object' && options !== null) {
      isConfigError = !!options.isConfigError;
      isRateLimit = !!options.isRateLimit;
      retryAfter = typeof options.retryAfter === 'number' ? options.retryAfter : 0;
      userText = options.userText || '';
    }

    if (message && message.toLowerCase().includes('rate limit')) {
      isRateLimit = true;
    }

    const banner = document.createElement('div');
    banner.className = `error-banner ${isRateLimit ? 'rate-limit' : ''}`;

    const iconSvg = isRateLimit
      ? `<svg class="error-icon rate-limit" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
           <circle cx="12" cy="12" r="10"></circle>
           <polyline points="12 6 12 12 16 14"></polyline>
         </svg>`
      : `<svg class="error-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5">
           <circle cx="12" cy="12" r="10"></circle>
           <line x1="12" y1="8" x2="12" y2="12"></line>
           <line x1="12" y1="16" x2="12.01" y2="16"></line>
         </svg>`;

    banner.innerHTML = `
      <div class="error-banner-content">
        ${iconSvg}
        <div style="flex:1;">
          <div style="font-weight:600; margin-bottom:2px;">
            ${isRateLimit ? '⚡ Groq API Rate Limit Reached' : 'Request Notice'}
          </div>
          <div>${escapeHtml(message)}</div>
        </div>
      </div>
      <div class="error-banner-actions">
        ${
          userText
            ? `<button class="btn-retry-banner" id="btn-retry-msg" type="button">
                 <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                 <span>Retry Message</span>
               </button>
               <button class="btn-restore-banner" id="btn-restore-msg" type="button">
                 <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                 <span>Restore to Input</span>
               </button>`
            : ''
        }
        ${
          isConfigError || isRateLimit
            ? `<button class="btn-restore-banner" onclick="document.getElementById('settings-modal').classList.add('active')" type="button">
                 <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                 <span>API Settings</span>
               </button>`
            : ''
        }
      </div>
    `;

    elements.chatInner.appendChild(banner);
    scrollToBottom();

    // Hook up retry button if userText provided
    if (userText) {
      const btnRetry = banner.querySelector('#btn-retry-msg');
      const btnRestore = banner.querySelector('#btn-restore-msg');

      if (btnRestore) {
        btnRestore.addEventListener('click', () => {
          elements.messageInput.value = userText;
          updateComposerState();
          elements.messageInput.focus();
          showToast('Message restored to input box', 'info');
        });
      }

      if (btnRetry) {
        if (retryAfter > 0) {
          btnRetry.disabled = true;
          let remaining = Math.ceil(retryAfter);
          const span = btnRetry.querySelector('span');
          span.textContent = `Wait ${remaining}s...`;
          const timer = setInterval(() => {
            remaining -= 1;
            if (remaining > 0) {
              span.textContent = `Wait ${remaining}s...`;
            } else {
              clearInterval(timer);
              btnRetry.disabled = false;
              span.textContent = 'Retry Message';
            }
          }, 1000);
        }

        btnRetry.addEventListener('click', () => {
          banner.remove();
          sendMessage(userText);
        });
      }
    }
  }

  async function sendMessage(text) {
    const cleanText = (text || '').trim();
    // 1. Debounce and synchronous duplicate prevention
    if (!cleanText || state.isGenerating) return;

    // Immediately mark generating and disable send button synchronously
    state.isGenerating = true;
    if (elements.btnSend) elements.btnSend.disabled = true;
    setGeneratingUI(true);

    // Save prompt to state so it is never lost on error
    state.lastSentUserMessage = cleanText;

    // Clear message input
    elements.messageInput.value = '';
    updateComposerState();
    elements.welcomeScreen.style.display = 'none';

    // Append user message
    appendMessageRow('user', cleanText);
    const typingRow = appendTypingIndicator();
    scrollToBottom();

    state.abortController = new AbortController();

    try {
      const payload = {
        message: cleanText,
        conversation_id: state.currentConversationId,
        model: state.activeModel,
      };

      if (state.attachedFile) {
        payload.file_id = state.attachedFile.id;
      }
      if (state.userApiKey) {
        payload.api_key = state.userApiKey;
      }

      const res = await apiFetch('/api/chat/', {
        method: 'POST',
        body: JSON.stringify(payload),
        signal: state.abortController.signal,
      });

      typingRow.remove();

      if (res.ok) {
        const data = await res.json();
        state.currentConversationId = data.conversation_id;
        elements.activeChatTitle.textContent = data.conversation_title;

        appendMessageRow('assistant', data.assistant_message.content, {
          model: data.model,
          messageId: data.assistant_message.id,
        });

        fetchConversations();
      } else {
        const errData = await res.json().catch(() => ({}));
        const isRateLimit = res.status === 429 || errData.error_code === 'RATE_LIMITED';
        const isConfigError = res.status === 401 || errData.error_code === 'MISSING_API_KEY' || errData.error_code === 'INVALID_API_KEY';
        const errorMsg = errData.error || (isRateLimit ? 'Groq API rate limit reached. Please wait a moment.' : `Server error (${res.status})`);
        if (errData.conversation_id) state.currentConversationId = errData.conversation_id;

        // Render banner preserving userText with Retry and Restore actions
        appendErrorBanner(errorMsg, {
          isConfigError,
          isRateLimit,
          retryAfter: errData.retry_after,
          userText: cleanText,
        });

        if (isRateLimit) {
          showToast('Groq rate limit reached. Your message is preserved.', 'warning');
        }
      }
    } catch (err) {
      typingRow.remove();
      if (err.name === 'AbortError') {
        showToast('Generation stopped', 'info');
      } else {
        appendErrorBanner(`Network error: ${err.message}`, {
          userText: cleanText,
        });
      }
    } finally {
      state.isGenerating = false;
      setGeneratingUI(false);
      state.abortController = null;
      updateComposerState();
      scrollToBottom();
    }
  }

  async function regenerateLastResponse() {
    if (!state.currentConversationId || state.isGenerating) return;

    const lastAiRow = elements.chatInner.querySelector('.message-row.assistant:last-child');
    if (lastAiRow) lastAiRow.remove();

    const typingRow = appendTypingIndicator();
    scrollToBottom();

    state.isGenerating = true;
    setGeneratingUI(true);
    state.abortController = new AbortController();

    try {
      const payload = {
        conversation_id: state.currentConversationId,
        model: state.activeModel,
      };
      if (state.userApiKey) payload.api_key = state.userApiKey;

      const res = await apiFetch('/api/chat/regenerate/', {
        method: 'POST',
        body: JSON.stringify(payload),
        signal: state.abortController.signal,
      });

      typingRow.remove();

      if (res.ok) {
        const data = await res.json();
        appendMessageRow('assistant', data.assistant_message.content, {
          model: data.model,
          messageId: data.assistant_message.id,
        });
      } else {
        const errData = await res.json().catch(() => ({}));
        const isRateLimit = res.status === 429 || errData.error_code === 'RATE_LIMITED';
        appendErrorBanner(errData.error || 'Failed to regenerate response', {
          isRateLimit,
          retryAfter: errData.retry_after,
        });
      }
    } catch (err) {
      typingRow.remove();
      if (err.name === 'AbortError') showToast('Regeneration stopped', 'info');
      else appendErrorBanner(`Network error: ${err.message}`);
    } finally {
      state.isGenerating = false;
      setGeneratingUI(false);
      state.abortController = null;
      updateComposerState();
      scrollToBottom();
    }
  }

  function setGeneratingUI(isGenerating) {
    if (elements.btnSend) elements.btnSend.style.display = isGenerating ? 'none' : 'flex';
    if (elements.btnStop) elements.btnStop.style.display = isGenerating ? 'flex' : 'none';
  }

  function updateComposerState() {
    const text = elements.messageInput.value;
    const len = text.length;
    if (elements.charCounter) elements.charCounter.textContent = `${len.toLocaleString()} chars`;
    if (elements.btnSend) elements.btnSend.disabled = len === 0 || state.isGenerating;

    // Auto-grow textarea
    elements.messageInput.style.height = 'auto';
    elements.messageInput.style.height = `${Math.min(elements.messageInput.scrollHeight, 180)}px`;
  }

  // ---------------------------------------------------------------------------
  // Conversations Sidebar Management
  // ---------------------------------------------------------------------------
  async function fetchConversations(searchQuery = '') {
    try {
      const endpoint = searchQuery
        ? `/api/conversations/?q=${encodeURIComponent(searchQuery)}`
        : '/api/conversations/';
      const res = await apiFetch(endpoint);
      if (res.ok) {
        const data = await res.json();
        state.conversations = data.conversations || [];
        renderConversationList();
      }
    } catch (err) {
      console.warn('Conversations fetch error:', err);
    }
  }

  function renderConversationList() {
    if (!elements.conversationList) return;

    if (state.conversations.length === 0) {
      elements.conversationList.innerHTML = `<div class="history-empty">No conversations yet</div>`;
      return;
    }

    elements.conversationList.innerHTML = state.conversations
      .map((conv) => {
        const isActive = conv.id === state.currentConversationId;
        return `
        <div class="conv-item ${isActive ? 'active' : ''}" data-id="${conv.id}">
          <div class="conv-item-main" onclick="window.AIStudentCompanion.loadConv('${conv.id}')">
            <svg class="conv-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span class="conv-title">${escapeHtml(conv.title)}</span>
          </div>
          <div class="conv-actions">
            <button class="icon-btn btn-rename" onclick="event.stopPropagation(); window.AIStudentCompanion.renameConv('${conv.id}', '${escapeHtml(conv.title)}')" title="Rename">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
            </button>
            <button class="icon-btn btn-delete" onclick="event.stopPropagation(); window.AIStudentCompanion.confirmDelete('conversation', '${conv.id}')" title="Delete">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
          </div>
        </div>
      `;
      })
      .join('');
  }

  async function loadConversation(id) {
    if (state.isGenerating) return;
    try {
      const res = await apiFetch(`/api/conversations/${id}/`);
      if (res.ok) {
        const data = await res.json();
        const conv = data.conversation;
        state.currentConversationId = conv.id;
        renderActiveConversation(conv);
        closeMobileSidebar();
        renderConversationList();
      }
    } catch (err) {
      showToast('Error loading conversation', 'error');
    }
  }

  function renderActiveConversation(conv) {
    elements.welcomeScreen.style.display = 'none';
    elements.chatInner.innerHTML = '';
    elements.activeChatTitle.textContent = conv.title;

    (conv.messages || []).forEach((msg) => {
      appendMessageRow(msg.role, msg.content, { messageId: msg.id });
    });

    if (conv.files && conv.files.length > 0) {
      const latestFile = conv.files[conv.files.length - 1];
      state.attachedFile = latestFile;
      elements.composerFilePreview.classList.add('active');
      elements.fileNameBadge.textContent = latestFile.filename;
      elements.fileStatusBadge.textContent = 'Attached file reference';
    } else {
      removeAttachedFile();
    }

    scrollToBottom();
  }

  function createNewConversation() {
    if (state.isGenerating) return;
    state.currentConversationId = null;
    elements.chatInner.innerHTML = '';
    elements.welcomeScreen.style.display = 'flex';
    elements.activeChatTitle.textContent = 'AI Study Chat';
    elements.messageInput.value = '';
    removeAttachedFile();
    updateComposerState();
    closeMobileSidebar();
    renderConversationList();
    elements.messageInput.focus();
  }

  async function renameConversation(id, currentTitle) {
    const newTitle = prompt('Rename conversation:', currentTitle);
    if (!newTitle || !newTitle.trim() || newTitle.trim() === currentTitle) return;

    try {
      const res = await apiFetch(`/api/conversations/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ title: newTitle.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        showToast('Conversation renamed', 'success');
        if (state.currentConversationId === id) {
          elements.activeChatTitle.textContent = data.conversation.title;
        }
        fetchConversations();
      }
    } catch (err) {
      showToast('Error renaming conversation', 'error');
    }
  }

  // ---------------------------------------------------------------------------
  // Theme & Settings
  // ---------------------------------------------------------------------------
  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('groqchat_theme', theme);

    if (elements.themeIcon) {
      elements.themeIcon.innerHTML =
        theme === 'light'
          ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`
          : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
    }
  }

  function toggleTheme() {
    applyTheme(state.theme === 'dark' ? 'light' : 'dark');
  }

  async function checkSystemStatus() {
    try {
      const res = await apiFetch('/api/status/');
      if (res.ok) {
        const data = await res.json();
        state.systemConfigured = data.is_configured;
        state.supportedModels = data.supported_models || [];

        if (elements.statusDot) {
          if (data.is_configured || state.userApiKey) {
            elements.statusDot.className = 'status-dot connected';
            elements.statusDot.title = 'Connected to Groq AI';
          } else {
            elements.statusDot.className = 'status-dot unconfigured';
            elements.statusDot.title = 'Groq API Key not configured';
          }
        }

        if (elements.selectModel) {
          elements.selectModel.innerHTML = '';
          state.supportedModels.forEach((m) => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = `${m.name}`;
            if (m.id === state.activeModel) opt.selected = true;
            elements.selectModel.appendChild(opt);
          });
        }

        const modelObj = state.supportedModels.find((m) => m.id === state.activeModel);
        const displayName = modelObj ? modelObj.name : state.activeModel;
        if (elements.modelBadge) elements.modelBadge.textContent = displayName;
        if (elements.topModelSelector) {
          elements.topModelSelector.querySelector('.model-name').textContent = displayName;
        }
      }
    } catch (err) {
      console.warn('System status check error:', err);
    }
  }

  function closeMobileSidebar() {
    if (elements.sidebar) elements.sidebar.classList.remove('mobile-open');
    if (elements.sidebarBackdrop) elements.sidebarBackdrop.classList.remove('active');
  }

  // ---------------------------------------------------------------------------
  // Event Listeners Setup
  // ---------------------------------------------------------------------------
  function setupEventListeners() {
    // Navigation bar items
    elements.navItems.forEach((btn) => {
      btn.addEventListener('click', () => {
        const view = btn.getAttribute('data-view');
        switchView(view);
      });
    });

    // Mobile sidebar toggle
    if (elements.btnToggleSidebar) {
      elements.btnToggleSidebar.addEventListener('click', () => {
        elements.sidebar.classList.toggle('mobile-open');
        elements.sidebarBackdrop.classList.toggle('active');
      });
    }

    if (elements.btnCollapseSidebar) {
      elements.btnCollapseSidebar.addEventListener('click', () => {
        elements.sidebar.classList.toggle('collapsed');
      });
    }

    if (elements.sidebarBackdrop) {
      elements.sidebarBackdrop.addEventListener('click', closeMobileSidebar);
    }

    // New Chat buttons
    if (elements.btnNewChat) elements.btnNewChat.addEventListener('click', () => { switchView('chat'); createNewConversation(); });
    if (elements.btnNewChatTop) elements.btnNewChatTop.addEventListener('click', () => { switchView('chat'); createNewConversation(); });

    // Clear Chat Button & Modal
    if (elements.btnClearChat) {
      elements.btnClearChat.addEventListener('click', () => {
        elements.clearChatModal.classList.add('active');
      });
    }
    if (elements.btnCancelClear) {
      elements.btnCancelClear.addEventListener('click', () => {
        elements.clearChatModal.classList.remove('active');
      });
    }
    if (elements.btnConfirmClear) {
      elements.btnConfirmClear.addEventListener('click', () => {
        elements.clearChatModal.classList.remove('active');
        handleClearChat();
      });
    }

    // Search chats
    if (elements.searchInput) {
      elements.searchInput.addEventListener('input', (e) => {
        fetchConversations(e.target.value);
      });
    }
    if (elements.searchClear) {
      elements.searchClear.addEventListener('click', () => {
        elements.searchInput.value = '';
        fetchConversations();
      });
    }

    // Chat Composer
    if (elements.messageInput) {
      elements.messageInput.addEventListener('input', updateComposerState);
      elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage(elements.messageInput.value);
        }
      });
    }
    if (elements.btnSend) {
      elements.btnSend.addEventListener('click', () => sendMessage(elements.messageInput.value));
    }
    if (elements.btnStop) {
      elements.btnStop.addEventListener('click', () => {
        if (state.abortController) state.abortController.abort();
      });
    }

    // Suggestions in welcome screen
    const suggestionCards = document.querySelectorAll('.suggestion-card');
    suggestionCards.forEach((card) => {
      card.addEventListener('click', () => {
        const prompt = card.getAttribute('data-prompt');
        if (prompt) sendMessage(prompt);
      });
    });

    // Theme toggle
    if (elements.btnThemeToggle) {
      elements.btnThemeToggle.addEventListener('click', toggleTheme);
    }

    // Auth Modal
    if (elements.btnCloseAuth) elements.btnCloseAuth.addEventListener('click', closeAuthModal);
    if (elements.tabLogin) elements.tabLogin.addEventListener('click', () => switchAuthTab('login'));
    if (elements.tabSignup) elements.tabSignup.addEventListener('click', () => switchAuthTab('signup'));
    if (elements.formLogin) elements.formLogin.addEventListener('submit', handleLogin);
    if (elements.formSignup) elements.formSignup.addEventListener('submit', handleSignup);

    // File Upload in Chat
    if (elements.btnUploadFile) {
      elements.btnUploadFile.addEventListener('click', () => elements.fileUploadInput.click());
    }
    if (elements.fileUploadInput) {
      elements.fileUploadInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          handleFileUpload(e.target.files[0]);
        }
      });
    }
    if (elements.btnRemoveFile) {
      elements.btnRemoveFile.addEventListener('click', removeAttachedFile);
    }
    if (elements.pillSummarize) {
      elements.pillSummarize.addEventListener('click', () => handleFileQuickAction('summary'));
    }
    if (elements.pillQuestions) {
      elements.pillQuestions.addEventListener('click', () => handleFileQuickAction('important_questions'));
    }
    if (elements.pillMcq) {
      elements.pillMcq.addEventListener('click', () => handleFileQuickAction('mcq'));
    }

    // Explainer Actions
    if (elements.btnGenerateExplanation) {
      elements.btnGenerateExplanation.addEventListener('click', handleGenerateExplanation);
    }
    if (elements.btnSaveExplanation) {
      elements.btnSaveExplanation.addEventListener('click', handleSaveExplanation);
    }
    if (elements.btnAskChatFollowup) {
      elements.btnAskChatFollowup.addEventListener('click', () => {
        if (state.currentExplanation) {
          switchView('chat');
          sendMessage(`Let's discuss and explore the topic '${state.currentExplanation.topic}' in detail.`);
        }
      });
    }

    // Interview Prep Actions
    if (elements.btnGenerateInterview) {
      elements.btnGenerateInterview.addEventListener('click', handleGenerateInterview);
    }

    // Quiz Actions
    if (elements.btnGenerateQuiz) {
      elements.btnGenerateQuiz.addEventListener('click', () => handleGenerateQuiz());
    }
    if (elements.btnSubmitQuiz) {
      elements.btnSubmitQuiz.addEventListener('click', handleSubmitQuiz);
    }
    if (elements.btnRetakeQuiz) {
      elements.btnRetakeQuiz.addEventListener('click', () => {
        if (state.currentQuiz) {
          state.currentQuiz.userAnswers = {};
          elements.quizResultsBanner.style.display = 'none';
          elements.btnSubmitQuiz.style.display = 'inline-block';
          renderActiveQuiz(state.currentQuiz);
        }
      });
    }
    if (elements.btnNewQuizGen) {
      elements.btnNewQuizGen.addEventListener('click', () => {
        elements.quizResultsBanner.style.display = 'none';
        elements.quizActiveArea.style.display = 'none';
        elements.btnSubmitQuiz.style.display = 'inline-block';
        elements.quizTopicInput.focus();
      });
    }

    // Learning History Actions
    if (elements.historyFilterBtns) {
      elements.historyFilterBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          elements.historyFilterBtns.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          const type = btn.getAttribute('data-type');
          loadLearningHistory(type, elements.historySearchInput ? elements.historySearchInput.value.trim() : '');
        });
      });
    }
    if (elements.historySearchInput) {
      elements.historySearchInput.addEventListener('input', (e) => {
        const activeFilter = document.querySelector('.history-filter-btn.active');
        const type = activeFilter ? activeFilter.getAttribute('data-type') : 'all';
        loadLearningHistory(type, e.target.value.trim());
      });
    }

    // Quick Action cards on Dashboard
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach((card) => {
      card.addEventListener('click', () => {
        const action = card.getAttribute('data-action');
        if (action === 'go-chat') switchView('chat');
        else if (action === 'go-explainer') switchView('explainer');
        else if (action === 'go-interview') switchView('interview');
        else if (action === 'go-quiz') switchView('quiz');
      });
    });

    // Delete Modal
    if (elements.btnCancelDelete) {
      elements.btnCancelDelete.addEventListener('click', () => {
        elements.deleteModal.classList.remove('active');
        state.deleteTarget = null;
      });
    }
    if (elements.btnConfirmDelete) {
      elements.btnConfirmDelete.addEventListener('click', executeDelete);
    }

    // Settings Modal
    if (elements.btnSettings) {
      elements.btnSettings.addEventListener('click', () => {
        elements.inputApiKey.value = state.userApiKey;
        elements.selectModel.value = state.activeModel;
        elements.settingsModal.classList.add('active');
      });
    }
    if (elements.topModelSelector) {
      elements.topModelSelector.addEventListener('click', () => {
        elements.inputApiKey.value = state.userApiKey;
        elements.selectModel.value = state.activeModel;
        elements.settingsModal.classList.add('active');
      });
    }
    if (elements.btnCloseSettings) {
      elements.btnCloseSettings.addEventListener('click', () => {
        elements.settingsModal.classList.remove('active');
      });
    }
    if (elements.btnSaveSettings) {
      elements.btnSaveSettings.addEventListener('click', () => {
        state.userApiKey = elements.inputApiKey.value.trim();
        state.activeModel = elements.selectModel.value;
        localStorage.setItem('groqchat_api_key', state.userApiKey);
        localStorage.setItem('groqchat_model', state.activeModel);
        elements.settingsModal.classList.remove('active');
        showToast('Settings saved', 'success');
        checkSystemStatus();
      });
    }

    if (elements.btnTestKey) {
      elements.btnTestKey.addEventListener('click', async () => {
        const key = elements.inputApiKey.value.trim() || state.userApiKey;
        elements.keyValidationResult.textContent = 'Testing connection...';
        elements.keyValidationResult.style.color = 'var(--text-muted)';
        try {
          const res = await apiFetch('/api/validate-key/', {
            method: 'POST',
            body: JSON.stringify({ api_key: key }),
          });
          const data = await res.json();
          if (res.ok && data.valid) {
            elements.keyValidationResult.textContent = '✓ Connected to Groq!';
            elements.keyValidationResult.style.color = '#10b981';
          } else {
            elements.keyValidationResult.textContent = `✗ ${data.message || 'Validation failed'}`;
            elements.keyValidationResult.style.color = '#ef4444';
          }
        } catch {
          elements.keyValidationResult.textContent = '✗ Connection error';
          elements.keyValidationResult.style.color = '#ef4444';
        }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Global Export for inline HTML event bindings
  // ---------------------------------------------------------------------------
  window.AIStudentCompanion = {
    switchView: (view) => switchView(view),
    openAuth: (tab) => openAuthModal(tab),
    loadConv: (id) => { switchView('chat'); loadConversation(id); },
    renameConv: (id, title) => renameConversation(id, title),
    confirmDelete: (type, id) => confirmDelete(type, id),
    selectQuizOption: (qId, letter) => selectQuizOption(qId, letter),
    toggleInterviewAccordion: (idx) => toggleInterviewAccordion(idx),
    viewSavedExp: (id) => reopenHistoryItem('explanation', id),
    viewInterviewSession: (id) => reopenHistoryItem('interview', id),
    reviewPastQuiz: (id) => reopenHistoryItem('quiz', id),
    reopenHistoryItem: (kind, id) => reopenHistoryItem(kind, id),
  };

  // ---------------------------------------------------------------------------
  // App Initialization
  // ---------------------------------------------------------------------------
  async function init() {
    applyTheme(state.theme);
    setupEventListeners();
    await checkAuthStatus();
    await checkSystemStatus();
    await fetchConversations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
