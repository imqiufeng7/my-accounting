document.addEventListener("DOMContentLoaded", () => {
  const rowsContainer = document.getElementById("batch-rows");
  const addRowButton = document.getElementById("add-row");
  const template = document.getElementById("batch-row-template");

  if (!rowsContainer || !addRowButton || !template) return;

  addRowButton.addEventListener("click", () => {
    const clone = template.content.cloneNode(true);
    rowsContainer.appendChild(clone);
  });

  rowsContainer.addEventListener("click", (event) => {
    if (event.target.classList.contains("remove-row")) {
      const rows = rowsContainer.querySelectorAll(".batch-row");
      if (rows.length > 1) {
        event.target.closest(".batch-row").remove();
      }
    }
  });
});
