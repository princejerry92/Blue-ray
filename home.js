document.getElementById('nextChoice').addEventListener('click', function() {
    // Get the selected role
    const adminRadio = document.getElementById('HomeAdmin');
    const studentRadio = document.getElementById('HomeStudent');

    // Redirect based on the checked radio button
    if (adminRadio.checked) {
      // Redirect to Admin login
      window.location.href = '/login'; 
    } else if (studentRadio.checked) {
      // Redirect to Student login
      window.location.href = '/stlogin'; // This will be rendered by Flask
    } else {
      alert("Please select a role before proceeding."); // Alert if no option is selected
    }
  });