// src/services/api.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export const uploadFileAndGetFlashcards = async (file, questionType) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('question_type', questionType);

  try {
    const response = await fetch(`${API_BASE_URL}/api/generate-flashcards`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = `HTTP error! status: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.message || `Server error (status ${response.status})`;
      } catch (e) {
        console.warn("Could not parse error response JSON", e);
        if (response.statusText) {
          errorMessage = `Server error: ${response.statusText} (status ${response.status})`;
        }
      }
      throw new Error(errorMessage);
    }

    const data = await response.json(); // Expected: { questions: [{ id, question, answer, options?, question_type?, source_page? }] }

    if (data && Array.isArray(data.questions)) {
      return data.questions.map((q, index) => ({
        id: q.id || `card-${Date.now()}-${index}`,
        question: q.question,
        answer: q.answer,
        options: q.options || null, // For MCQs
        question_type: q.question_type || questionType, // Use specific type from card, or fallback
        source_page: q.source_page || null, // <<<< Ensure this is being mapped
        // SM-2 initial values
        interval: 0,
        repetitions: 0,
        easeFactor: 2.5,
        dueDate: new Date().toISOString(),
        isFlipped: false,
        userAnswer: '',
        showFeedback: false,
        lastQuality: undefined,
      }));
    } else {
      console.error("Received malformed flashcard data from server:", data);
      throw new Error("Received malformed data from the server. Expected { questions: [...] } structure.");
    }

  } catch (error) {
    console.error("Error in uploadFileAndGetFlashcards service:", error);
    throw error;
  }
};