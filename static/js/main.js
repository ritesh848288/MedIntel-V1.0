// Hamburger menu toggle
document.addEventListener('DOMContentLoaded', function () {
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');

    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function () {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('open');
        });

        // Close menu when clicking a link (mobile)
        navMenu.querySelectorAll('.nav-link, .btn').forEach(function (link) {
            link.addEventListener('click', function () {
                hamburger.classList.remove('active');
                navMenu.classList.remove('open');
            });
        });
    }

    // Auto-dismiss flash messages after 5 seconds
    document.querySelectorAll('.flash').forEach(function (flash) {
        setTimeout(function () {
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-8px)';
            setTimeout(function () { flash.remove(); }, 300);
        }, 5000);
    });
});
