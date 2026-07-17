const progressBars = document.querySelectorAll(".progress-bar[data-progress]");

progressBars.forEach(function (bar) {
    const progressValue = bar.getAttribute("data-progress");
    bar.style.width = progressValue + "%";
});

const flashAlerts = document.querySelectorAll(".flash-alert");

flashAlerts.forEach(function (alertBox) {
    setTimeout(function () {
        if (window.bootstrap && bootstrap.Alert) {
            const alertInstance = bootstrap.Alert.getOrCreateInstance(alertBox);
            alertInstance.close();
        }
    }, 2500);
});

const taskSearchInput = document.querySelector("#taskSearchInput");
const taskCards = document.querySelectorAll("[data-task-card]");
const taskSearchEmpty = document.querySelector("#taskSearchEmpty");

if (taskSearchInput && taskCards.length > 0) {
    taskSearchInput.addEventListener("input", function () {
        const searchValue = taskSearchInput.value.toLowerCase().trim();
        let visibleTaskCount = 0;

        taskCards.forEach(function (card) {
            const searchText = card.getAttribute("data-search-text") || "";
            const isVisible = searchText.includes(searchValue);

            card.classList.toggle("d-none", !isVisible);

            if (isVisible) {
                visibleTaskCount += 1;
            }
        });

        const kanbanColumns = document.querySelectorAll(".modern-kanban-column");

        kanbanColumns.forEach(function (column) {
            const visibleCards = column.querySelectorAll("[data-task-card]:not(.d-none)");
            const countBadge = column.querySelector(".column-count");

            if (countBadge) {
                countBadge.textContent = visibleCards.length;
            }
        });

        if (taskSearchEmpty) {
            taskSearchEmpty.classList.toggle("d-none", visibleTaskCount > 0 || searchValue === "");
        }
    });
}