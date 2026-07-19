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

document.addEventListener("DOMContentLoaded", () => {
    const currentFile =
        window.location.pathname.split("/").pop() || "index.html";

    const sidebarLinks = document.querySelectorAll(
        ".course-section-content a"
    );

    sidebarLinks.forEach(link => {
        const linkFile =
            new URL(link.href, window.location.href)
                .pathname
                .split("/")
                .pop();

        if (linkFile === currentFile) {
            link.classList.add("is-active");

            const section =
                link.closest(".course-section");

            section?.classList.add("is-open");
        }
    });

    const menuButton =
        document.getElementById("courseMenuButton");

    const sidebar =
        document.getElementById("courseSidebar");

    const closeButton =
        document.getElementById("sidebarClose");

    const overlay =
        document.getElementById("courseSidebarOverlay");

    const openSidebar = () => {
        sidebar?.classList.add("is-visible");
        overlay?.classList.add("is-visible");
        document.body.classList.add("sidebar-open");
    };

    const closeSidebar = () => {
        sidebar?.classList.remove("is-visible");
        overlay?.classList.remove("is-visible");
        document.body.classList.remove("sidebar-open");
    };

    menuButton?.addEventListener("click", openSidebar);
    closeButton?.addEventListener("click", closeSidebar);
    overlay?.addEventListener("click", closeSidebar);

    document
        .querySelectorAll(".course-section-toggle")
        .forEach(button => {
            button.addEventListener("click", () => {
                button
                    .closest(".course-section")
                    ?.classList.toggle("is-open");
            });
        });
});