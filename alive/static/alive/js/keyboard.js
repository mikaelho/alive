/**
 * Keyboard utilities for PyView components.
 */

/**
 * Initialize Command+Enter (Mac) / Ctrl+Enter (other platforms) to save edits.
 * Looks for a save button within the .field-edit container of the focused element.
 */
function initKeyboardShortcuts() {
    // Use capture phase to get the event before anything else
    document.addEventListener('keydown', function(e) {
        // Escape to cancel
        if (e.key === 'Escape') {
            // Check for create form first (it's visible on the page)
            const createForm = document.querySelector('.create-form');
            if (createForm) {
                e.preventDefault();
                e.stopPropagation();
                const cancelBtn = createForm.querySelector('button[phx-click="cancel_create"]');
                if (cancelBtn) {
                    cancelBtn.click();
                    return;
                }
            }

            // Check for field edit mode
            const activeEl = document.activeElement;
            const fieldEdit = activeEl ? activeEl.closest('.field-edit') : null;
            if (fieldEdit) {
                e.preventDefault();
                e.stopPropagation();
                const cancelBtn = fieldEdit.querySelector('button[phx-click="cancel_edit"]');
                if (cancelBtn) {
                    cancelBtn.click();
                    return;
                }
            }
        }

        // Cmd+Enter / Ctrl+Enter to save
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            const activeEl = document.activeElement;
            if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT')) {
                e.preventDefault();

                // Blur first to trigger phx-blur and send the current value
                activeEl.blur();

                // Small delay to let the blur event be processed
                setTimeout(function() {
                    // Check for field edit mode
                    const fieldEdit = activeEl.closest('.field-edit');
                    if (fieldEdit) {
                        const saveBtn = fieldEdit.querySelector('button[phx-click="save_edit"]');
                        if (saveBtn) {
                            saveBtn.click();
                            return;
                        }
                    }

                    // Check for create form
                    const createForm = activeEl.closest('.create-form');
                    if (createForm) {
                        const createBtn = createForm.querySelector('button[phx-click="save_create"]');
                        if (createBtn) {
                            createBtn.click();
                            return;
                        }
                    }
                }, 50);
            }
        }
    }, true);  // Use capture phase
}

/**
 * Hook to auto-focus the first input in a create form.
 */
window.Hooks = window.Hooks || {};

window.Hooks.AutoFocus = {
    mounted() {
        this.focusInput();
    },
    updated() {
        this.focusInput();
    },
    focusInput() {
        setTimeout(() => {
            const input = this.el.querySelector('input, textarea, select');
            if (input && document.activeElement !== input) {
                input.focus();
                if (input.tagName === 'INPUT' || input.tagName === 'TEXTAREA') {
                    const len = input.value.length;
                    input.setSelectionRange(len, len);
                }
            }
        }, 10);
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initKeyboardShortcuts);
} else {
    initKeyboardShortcuts();
}
