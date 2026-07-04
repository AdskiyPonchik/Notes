function escapeHtml(text) {
    return $('<div>').text(text).html();
}

function loadNotes() {
    let container = $('#notes');
    if (!container.length) {
        return;
    }
    $.ajax({
        headers: {
            "X-Requested-With": "XMLHttpRequest",
        },
        url: container.data('url'),
        method: 'GET',
        dataType: 'json',
        success: function (data) {
            container.empty();
            for (let i = 0; i < data.length; i++) {
                let noteHtml = `<div class="card" data-note-id="${data[i].id}">
                                    <div class="name">
                                        <h2>${escapeHtml(data[i].title)}</h2>
                                    </div>
                                    <hr class="honey-yellow"/>
                                    <div class="text-field">
                                        <p class="text">${escapeHtml(data[i].text)}</p>
                                    </div>
                                </div>`;
                container.append(noteHtml);
            }
        },
    });
}

$(document).ready(function () {
    loadNotes();

    $('.plus').on('click', function (e) {
        e.preventDefault();
        $('#noteModal').show();
    });

    $('.close').on('click', function () {
        $('#noteModal').hide();
    });

    $('#submitNote').on('click', function (e) {
        e.preventDefault();
        let formData = $('#noteForm').serialize();
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
                let errors = xhr.responseJSON ? xhr.responseJSON.errors : 'Unknown error';
                alert('Errors: ' + JSON.stringify(errors));
            }
        });
    });
});
