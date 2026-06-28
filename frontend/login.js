// login.js

const loginForm = document.querySelector("form");

// Login Validation
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.querySelector('input[type="email"]').value.trim();
    const password = document.querySelector('input[type="password"]').value.trim();

    if (!email || !password) {
        alert("Please enter email and password");
        return;
    }

    try {
        // Call backend API
        const response = await fetch("/api/v1/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {
            alert("Login Successful");
            window.location.href = "dashboard.html";
        } else {
            alert(data.message || "Login failed");
        }
    } catch (error) {
        alert("Error: " + error.message);
    }
});
