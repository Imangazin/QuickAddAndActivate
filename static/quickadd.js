(function () {
    var form = document.getElementById("quickAddForm");
    var feedback = document.getElementById("quickAddResponse");
    var spinner = document.getElementById("quickAddSpinner");
    var button = document.getElementById("quickAddButton");

    if (!form || !feedback || !spinner || !button) {
        return;
    }

    function setBusy(isBusy) {
        button.disabled = isBusy;
        spinner.className = isBusy ? "spinner" : "";
        spinner.innerHTML = "";
    }

    function showMessage(success, message) {
        feedback.className = success ? "message-success" : "message-error";
        feedback.textContent = message;
        feedback.focus();
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();

        feedback.className = "";
        feedback.textContent = "";
        setBusy(true);

        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            credentials: "same-origin",
        })
            .then(function (response) {
                return response.json().then(function (body) {
                    if (!response.ok) {
                        throw body;
                    }
                    return body;
                });
            })
            .then(function (body) {
                setBusy(false);
                showMessage(Boolean(body.success), body.message || "Done.");
                if (body.success) {
                    form.reset();
                }
            })
            .catch(function (error) {
                setBusy(false);
                showMessage(false, error.message || "An error occurred. Please try again.");
            });
    });
})();
