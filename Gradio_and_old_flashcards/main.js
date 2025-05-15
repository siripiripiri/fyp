// Define variables
let flashcardsData = null;
let currentCardIndex = 0;
let answeredCards = [];

// DOM elements
const initialScreen = document.getElementById('initialScreen');
const loadingScreen = document.getElementById('loadingScreen');
const appContainer = document.getElementById('appContainer');
const jsonPathInput = document.getElementById('jsonPath');
const loadBtn = document.getElementById('loadBtn');
const errorMessage = document.getElementById('errorMessage');

const flashcard = document.querySelector('.flashcard');
const questionElement = document.getElementById('question');
const answerElement = document.getElementById('answer');
const userAnswerInput = document.getElementById('userAnswer');
const submitBtn = document.getElementById('submitBtn');
const giveUpBtn = document.getElementById('giveUpBtn');
const prevBtn = document.getElementById('prevBtn');
const skipBtn = document.getElementById('skipBtn');
const feedbackElement = document.getElementById('feedback');
const counterElement = document.getElementById('counter');

// Load JSON data from file
loadBtn.addEventListener('click', () => {
    const jsonPath = jsonPathInput.value.trim();
    
    if (!jsonPath) {
        showError('Please enter a path to your JSON file.');
        return;
    }
    
    // Show loading screen
    initialScreen.style.display = 'none';
    loadingScreen.style.display = 'flex';
    errorMessage.style.display = 'none';
    
    // Fetch the JSON file
    fetch(jsonPath)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Check if the JSON has the expected structure
            if (!data.questions || !Array.isArray(data.questions)) {
                throw new Error('Invalid JSON format. Expected a "questions" array.');
            }
            
            // Initialize the app with the loaded data
            flashcardsData = data.questions;
            initializeApp();
        })
        .catch(error => {
            console.error('Error loading JSON:', error);
            showError(`Error loading JSON file: ${error.message}`);
            // Return to initial screen
            loadingScreen.style.display = 'none';
            initialScreen.style.display = 'block';
        });
});

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

// Initialize the application after JSON is loaded
function initializeApp() {
    // Hide loading screen and show app
    loadingScreen.style.display = 'none';
    appContainer.style.display = 'flex';
    appContainer.style.flexDirection = 'column'
    
    // Reset variables
    currentCardIndex = 0;
    answeredCards = [];
    
    // Display first card
    if (flashcardsData.length > 0) {
        displayCard(currentCardIndex);
        updateCounter();
    } else {
        showError('No flashcards found in the JSON file.');
        appContainer.style.display = 'none';
        initialScreen.style.display = 'block';
    }
}

// Function to display card
function displayCard(index) {
    if (index >= 0 && index < flashcardsData.length) {
        const card = flashcardsData[index];
        questionElement.textContent = card.question;
        answerElement.textContent = card.answer;
        
        // Reset UI state
        flashcard.classList.remove('flipped');
        userAnswerInput.value = '';
        feedbackElement.style.display = 'none';
        
        // Update counter
        updateCounter();
        
        // Update button states
        prevBtn.disabled = (index === 0);
        prevBtn.classList.toggle('disabled', index === 0);
        skipBtn.disabled = (index === flashcardsData.length - 1);
        skipBtn.classList.toggle('disabled', index === flashcardsData.length - 1);
    }
}

// Update counter function
function updateCounter() {
    counterElement.textContent = `Card ${currentCardIndex + 1} of ${flashcardsData.length}`;
}

// Check answer using GPT-3.5 (mock implementation)
async function checkAnswerWithGPT(userAnswer, correctAnswer) {
    // In a real implementation, you would make an API call to OpenAI
    // For this example, we'll simulate the API response
    
    // Add loading indicator to submit button
    submitBtn.innerHTML = 'Checking... <span class="loading"></span>';
    submitBtn.disabled = true;
    
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Simple comparison for demonstration - in reality you'd use the GPT API
    const userAnswerLower = userAnswer.toLowerCase().trim();
    const correctAnswerLower = correctAnswer.toLowerCase().trim();
    
    // Very basic similarity check - the real GPT API would be much more sophisticated
    const isCorrect = userAnswerLower === correctAnswerLower || 
                      correctAnswerLower.includes(userAnswerLower) || 
                      userAnswerLower.includes(correctAnswerLower);
    
    // Reset button
    submitBtn.innerHTML = 'Submit';
    submitBtn.disabled = false;
    
    return {
        isCorrect: isCorrect,
        explanation: isCorrect ? 
            "That's correct!" : 
            "Incorrect, Try again"
    };
}

// Event Listeners for the flashcard app functionality
// These are initialized after the JSON is loaded

// Submit button
document.getElementById('submitBtn').addEventListener('click', async () => {
    const userAnswer = userAnswerInput.value.trim();
    if (!userAnswer) return;
    
    const currentCard = flashcardsData[currentCardIndex];
    const result = await checkAnswerWithGPT(userAnswer, currentCard.answer);
    
    // Display feedback
    feedbackElement.textContent = result.explanation;
    feedbackElement.className = 'feedback ' + (result.isCorrect ? 'correct' : 'incorrect');
    feedbackElement.style.display = 'block';
    
    // If correct, mark as answered
    if (result.isCorrect && !answeredCards.includes(currentCardIndex)) {
        answeredCards.push(currentCardIndex);
    }
});

// Give up button
document.getElementById('giveUpBtn').addEventListener('click', () => {
    flashcard.classList.add('flipped');
});

// Previous button
document.getElementById('prevBtn').addEventListener('click', () => {
    if (currentCardIndex > 0) {
        currentCardIndex--;
        displayCard(currentCardIndex);
    }
});

// Skip button
document.getElementById('skipBtn').addEventListener('click', () => {
    if (currentCardIndex < flashcardsData.length - 1) {
        currentCardIndex++;
        displayCard(currentCardIndex);
    }
});

// Allow flipping card by clicking on it
flashcard.addEventListener('click', () => {
    flashcard.classList.toggle('flipped');
});

// Allow submitting by pressing Enter
userAnswerInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        submitBtn.click();
    }
});
