let messages = []; // To store the messages fetched from the server
let currentMessageIndex = 0; // To track the current message being typed

async function fetchMessages() {
  try {
    const response = await fetch('/init');
    console.log('/init endpoint called ');
    const data = await response.json();
    messages = data.messages;
    startTyping(); // Start typing after fetching messages
    console.log('typing function called');
  } catch (error) {
    console.error('Error fetching messages:', error);
  }
}

function typeMessage(message, callback) {
  const element = document.getElementById('dynamicMessage');
  let index = 0;
  element.innerHTML = ''; // Clear the previous content

  function type() {
    if (index < message.length) {
      element.innerHTML += message.charAt(index);
      index++;
      setTimeout(type, 20); // Adjust typing speed here (100ms per character)
    } else if (callback) {
      setTimeout(callback, 1000); // Pause before the next message
    }
  }

  type();
}

function startTyping() {
  if (currentMessageIndex < messages.length) {
    typeMessage(messages[currentMessageIndex], () => {
      currentMessageIndex++;
      if (currentMessageIndex === messages.length) {
        // Show modal after typing all messages
        showModal();
      } else {
        startTyping(); // Start typing the next message
      }
    });
  }
}

function showModal() {
  // Remove all child elements from the <body> element
  document.body.innerHTML = '';

  // Create the modal dialog box
  const modal = `
    <div class="modal" tabindex="-1" role="dialog">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <header class="modal-header">
            <h5 class="modal-title">Installation Complete!</h5>
          </header>
          <main class="modal-body">
            <p>Your Installation is complete! click ok to move to the next page.</p>
          </main>
          <footer class="modal-footer">
            <button type="button" class="btn btn-primary" onclick="window.location.href='/welcome'">Ok</button>
          </footer>
        </div>
      </div>
    </div>
  `;

  // Append the modal dialog box to the <body> element
  document.body.innerHTML = modal;
}


// Optional: Automatically fetch and start typing on page load
fetchMessages();