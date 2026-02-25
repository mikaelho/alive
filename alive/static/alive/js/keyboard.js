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
            // Check for picker modal first (highest priority)
            const pickerModal = document.querySelector('.picker-modal');
            if (pickerModal) {
                e.preventDefault();
                e.stopPropagation();
                const cancelBtn = pickerModal.querySelector('button[phx-click="close_picker"]');
                if (cancelBtn) {
                    cancelBtn.click();
                    return;
                }
            }

            // Check for field edit mode (including map detail edits)
            const activeEl = document.activeElement;
            const fieldEdit = activeEl ? activeEl.closest('.field-edit') : null;
            if (fieldEdit) {
                e.preventDefault();
                e.stopPropagation();
                const cancelBtn = fieldEdit.querySelector('button[phx-click="cancel_edit"], button[phx-click="cancel_inline_target_edit"], button[phx-click="map_cancel_edit"]');
                if (cancelBtn) {
                    cancelBtn.click();
                    return;
                }
            }

            // Check for create form (including map create)
            const createForm = document.querySelector('.create-form');
            if (createForm) {
                e.preventDefault();
                e.stopPropagation();
                const cancelBtn = createForm.querySelector('button[phx-click="cancel_create"], button[phx-click="map_cancel_create"]');
                if (cancelBtn) {
                    cancelBtn.click();
                    return;
                }
            }

            // Check for map detail popup (close with Escape)
            const mapDetail = document.querySelector('.map-detail-popup');
            if (mapDetail) {
                e.preventDefault();
                e.stopPropagation();
                const closeBtn = mapDetail.querySelector('button[phx-click="close_map_detail"]');
                if (closeBtn) {
                    closeBtn.click();
                    return;
                }
            }
        }

        // Cmd+Enter / Ctrl+Enter to save/confirm
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            // Check for picker modal first
            const pickerModal = document.querySelector('.picker-modal');
            if (pickerModal) {
                e.preventDefault();
                const confirmBtn = pickerModal.querySelector('button[phx-click="confirm_picker"]');
                if (confirmBtn && !confirmBtn.disabled) {
                    confirmBtn.click();
                    return;
                }
            }

            const activeEl = document.activeElement;
            if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT')) {
                e.preventDefault();

                // Find the save button BEFORE blurring, since blur may trigger re-render
                const fieldEdit = activeEl.closest('.field-edit');
                const createForm = activeEl.closest('.create-form');
                const saveBtn = fieldEdit
                    ? fieldEdit.querySelector('button[phx-click="save_edit"], button[phx-click="save_inline_target_edit"], button[phx-click="map_save_edit"]')
                    : createForm
                    ? createForm.querySelector('button[phx-click="save_create"], button[phx-click="map_save_create"]')
                    : null;

                if (saveBtn) {
                    saveBtn.click();
                }
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

window.Hooks.ConfirmClick = {
    mounted() {
        this.el.addEventListener('click', (e) => {
            const message = this.el.dataset.confirm || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
                e.stopPropagation();
            }
        }, true);  // Use capture to run before phx-click
    }
};

window.Hooks.Collapsible = {
    mounted() {
        this.expanded = false;
        this.setup();
    },
    updated() {
        this.setup();
    },
    setup() {
        const content = this.el.querySelector('.collapsible-content');
        const toggle = this.el.querySelector('.collapsible-toggle');
        if (!content || !toggle) return;

        if (this.expanded) {
            content.classList.remove('line-clamp-3');
            toggle.textContent = 'Show less';
            toggle.classList.remove('hidden');
        } else {
            content.classList.add('line-clamp-3');
            if (content.scrollHeight > content.clientHeight + 1) {
                toggle.textContent = 'Show more';
                toggle.classList.remove('hidden');
            } else {
                toggle.classList.add('hidden');
            }
        }

        if (!this._bound) {
            this._bound = true;
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.expanded = !this.expanded;
                this.setup();
            });
        }
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initKeyboardShortcuts);
} else {
    initKeyboardShortcuts();
}
