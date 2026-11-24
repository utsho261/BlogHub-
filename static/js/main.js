/**
 * BlogHub — Modern Client-Side Controller & Real-Time Validation Engine
 * CSE-458: Web Database Programming
 */

document.addEventListener('DOMContentLoaded', () => {
    initUserMenu();
    initToasts();
    initRegistrationValidation();
    initLoginValidation();
    initPostEditor();
    initLikeToggle();
    initCommentForm();
    initAvatarInputs();
});

/* ==========================================================================
   User Navigation Dropdown & Mobile Menu
   ========================================================================== */
function initUserMenu() {
    const userBtn = document.getElementById('userMenuBtn');
    const dropdownPanel = document.getElementById('userDropdownPanel');

    if (userBtn && dropdownPanel) {
        userBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownPanel.classList.toggle('show');
            const expanded = dropdownPanel.classList.contains('show');
            userBtn.setAttribute('aria-expanded', expanded);
        });

        document.addEventListener('click', (e) => {
            if (!dropdownPanel.contains(e.target) && !userBtn.contains(e.target)) {
                dropdownPanel.classList.remove('show');
                userBtn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    const mobileToggle = document.getElementById('mobileMenuToggle');
    if (mobileToggle) {
        mobileToggle.addEventListener('click', () => {
            const searchForm = document.querySelector('.nav-search-form');
            if (searchForm) {
                searchForm.style.display = searchForm.style.display === 'block' ? 'none' : 'block';
            }
        });
    }
}

/* ==========================================================================
   Flash Toasts Auto-Dismissal
   ========================================================================== */
function initToasts() {
    const toasts = document.querySelectorAll('.toast-card');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(50px)';
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-card toast-${type}`;
    
    let iconClass = 'fa-circle-info';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'danger') iconClass = 'fa-circle-exclamation';
    if (type === 'warning') iconClass = 'fa-triangle-exclamation';

    toast.innerHTML = `
        <div class="toast-icon"><i class="fa-solid ${iconClass}"></i></div>
        <div class="toast-message">${message}</div>
        <button class="toast-close-btn" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}

/* ==========================================================================
   Real-Time Registration Form Validation
   ========================================================================== */
function initRegistrationValidation() {
    const form = document.getElementById('registerForm');
    if (!form) return;

    const nameInput = document.getElementById('regName');
    const usernameInput = document.getElementById('regUsername');
    const emailInput = document.getElementById('regEmail');
    const passwordInput = document.getElementById('regPassword');
    const confirmInput = document.getElementById('regConfirmPassword');
    const bioInput = document.getElementById('regBio');

    let usernameDebounceTimer;
    let emailDebounceTimer;

    // 1. Full Name Validation
    if (nameInput) {
        nameInput.addEventListener('input', () => {
            const val = nameInput.value.trim();
            const feedback = document.getElementById('nameFeedback');
            const nameRegex = /^[a-zA-Z\s\.\-']+$/;

            if (val.length < 2 || val.length > 60 || !nameRegex.test(val)) {
                setInvalid(nameInput, feedback, 'Name must be 2-60 characters and contain only letters.');
            } else {
                setValid(nameInput, feedback);
            }
        });
    }

    // 2. Live AJAX Username Availability
    if (usernameInput) {
        usernameInput.addEventListener('input', () => {
            clearTimeout(usernameDebounceTimer);
            const val = usernameInput.value.trim().toLowerCase();
            const feedback = document.getElementById('usernameFeedback');
            const statusPill = document.getElementById('usernameStatus');
            const userRegex = /^[a-z0-9_]+$/;

            if (val.length < 3 || val.length > 25) {
                setInvalid(usernameInput, feedback, 'Username must be between 3 and 25 characters.');
                if (statusPill) statusPill.textContent = '';
                return;
            }
            if (!userRegex.test(val)) {
                setInvalid(usernameInput, feedback, 'Only lowercase letters, numbers, and underscores allowed.');
                if (statusPill) statusPill.textContent = '';
                return;
            }

            if (statusPill) {
                statusPill.className = 'live-status-pill';
                statusPill.textContent = 'Checking...';
            }

            usernameDebounceTimer = setTimeout(() => {
                fetch(`/api/validate/username?username=${encodeURIComponent(val)}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.valid) {
                            setValid(usernameInput, feedback);
                            if (statusPill) {
                                statusPill.className = 'live-status-pill success';
                                statusPill.innerHTML = '<i class="fa-solid fa-check"></i> Available';
                            }
                        } else {
                            setInvalid(usernameInput, feedback, data.message);
                            if (statusPill) {
                                statusPill.className = 'live-status-pill error';
                                statusPill.innerHTML = '<i class="fa-solid fa-xmark"></i> ' + data.message;
                            }
                        }
                    })
                    .catch(() => {});
            }, 350);
        });
    }

    // 3. Live AJAX Email Availability
    if (emailInput) {
        emailInput.addEventListener('input', () => {
            clearTimeout(emailDebounceTimer);
            const val = emailInput.value.trim().toLowerCase();
            const feedback = document.getElementById('emailFeedback');
            const statusPill = document.getElementById('emailStatus');
            const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;

            if (!emailRegex.test(val)) {
                setInvalid(emailInput, feedback, 'Please enter a valid email address.');
                if (statusPill) statusPill.textContent = '';
                return;
            }

            if (statusPill) {
                statusPill.className = 'live-status-pill';
                statusPill.textContent = 'Checking...';
            }

            emailDebounceTimer = setTimeout(() => {
                fetch(`/api/validate/email?email=${encodeURIComponent(val)}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.valid) {
                            setValid(emailInput, feedback);
                            if (statusPill) {
                                statusPill.className = 'live-status-pill success';
                                statusPill.innerHTML = '<i class="fa-solid fa-check"></i> Available';
                            }
                        } else {
                            setInvalid(emailInput, feedback, data.message);
                            if (statusPill) {
                                statusPill.className = 'live-status-pill error';
                                statusPill.innerHTML = '<i class="fa-solid fa-xmark"></i> ' + data.message;
                            }
                        }
                    })
                    .catch(() => {});
            }, 350);
        });
    }

    // 4. Password Strength & Checklist
    if (passwordInput) {
        passwordInput.addEventListener('input', () => {
            const pwd = passwordInput.value;
            const feedback = document.getElementById('passwordFeedback');
            const strengthBar = document.getElementById('strengthBar');
            const strengthLabel = document.getElementById('strengthLabel');

            const hasLen = pwd.length >= 8;
            const hasUpper = /[A-Z]/.test(pwd);
            const hasLower = /[a-z]/.test(pwd);
            const hasNum = /[0-9]/.test(pwd);
            const hasSpec = /[!@#$%^&*(),.?":{}|<>\-_]/.test(pwd);

            updateCheckItem('checkLen', hasLen);
            updateCheckItem('checkUpper', hasUpper);
            updateCheckItem('checkLower', hasLower);
            updateCheckItem('checkNum', hasNum);
            updateCheckItem('checkSpec', hasSpec);

            // Compute score out of 5
            const score = [hasLen, hasUpper, hasLower, hasNum, hasSpec].filter(Boolean).length;
            let width = (score / 5) * 100;
            let color = '#ef4444';
            let label = 'Weak';

            if (score === 5) {
                color = '#10b981';
                label = 'Strong & Secure';
            } else if (score >= 3) {
                color = '#f59e0b';
                label = 'Moderate';
            }

            if (strengthBar) {
                strengthBar.style.width = width + '%';
                strengthBar.style.backgroundColor = color;
            }
            if (strengthLabel) {
                strengthLabel.textContent = pwd.length === 0 ? 'Enter password' : label;
                strengthLabel.style.color = color;
            }

            if (score === 5) {
                setValid(passwordInput, feedback);
            } else {
                setInvalid(passwordInput, feedback, 'Password must meet all 5 requirements below.');
            }

            // Also revalidate confirm password if already typed
            if (confirmInput && confirmInput.value) {
                validateConfirm();
            }
        });
    }

    // 5. Confirm Password
    function validateConfirm() {
        if (!confirmInput) return;
        const feedback = document.getElementById('confirmFeedback');
        if (confirmInput.value !== passwordInput.value) {
            setInvalid(confirmInput, feedback, 'Passwords do not match.');
        } else if (confirmInput.value.length === 0) {
            setInvalid(confirmInput, feedback, 'Please confirm your password.');
        } else {
            setValid(confirmInput, feedback);
        }
    }

    if (confirmInput) {
        confirmInput.addEventListener('input', validateConfirm);
    }

    // 6. Bio counter
    if (bioInput) {
        const bioCounter = document.getElementById('bioCounter');
        bioInput.addEventListener('input', () => {
            if (bioCounter) bioCounter.textContent = `${bioInput.value.length} / 300`;
        });
    }

    // Submit Validation Prevention
    form.addEventListener('submit', (e) => {
        let hasErrors = false;
        
        // Trigger validation checks
        if (!nameInput.value.trim()) {
            setInvalid(nameInput, document.getElementById('nameFeedback'), 'Full name is required.');
            hasErrors = true;
        }
        if (!usernameInput.value.trim()) {
            setInvalid(usernameInput, document.getElementById('usernameFeedback'), 'Username is required.');
            hasErrors = true;
        }
        if (!emailInput.value.trim()) {
            setInvalid(emailInput, document.getElementById('emailFeedback'), 'Email address is required.');
            hasErrors = true;
        }
        if (passwordInput.value.length < 8) {
            setInvalid(passwordInput, document.getElementById('passwordFeedback'), 'Password is too short.');
            hasErrors = true;
        }
        if (confirmInput.value !== passwordInput.value) {
            setInvalid(confirmInput, document.getElementById('confirmFeedback'), 'Passwords must match.');
            hasErrors = true;
        }

        if (hasErrors) {
            e.preventDefault();
            showToast('Please fix all form validation errors before proceeding.', 'danger');
        }
    });
}

function updateCheckItem(elementId, isValid) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (isValid) {
        el.className = 'check-item valid';
        el.querySelector('i').className = 'fa-solid fa-circle-check';
    } else {
        el.className = 'check-item';
        el.querySelector('i').className = 'fa-regular fa-circle';
    }
}

/* ==========================================================================
   Login Form Validation
   ========================================================================== */
function initLoginValidation() {
    const form = document.getElementById('loginForm');
    if (!form) return;

    const idInput = document.getElementById('loginIdentifier');
    const pwdInput = document.getElementById('loginPassword');

    form.addEventListener('submit', (e) => {
        let hasErrors = false;
        if (!idInput.value.trim()) {
            setInvalid(idInput, document.getElementById('identifierFeedback'), 'Username or Email is required.');
            hasErrors = true;
        } else {
            setValid(idInput, document.getElementById('identifierFeedback'));
        }

        if (!pwdInput.value) {
            setInvalid(pwdInput, document.getElementById('passwordFeedback'), 'Password is required.');
            hasErrors = true;
        } else {
            setValid(pwdInput, document.getElementById('passwordFeedback'));
        }

        if (hasErrors) {
            e.preventDefault();
        }
    });
}

/* ==========================================================================
   Post Editor & Live Preview
   ========================================================================== */
function initPostEditor() {
    const titleInput = document.getElementById('postTitle');
    const categorySelect = document.getElementById('postCategory');
    const summaryInput = document.getElementById('postSummary');
    const contentInput = document.getElementById('postContent');
    const coverInput = document.getElementById('postCoverImage');

    if (titleInput) {
        const titleCounter = document.getElementById('titleCounter');
        titleInput.addEventListener('input', () => {
            const len = titleInput.value.length;
            if (titleCounter) titleCounter.textContent = `${len} / 150`;

            const feedback = document.getElementById('titleFeedback');
            if (len < 5) {
                setInvalid(titleInput, feedback, 'Title must be at least 5 characters long.');
            } else {
                setValid(titleInput, feedback);
            }
            updateLivePreview();
        });
    }

    if (categorySelect) {
        categorySelect.addEventListener('change', () => {
            const feedback = document.getElementById('categoryFeedback');
            if (!categorySelect.value) {
                setInvalid(categorySelect, feedback, 'Please select a valid topic.');
            } else {
                setValid(categorySelect, feedback);
            }
            updateLivePreview();
        });
    }

    if (summaryInput) {
        const counter = document.getElementById('summaryCounter');
        summaryInput.addEventListener('input', () => {
            if (counter) counter.textContent = `${summaryInput.value.length} / 300`;
            updateLivePreview();
        });
    }

    if (contentInput) {
        const wordCountEl = document.getElementById('contentWordCount');
        const readTimeEl = document.getElementById('contentReadTime');
        const feedback = document.getElementById('contentFeedback');

        contentInput.addEventListener('input', () => {
            const text = contentInput.value.trim();
            const words = text ? text.split(/\s+/).length : 0;
            const minutes = Math.max(1, Math.ceil(words / 200));

            if (wordCountEl) wordCountEl.textContent = `${words} words`;
            if (readTimeEl) readTimeEl.textContent = `${minutes} min read`;

            if (text.length < 30) {
                setInvalid(contentInput, feedback, 'Content must be at least 30 characters long.');
            } else {
                setValid(contentInput, feedback);
            }
            updateLivePreview();
        });
    }

    const coverFileInput = document.getElementById('postCoverFile');
    const coverFileLabel = document.getElementById('coverFileLabel');
    const previewBox = document.getElementById('imagePreviewBox');
    const previewImg = document.getElementById('imagePreviewImg');

    if (coverFileInput) {
        coverFileInput.addEventListener('change', () => {
            if (coverFileInput.files && coverFileInput.files[0]) {
                const file = coverFileInput.files[0];
                if (coverFileLabel) coverFileLabel.textContent = file.name;
                const reader = new FileReader();
                reader.onload = (e) => {
                    if (previewImg) previewImg.src = e.target.result;
                    if (previewBox) previewBox.style.display = 'block';
                    const liveCoverBox = document.getElementById('previewCoverBox');
                    const liveCoverImg = document.getElementById('previewCoverImg');
                    if (liveCoverBox && liveCoverImg) {
                        liveCoverBox.style.display = 'block';
                        liveCoverImg.src = e.target.result;
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

function clearCoverPreview() {
    const coverFileInput = document.getElementById('postCoverFile');
    const coverFileLabel = document.getElementById('coverFileLabel');
    const previewBox = document.getElementById('imagePreviewBox');
    const liveCoverBox = document.getElementById('previewCoverBox');

    if (coverFileInput) coverFileInput.value = '';
    if (coverFileLabel) coverFileLabel.textContent = 'Click or drop image to upload from your computer';
    if (previewBox) previewBox.style.display = 'none';
    if (liveCoverBox) liveCoverBox.style.display = 'none';
}

function switchEditorTab(tab) {
    const editPane = document.getElementById('editPane');
    const previewPane = document.getElementById('previewPane');
    const editBtn = document.getElementById('editTabBtn');
    const previewBtn = document.getElementById('previewTabBtn');

    if (tab === 'edit') {
        editPane.style.display = 'block';
        previewPane.style.display = 'none';
        editBtn.classList.add('active');
        previewBtn.classList.remove('active');
    } else {
        editPane.style.display = 'none';
        previewPane.style.display = 'block';
        editBtn.classList.remove('active');
        previewBtn.classList.add('active');
        updateLivePreview();
    }
}

function updateLivePreview() {
    const title = document.getElementById('postTitle')?.value || 'Your Story Title';
    const cat = document.getElementById('postCategory')?.value || 'Category';
    const summary = document.getElementById('postSummary')?.value || '';
    const content = document.getElementById('postContent')?.value || 'Write some content to see preview...';
    const coverUrl = document.getElementById('postCoverImage')?.value || '';

    const pTitle = document.getElementById('previewTitle');
    const pCat = document.getElementById('previewCategory');
    const pSummary = document.getElementById('previewSummary');
    const pBody = document.getElementById('previewBody');
    const pCoverBox = document.getElementById('previewCoverBox');
    const pCoverImg = document.getElementById('previewCoverImg');

    if (pTitle) pTitle.textContent = title;
    if (pCat) pCat.textContent = cat;
    if (pSummary) pSummary.textContent = summary;

    if (pCoverBox && pCoverImg) {
        if (coverUrl) {
            pCoverBox.style.display = 'block';
            pCoverImg.src = coverUrl;
        } else {
            pCoverBox.style.display = 'none';
        }
    }

    if (pBody) {
        // Simple Markdown parsing for preview
        const paragraphs = content.split('\n\n');
        let html = '';
        paragraphs.forEach(p => {
            const trimmed = p.trim();
            if (trimmed.startsWith('### ')) {
                html += `<h3>${trimmed.substring(4)}</h3>`;
            } else if (trimmed.startsWith('## ')) {
                html += `<h2>${trimmed.substring(3)}</h2>`;
            } else if (trimmed.startsWith('# ')) {
                html += `<h1>${trimmed.substring(2)}</h1>`;
            } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                const items = trimmed.split('\n').filter(i => i.trim().startsWith('- ') || i.trim().startsWith('* '));
                html += '<ul class="article-bullet-list">' + items.map(i => `<li>${i.substring(2)}</li>`).join('') + '</ul>';
            } else {
                html += `<p>${trimmed.replace(/\n/g, '<br>')}</p>`;
            }
        });
        pBody.innerHTML = html;
    }
}

/* ==========================================================================
   Like Toggle (AJAX)
   ========================================================================== */
function initLikeToggle() {
    const likeBtn = document.getElementById('likeBtn');
    if (!likeBtn) return;

    likeBtn.addEventListener('click', () => {
        const postId = likeBtn.getAttribute('data-post-id');
        if (!postId) return;

        likeBtn.disabled = true;

        fetch(`/post/${postId}/like`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        })
        .then(res => res.json())
        .then(data => {
            likeBtn.disabled = false;
            const countEl = document.getElementById('likeCount');
            const labelEl = likeBtn.querySelector('.like-label');

            if (countEl) countEl.textContent = data.likes_count;

            if (data.liked) {
                likeBtn.classList.add('liked');
                if (labelEl) labelEl.textContent = 'Liked';
            } else {
                likeBtn.classList.remove('liked');
                if (labelEl) labelEl.textContent = 'Like';
            }
        })
        .catch(() => {
            likeBtn.disabled = false;
            showToast('Could not update like. Please try again.', 'danger');
        });
    });
}

/* ==========================================================================
   Comment Form Character Counter
   ========================================================================== */
function initCommentForm() {
    const commentInput = document.getElementById('commentInput');
    const counter = document.getElementById('commentCharCounter');
    if (commentInput && counter) {
        commentInput.addEventListener('input', () => {
            counter.textContent = `${commentInput.value.length} / 600`;
        });
    }
}

/* ==========================================================================
   Helper Utilities & Modals
   ========================================================================== */
function setInvalid(input, feedbackEl, message) {
    input.classList.remove('is-valid');
    input.classList.add('is-invalid');
    if (feedbackEl) {
        feedbackEl.textContent = message;
        feedbackEl.classList.add('show');
    }
}

function setValid(input, feedbackEl) {
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');
    if (feedbackEl) {
        feedbackEl.classList.remove('show');
    }
}

function togglePasswordVisibility(fieldId, btn) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    const isPassword = field.type === 'password';
    field.type = isPassword ? 'text' : 'password';
    btn.innerHTML = isPassword ? '<i class="fa-regular fa-eye-slash"></i>' : '<i class="fa-regular fa-eye"></i>';
}

function copyPostLink() {
    navigator.clipboard.writeText(window.location.href)
        .then(() => showToast('Link copied to clipboard!', 'success'))
        .catch(() => showToast('Could not copy link.', 'warning'));
}

function openDeleteModal(postId) {
    const backdrop = document.getElementById('deleteModalBackdrop');
    const form = document.getElementById('deleteForm');
    if (backdrop && form) {
        form.action = `/post/${postId}/delete`;
        backdrop.classList.add('show');
    }
}

function closeDeleteModal() {
    const backdrop = document.getElementById('deleteModalBackdrop');
    if (backdrop) backdrop.classList.remove('show');
}

// Global backdrop click & escape key listener for modals
document.addEventListener('click', (e) => {
    const deleteModal = document.getElementById('deleteModalBackdrop');
    if (deleteModal && e.target === deleteModal) {
        closeDeleteModal();
    }
    const profileModal = document.getElementById('editProfileModal');
    if (profileModal && e.target === profileModal) {
        closeProfileEditModal();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeDeleteModal();
        closeProfileEditModal();
    }
});

/* ==========================================================================
   Avatar Upload & Live Preview (File Only from Device)
   ========================================================================== */
function initAvatarInputs() {
    // 1. Registration form avatar
    const regFileInput = document.getElementById('regAvatarFile');
    const regLivePreview = document.getElementById('avatarLivePreview');
    const regFileLabel = document.getElementById('fileUploadLabel');
    const regNameInput = document.getElementById('regName');

    if (regNameInput && regLivePreview) {
        regNameInput.addEventListener('input', () => {
            if ((!regFileInput || !regFileInput.files.length) && regNameInput.value.trim()) {
                regLivePreview.src = `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(regNameInput.value.trim())}`;
            }
        });
    }

    if (regFileInput && regLivePreview) {
        regFileInput.addEventListener('change', () => {
            if (regFileInput.files && regFileInput.files[0]) {
                const file = regFileInput.files[0];
                if (regFileLabel) regFileLabel.textContent = file.name;
                const reader = new FileReader();
                reader.onload = (e) => {
                    regLivePreview.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 2. Profile Edit Modal avatar
    const editFileInput = document.getElementById('editAvatarFileInput');
    const editLivePreview = document.getElementById('editAvatarLivePreview');
    const editFileLabel = document.getElementById('editFileLabel');
    const editBio = document.getElementById('editProfileBio');
    const editBioCounter = document.getElementById('editBioCounter');

    if (editBio && editBioCounter) {
        editBio.addEventListener('input', () => {
            editBioCounter.textContent = `${editBio.value.length} / 300`;
        });
    }

    if (editFileInput && editLivePreview) {
        editFileInput.addEventListener('change', () => {
            if (editFileInput.files && editFileInput.files[0]) {
                const file = editFileInput.files[0];
                if (editFileLabel) editFileLabel.textContent = file.name;
                const reader = new FileReader();
                reader.onload = (e) => {
                    editLivePreview.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

function openProfileEditModal() {
    const modal = document.getElementById('profileEditModal');
    if (modal) modal.classList.add('show');
}

function closeProfileEditModal() {
    const modal = document.getElementById('profileEditModal');
    if (modal) modal.classList.remove('show');
}
