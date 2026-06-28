// static/login.js

document.addEventListener("DOMContentLoaded", function () {
console.log("Mom's Care Login Page Loaded");


const form = document.querySelector("form");

if (!form) {
    console.log("Login form not found");
    return;
}

form.addEventListener("submit", function () {

    const email = document.querySelector(
        'input[name="email"]'
    ).value.trim();

    const password = document.querySelector(
        'input[name="password"]'
    ).value.trim();

    if (email === "" || password === "") {

        alert(
            "Please enter email and password"
        );

        event.preventDefault();

        return false;
    }

    return true;
});


});
