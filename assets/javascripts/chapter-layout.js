document.addEventListener("DOMContentLoaded", () => {
    const menuButton =
        document.getElementById("courseMenuButton");

    const sidebar =
        document.getElementById("courseSidebar");

    const closeButton =
        document.getElementById("sidebarClose");

    document
        .querySelectorAll(".course-section-toggle")
        .forEach(button => {
            button.addEventListener("click", () => {
                button
                    .closest(".course-section")
                    .classList
                    .toggle("is-open");
            });
        });

    menuButton?.addEventListener("click", () => {
        sidebar?.classList.add("is-visible");
    });

    closeButton?.addEventListener("click", () => {
        sidebar?.classList.remove("is-visible");
    });
});