<script>
    $(document).ready(function() {
    var modal = $('#myModal');
    var openModalButton = $('.plus a');
    var closeButton = $('.close');

    // Открытие модального окна при клике на кнопку "+"
    openModalButton.click(function() {
    modal.css('display', 'block');
});

    // Закрытие модального окна при клике на кнопку "×"
    closeButton.click(function() {
    modal.css('display', 'none');
});

    // Закрытие модального окна при клике за его пределами
    $(window).click(function(event) {
    if (event.target == modal[0]) {
    modal.css('display', 'none');
}
});
});
</script>
