/* Dashboard behavior: server-side view switching (active/archived/trash),
   client-side sub-filtering (favorites, #tags), and the Focus Edit Overlay. */

const STATUS = {ACTIVE: 'A', FAVORITE: 'F', ARCHIVED: 'R', TRASH: 'T'};

const ICONS = {
    star: '&#9733;',
    edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"/></svg>',
    archive: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="5" rx="1"/><path d="M4 9v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V9"/><line x1="10" y1="13" x2="14" y2="13"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    restore: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="1 4 1 10 7 10"/><path d="M3.5 15a9 9 0 1 0 2-9.4L1 10"/></svg>',
};

const ANIMATION_MS = 380;

let currentView = 'active';
let subFilter = 'all';
let activeTag = null;

/* ---- Helpers ---- */

function escapeHtml(text) {
    return $('<div>').text(text).html();
}

function getCsrfToken() {
    return $('#noteForm [name=csrfmiddlewaretoken]').val();
}

function updateUrl(noteId) {
    // The template renders {% url 'update_note' 0 %} as the pattern.
    return $('#notes').data('update-url').replace('/0/', '/' + noteId + '/');
}

function actionUrl(noteId, action) {
    // The template renders {% url 'note_action' 0 'archive' %} as the pattern.
    return $('#notes').data('action-url')
        .replace('/0/', '/' + noteId + '/')
        .replace('archive/', action + '/');
}

function sendUpdate(noteId, fields) {
    return $.ajax({
        url: updateUrl(noteId),
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(fields),
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
        },
    });
}

function sendAction(noteId, action) {
    return $.ajax({
        url: actionUrl(noteId, action),
        type: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
        },
    });
}

function describeErrors(xhr) {
    let errors = xhr.responseJSON ? xhr.responseJSON.errors : 'Unknown error';
    return typeof errors === 'string' ? errors : Object.values(errors).join('\n');
}

/* ---- Rendering ---- */

function actionButton(action, title, icon, extraClass) {
    return `<button type="button" class="note-action note-action-${action} ${extraClass || ''}"
                    title="${title}">${icon}</button>`;
}

function cardActions(note) {
    let buttons = [];
    if (note.status === STATUS.ACTIVE || note.status === STATUS.FAVORITE) {
        let starred = note.status === STATUS.FAVORITE;
        buttons.push(actionButton('fav', 'Toggle favorite', ICONS.star, starred ? 'is-active' : ''));
        buttons.push(actionButton('edit', 'Edit note', ICONS.edit));
        buttons.push(actionButton('archive', 'Archive', ICONS.archive));
        buttons.push(actionButton('trash', 'Move to trash', ICONS.trash));
    } else if (note.status === STATUS.ARCHIVED) {
        buttons.push(actionButton('edit', 'Edit note', ICONS.edit));
        buttons.push(actionButton('restore', 'Restore to notes', ICONS.restore));
        buttons.push(actionButton('trash', 'Move to trash', ICONS.trash));
    } else {
        buttons.push(actionButton('restore', 'Restore to notes', ICONS.restore));
    }
    return buttons.join('');
}

function renderNote(note) {
    let tags = note.tags.map(function (tag) {
        return `<button type="button" class="note-tag" data-tag="${escapeHtml(tag)}">#${escapeHtml(tag)}</button>`;
    }).join('');
    return `<article class="note-card" data-note-id="${note.id}"
                     data-status="${escapeHtml(note.status)}"
                     data-tags="${escapeHtml(note.tags.join(' '))}">
                <div class="note-card-head">
                    <h2 class="note-title">${escapeHtml(note.title)}</h2>
                    <div class="note-actions">${cardActions(note)}</div>
                </div>
                <p class="note-text">${escapeHtml(note.text)}</p>
                ${tags ? `<div class="note-tags">${tags}</div>` : ''}
            </article>`;
}

function renderCounts(counts) {
    $('.view-count').each(function () {
        let count = counts[$(this).data('count')];
        $(this).text(count || '');
    });
}

function renderTagList(notes) {
    let unique = [];
    notes.forEach(function (note) {
        note.tags.forEach(function (tag) {
            if (unique.indexOf(tag) === -1) {
                unique.push(tag);
            }
        });
    });
    unique.sort();

    if (activeTag && unique.indexOf(activeTag) === -1) {
        activeTag = null;
    }

    let list = $('#tagList').empty();
    if (!unique.length) {
        list.append('<span class="empty-tags-hint">Use #hashtags in notes to see categories here.</span>');
        return;
    }
    unique.forEach(function (tag) {
        list.append(`<button type="button"
                             class="sidebar-link tag-btn ${tag === activeTag ? 'is-active' : ''}"
                             data-tag="${escapeHtml(tag)}">#${escapeHtml(tag)}</button>`);
    });
}

function emptyMessage() {
    if (activeTag) {
        return `Nothing here tagged #${escapeHtml(activeTag)}.`;
    }
    if (currentView === 'archived') {
        return 'The archive is empty.';
    }
    if (currentView === 'trash') {
        return 'The trash is empty.';
    }
    if (subFilter === 'favorites') {
        return 'No favorites yet — press the star on a note to pin it here.';
    }
    return 'No notes yet — press + to create your first one.';
}

function applyClientFilter() {
    let visible = 0;
    $('#notes .note-card').each(function () {
        let card = $(this);
        let show = true;
        if (subFilter === 'favorites' && card.attr('data-status') !== STATUS.FAVORITE) {
            show = false;
        }
        if (show && activeTag) {
            let tags = (card.attr('data-tags') || '').split(' ');
            show = tags.indexOf(activeTag) !== -1;
        }
        card.toggle(show);
        if (show) {
            visible++;
        }
    });

    $('#notes .empty-state').remove();
    if (visible === 0) {
        $('#notes').append(`<p class="empty-state">${emptyMessage()}</p>`);
    }

    $('.tag-btn').each(function () {
        $(this).toggleClass('is-active', $(this).data('tag') === activeTag);
    });
}

function loadNotes() {
    let container = $('#notes');
    if (!container.length) {
        return;
    }
    $.ajax({
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
        url: container.data('url'),
        data: {filter: currentView},
        method: 'GET',
        dataType: 'json',
        success: function (data) {
            container.empty();
            data.notes.forEach(function (note) {
                container.append(renderNote(note));
            });
            renderCounts(data.counts);
            renderTagList(data.notes);
            applyClientFilter();
        },
    });
}

function switchView(view) {
    currentView = view;
    activeTag = null;
    subFilter = 'all';

    $('.view-btn').each(function () {
        $(this).toggleClass('is-active', $(this).data('view') === view);
    });
    $('.subfilter-btn').each(function () {
        let active = $(this).data('subfilter') === 'all';
        $(this).toggleClass('is-active', active).attr('aria-selected', active);
    });
    // Favorites only exist inside the active view.
    $('#subFilterBar').toggleClass('is-hidden', view !== 'active');

    loadNotes();
}

/* ---- Focus Edit Overlay ---- */

let focusState = null;

function overlayStatusButtons(status) {
    let side = $('#focusStatusActions').empty();
    if (status === STATUS.ACTIVE || status === STATUS.FAVORITE) {
        side.append(`<button type="button" class="focus-action" data-action="archive">${ICONS.archive}<span>Archive</span></button>`);
        side.append(`<button type="button" class="focus-action" data-action="trash">${ICONS.trash}<span>Trash</span></button>`);
    } else {
        side.append(`<button type="button" class="focus-action" data-action="restore">${ICONS.restore}<span>Restore</span></button>`);
        if (status === STATUS.ARCHIVED) {
            side.append(`<button type="button" class="focus-action" data-action="trash">${ICONS.trash}<span>Trash</span></button>`);
        }
    }
}

function centeredRect() {
    let width = Math.min(640, window.innerWidth - 48);
    let height = Math.min(Math.round(window.innerHeight * 0.72), 560);
    return {
        top: Math.round((window.innerHeight - height) / 2) + 'px',
        left: Math.round((window.innerWidth - width) / 2) + 'px',
        width: width + 'px',
        height: height + 'px',
    };
}

function rectOf(card) {
    let rect = card[0].getBoundingClientRect();
    return {
        top: rect.top + 'px',
        left: rect.left + 'px',
        width: rect.width + 'px',
        height: rect.height + 'px',
    };
}

function openFocus(card) {
    let overlay = $('#focusOverlay');
    let focusCard = overlay.find('.focus-card');

    focusState = {
        noteId: card.data('note-id'),
        originRect: rectOf(card),
        title: card.find('.note-title').text(),
        text: card.find('.note-text').text(),
        closing: false,
    };

    $('#focusTitle').val(focusState.title);
    $('#focusText').val(focusState.text);
    overlayStatusButtons(card.attr('data-status'));

    // Fly out: start at the card's on-screen rect, then transition to center.
    overlay.css('display', 'block').attr('aria-hidden', 'false');
    focusCard.addClass('no-anim').css(focusState.originRect);
    focusCard[0].offsetHeight; // force reflow so the start rect is committed
    focusCard.removeClass('no-anim');
    overlay.addClass('is-visible');
    focusCard.css(centeredRect()).addClass('is-open');

    setTimeout(function () {
        $('#focusTitle').trigger('focus');
    }, ANIMATION_MS);
}

function hideFocus(reload) {
    let overlay = $('#focusOverlay');
    let focusCard = overlay.find('.focus-card');

    overlay.removeClass('is-visible');
    focusCard.removeClass('is-open').css(focusState.originRect);

    setTimeout(function () {
        overlay.css('display', 'none').attr('aria-hidden', 'true');
        focusCard.addClass('no-anim').removeAttr('style');
        focusState = null;
        if (reload) {
            loadNotes();
        }
    }, ANIMATION_MS);
}

function closeFocus() {
    if (!focusState || focusState.closing) {
        return;
    }
    let title = $('#focusTitle').val().trim();
    let text = $('#focusText').val().trim();
    let changed = title !== focusState.title || text !== focusState.text;

    if (!changed || !title || !text) {
        hideFocus(false); // nothing to save (or emptied out — discard, keep original)
        return;
    }

    focusState.closing = true;
    sendUpdate(focusState.noteId, {title: title, text: text})
        .done(function () {
            hideFocus(true);
        })
        .fail(function (xhr) {
            focusState.closing = false;
            alert('Could not save note: ' + describeErrors(xhr));
        });
}

/* ---- Wiring ---- */

$(document).ready(function () {
    loadNotes();

    /* Sidebar views, favorites sub-filter, tag filtering */

    $(document).on('click', '.view-btn', function () {
        switchView($(this).data('view'));
    });

    $(document).on('click', '.subfilter-btn', function () {
        subFilter = $(this).data('subfilter');
        if (subFilter === 'all') {
            activeTag = null; // "All Notes" clears any tag filter too
        }
        $('.subfilter-btn').each(function () {
            let active = $(this).data('subfilter') === subFilter;
            $(this).toggleClass('is-active', active).attr('aria-selected', active);
        });
        applyClientFilter();
    });

    $(document).on('click', '.tag-btn, .note-tag', function () {
        let tag = $(this).data('tag');
        activeTag = (activeTag === tag) ? null : tag; // click again to clear
        applyClientFilter();
    });

    /* Card actions */

    $('#notes').on('click', '.note-action-fav', function () {
        let btn = $(this);
        let card = btn.closest('.note-card');
        let starred = card.attr('data-status') === STATUS.FAVORITE;
        let newStatus = starred ? STATUS.ACTIVE : STATUS.FAVORITE;

        sendUpdate(card.data('note-id'), {status: newStatus})
            .done(function () {
                card.attr('data-status', newStatus);
                btn.toggleClass('is-active', newStatus === STATUS.FAVORITE);
                if (subFilter === 'favorites') {
                    applyClientFilter();
                }
            })
            .fail(function (xhr) {
                alert('Could not update favorite: ' + describeErrors(xhr));
            });
    });

    $('#notes').on('click', '.note-action-archive, .note-action-trash, .note-action-restore', function () {
        let card = $(this).closest('.note-card');
        let action = $(this).hasClass('note-action-archive') ? 'archive'
            : $(this).hasClass('note-action-trash') ? 'trash' : 'restore';

        sendAction(card.data('note-id'), action)
            .done(function () {
                loadNotes(); // the note leaves this view; counts change too
            })
            .fail(function (xhr) {
                alert('Could not move note: ' + describeErrors(xhr));
            });
    });

    /* Focus Edit Overlay */

    $('#notes').on('click', '.note-action-edit', function () {
        openFocus($(this).closest('.note-card'));
    });

    $('#focusSave').on('click', closeFocus);

    $('#focusOverlay').on('click', function (e) {
        if (e.target === this) {
            closeFocus();
        }
    });

    $('#focusStatusActions').on('click', '.focus-action', function () {
        if (!focusState || focusState.closing) {
            return;
        }
        focusState.closing = true;
        sendAction(focusState.noteId, $(this).data('action'))
            .done(function () {
                hideFocus(true);
            })
            .fail(function (xhr) {
                focusState.closing = false;
                alert('Could not move note: ' + describeErrors(xhr));
            });
    });

    $(document).on('keydown', function (e) {
        if (e.key !== 'Escape') {
            return;
        }
        if (focusState) {
            closeFocus();
        } else if ($('#noteModal').is(':visible')) {
            $('#noteModal').hide();
        }
    });

    /* Create-note modal */

    $('#openModalBtn').on('click', function () {
        $('#noteModal').show();
        $('#noteForm input:visible').first().trigger('focus');
    });

    $('.close').on('click', function () {
        $('#noteModal').hide();
    });

    $('#noteModal').on('click', function (e) {
        if (e.target === this) {
            $(this).hide();
        }
    });

    $('#noteForm').on('submit', function (e) {
        e.preventDefault();
        let formData = $(this).serialize();
        $.ajax({
            url: '',
            type: 'POST',
            data: formData,
            success: function (response) {
                if (response.status === 'success') {
                    $('#noteModal').hide();
                    $('#noteForm')[0].reset();
                    loadNotes();
                }
            },
            error: function (xhr) {
                alert('Errors: ' + describeErrors(xhr));
            }
        });
    });
});
