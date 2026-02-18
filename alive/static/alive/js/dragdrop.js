/**
 * Drag and drop hook using SortableJS.
 *
 * This hook must be defined before PyView's app.js loads.
 * It's registered on window.Hooks and used via phx-hook="Sortable".
 */

window.Hooks = window.Hooks || {};

window.Hooks.Sortable = {
    mounted() {
        const container = this.el;
        const hook = this;

        this.sortable = new Sortable(container, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            handle: '.drag-handle',

            onEnd: function(evt) {
                const cardId = evt.item.dataset.cardId;
                const newIndex = evt.newIndex;
                const oldIndex = evt.oldIndex;

                if (oldIndex === newIndex) return;

                hook.pushEvent('reorder_to_position', {
                    card_id: cardId,
                    position: newIndex.toString()
                });
            }
        });
    },

    updated() {
        // SortableJS handles DOM changes automatically
    },

    destroyed() {
        if (this.sortable) {
            this.sortable.destroy();
        }
    }
};

window.Hooks.SortableTags = {
    mounted() {
        const hook = this;
        this.sortable = new Sortable(this.el, {
            animation: 150,
            filter: '.no-drag',
            preventOnFilter: false,
            draggable: '.sortable-tag',
            onEnd(evt) {
                hook.pushEvent('reorder_tag', {
                    item_id: hook.el.dataset.itemId,
                    field: hook.el.dataset.field,
                    tag_pk: evt.item.dataset.tagPk,
                    position: evt.newIndex.toString()
                });
            }
        });
    },
    updated() {},
    destroyed() {
        if (this.sortable) this.sortable.destroy();
    }
};
