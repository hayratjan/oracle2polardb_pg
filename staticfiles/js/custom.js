// 自定义JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 初始化提示框
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化下拉菜单
    var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'));
    var dropdownList = dropdownElementList.map(function (dropdownToggleEl) {
        return new bootstrap.Dropdown(dropdownToggleEl);
    });

    // 表单验证
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // AJAX错误处理
    $(document).ajaxError(function(event, jqXHR, settings, error) {
        console.error('Ajax error:', error);
        var message = '操作失败：' + (jqXHR.responseJSON?.message || error || '未知错误');
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: '错误',
                text: message
            });
        } else {
            alert(message);
        }
    });
}); 