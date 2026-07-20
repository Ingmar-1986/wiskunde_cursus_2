document.addEventListener("DOMContentLoaded", () => {
    const themeHeadings = document.querySelectorAll(
        ".activity-card.card-sectionheading.card.part"
    );

    themeHeadings.forEach((heading, index) => {
        const contentWrapper = document.createElement("div");

        contentWrapper.classList.add("theme-content");
        contentWrapper.id = `theme-content-${index + 1}`;

        heading.setAttribute("role", "button");
        heading.setAttribute("tabindex", "0");
        heading.setAttribute("aria-expanded", "true");
        heading.setAttribute("aria-controls", contentWrapper.id);

        let nextElement = heading.nextElementSibling;

        while (
            nextElement &&
            !nextElement.matches(
                ".activity-card.card-sectionheading.card.part"
            ) &&
            !nextElement.matches(".course-footer-clear") &&
            !nextElement.matches(".site-footer")
        ) {
            const elementToMove = nextElement;
            nextElement = nextElement.nextElementSibling;

            contentWrapper.appendChild(elementToMove);
        }

        heading.insertAdjacentElement("afterend", contentWrapper);
            if (index > 0) {
                heading.classList.add("is-collapsed");
                contentWrapper.classList.add("is-collapsed");
                heading.setAttribute("aria-expanded", "false");
            }

        const toggleTheme = () => {
            const isCollapsed = heading.classList.toggle("is-collapsed");

            contentWrapper.classList.toggle(
                "is-collapsed",
                isCollapsed
            );

            heading.setAttribute(
                "aria-expanded",
                String(!isCollapsed)
            );
        };

        heading.addEventListener("click", toggleTheme);

        heading.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                toggleTheme();
            }
        });
    });
});