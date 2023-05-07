// Get the form element
const form = document.querySelector('#signup');

// Get the input fields
const emailField = document.querySelector('#email');
const passwordField = document.querySelector('#pass');
const confirmPasswordField = document.querySelector('#cpass');
const fnameField = document.querySelector('#fname');
const lnameField = document.querySelector('#lname');

// Get the error message element
const errorMessage = document.querySelector('#error');

// Disable sign-in button by default
const signInButton = document.querySelector('#submit');
signInButton.disabled = true;

// Add event listener to form submit
form.addEventListener('submit', (event) => {
  event.preventDefault();

  // Perform validation on form fields
  let valid = true;

  if (!emailField.value.includes('@')) {
    valid = false;
    errorMessage.textContent = 'Invalid email address';
  } else if (passwordField.value !== confirmPasswordField.value) {
    valid = false;
    errorMessage.textContent = 'Passwords do not match';
  } else if (fnameField.value === '' || lnameField.value === '') {
    valid = false;
    errorMessage.textContent = 'Please enter your first and last name';
  }

  // If validation fails, disable sign-in button and show error message
  if (!valid) {
    signInButton.disabled = true;
    errorMessage.style.display = 'block';
  } else {
    signInButton.disabled = false;
    errorMessage.style.display = 'none';
    
    // Submit the form if validation passes
    form.submit();
  }
});