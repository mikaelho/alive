/**
 * Keyboard utilities for PyView components.
 */

/**
 * Initialize Command+Enter (Mac) / Ctrl+Enter (other platforms) to save edits.
 * Looks for a save button within the .field-edit container of the focused element.
 */
function initSaveOnCmdEnter() {
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            const activeEl = document.activeElement;
            if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
                const fieldEdit = activeEl.closest('.field-edit');
                if (fieldEdit) {
                    const saveBtn = fieldEdit.querySelector('button[phx-click="save_edit"]');
                    if (saveBtn) {
                        e.preventDefault();
                        saveBtn.click();
                    }
                }
            }
        }
    });
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSaveOnCmdEnter);
} else {
    initSaveOnCmdEnter();
}
