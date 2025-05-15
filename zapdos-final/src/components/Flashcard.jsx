// src/components/Flashcard.jsx
import { useEffect, useState } from 'react'; // Combined React import
import { checkAnswerSimilarity } from '../utils/answerSimilarity';
import AnswerInput from './AnswerInput';
import FeedbackButtons from './FeedbackButtons';
import ResultMessage from './ResultMessage';

const Flashcard = ({ cardData, onSubmitAnswer, onNextCard, isCurrent, style }) => {
  // Destructure source_page along with other card data
  const { id, question, answer, options, question_type, source_page } = cardData;

  const [isFlipped, setIsFlipped] = useState(false);
  const [userSelection, setUserSelection] = useState(''); 
  const [isCorrect, setIsCorrect] = useState(null);
  const [showEvaluation, setShowEvaluation] = useState(false);
  const [selectedFeedback, setSelectedFeedback] = useState(null);

  // For potential inline FIB (currently uses AnswerInput fallback)
  const [fibInputs, setFibInputs] = useState({}); 
  // const BLANK_PLACEHOLDER = "_____"; // Not used in current fallback

  useEffect(() => {
    // Reset card state when cardData (specifically id) changes
    setIsFlipped(false);
    setUserSelection('');
    setIsCorrect(null);
    setShowEvaluation(false);
    setSelectedFeedback(null);
    setFibInputs({}); 
  }, [id]); 

  const handleGeneralSubmit = () => {
    // Check if an answer is provided for types that require it before submit
    // True/False submits on click, so it won't hit this button with empty userSelection
    if (!userSelection && (question_type === "MCQs" || question_type === "One-word Answer" || question_type === "Short Answer" || question_type === "Fill-in-the-Blanks")) { 
        alert("Please provide an answer or make a selection.");
        return;
    }

    let submittedAnswer = userSelection;
    let correct = false;

    // For FIB with the current fallback, userSelection directly holds the typed answer
    // If inline FIB was implemented, this logic would need to construct the answer from fibInputs
    // if (question_type === "Fill-in-the-Blanks") {
    //     const firstBlankKey = Object.keys(fibInputs)[0]; // Simplified: assumes one blank
    //     submittedAnswer = firstBlankKey ? fibInputs[firstBlankKey] : "";
    //     correct = checkAnswerSimilarity(submittedAnswer, answer);
    // } else {
    //     correct = checkAnswerSimilarity(submittedAnswer, answer);
    // }
    correct = checkAnswerSimilarity(submittedAnswer, answer); // General case
    
    setIsCorrect(correct);
    setIsFlipped(true);
    setShowEvaluation(true);
    onSubmitAnswer(id, correct); // Notify parent stack about the answer correctness
  };

  // This handler is not directly used if AnswerInput calls onSubmit, but good for completeness
  // const handleAnswerInputChange = (textAnswer) => { 
  //   setUserSelection(textAnswer);
  // };

  const handleMcqOptionSelect = (option) => {
    setUserSelection(option);
  };

  const handleTrueFalseSelect = (choice) => {
    setUserSelection(choice); // "True" or "False"
    // For T/F, evaluate and flip immediately
    const correct = checkAnswerSimilarity(choice, answer);
    setIsCorrect(correct);
    setIsFlipped(true);
    setShowEvaluation(true);
    onSubmitAnswer(id, correct);
  };

  // For potential inline FIB
  // const handleFibInputChange = (blankIndex, value) => {
  //   setFibInputs(prev => ({ ...prev, [blankIndex]: value }));
  // };


  const handleFeedbackSelect = (feedback) => {
    setSelectedFeedback(feedback);
  };

  const handleNext = () => {
    if (!selectedFeedback) {
      alert("Please select a feedback level for this card.");
      return;
    }
    onNextCard(id, selectedFeedback);
  };

  // --- Render different input types based on question_type ---
  const renderInteractionArea = () => {
    if (showEvaluation || !isCurrent) return null; // Don't show input if evaluated or not the current card

    switch (question_type) {
      case "MCQs":
        return (
          <div className="mcq-options-container">
            {options && options.map((option, index) => (
              <button
                key={index}
                className={`neumorphism-button mcq-option ${userSelection === option ? 'selected' : ''}`}
                onClick={() => handleMcqOptionSelect(option)}
              >
                {option}
              </button>
            ))}
            <button 
                onClick={handleGeneralSubmit} 
                className="neumorphism-button submit-mcq-tf" // Reusing class for similar styling
                disabled={!userSelection} // Enable only if an option is selected
            >
                Submit Choice
            </button>
          </div>
        );
      case "True or False":
        return (
          <div className="true-false-options-container">
            <button
              className={`neumorphism-button tf-option ${userSelection === "True" ? 'selected' : ''}`}
              onClick={() => handleTrueFalseSelect("True")}
            >
              True
            </button>
            <button
              className={`neumorphism-button tf-option ${userSelection === "False" ? 'selected' : ''}`}
              onClick={() => handleTrueFalseSelect("False")}
            >
              False
            </button>
            {/* Submission for T/F is handled by handleTrueFalseSelect on click */}
          </div>
        );
      case "Fill-in-the-Blanks": // Currently uses standard AnswerInput
        return (
            <div className="answer-section">
                <AnswerInput 
                    onSubmit={(val) => { setUserSelection(val); handleGeneralSubmit(); }} 
                    initialValue={userSelection} // To prefill if user comes back to edit
                    disabled={showEvaluation} 
                />
            </div>
        );
      case "One-word Answer":
      case "Short Answer":
      default: // Fallback for any other types or if question_type is missing
        return (
          <div className="answer-section">
            <AnswerInput 
                onSubmit={(val) => { setUserSelection(val); handleGeneralSubmit(); }} 
                initialValue={userSelection}
                disabled={showEvaluation} 
            />
          </div>
        );
    }
  };
  
  // The renderQuestionContent function was removed as the simple div is sufficient for now.
  // If inline FIB was fully implemented, it might be revived.

  return (
    <div className="flashcard-wrapper" style={{ ...style }}> {/* zIndex is applied by parent FlashcardStack */}
      <div className={`flashcard ${isFlipped ? 'is-flipped' : ''}`}>
        <div className="flashcard-face flashcard-front">
          <div className="flashcard-content" dangerouslySetInnerHTML={{ __html: question?.replace(/\n/g, '<br/>') }} />
          {renderInteractionArea()}
        </div>
        <div 
          className={`flashcard-face flashcard-back ${
            isCorrect === null ? '' : isCorrect ? 'correct' : 'incorrect'
          }`}
        >
          {/* Container for main answer content + source page */}
          <div className="flashcard-content-container"> 
            <div className="flashcard-answer-text"> {/* Specific class for answer text */}
              <strong>Answer:</strong> <span dangerouslySetInnerHTML={{ __html: answer?.replace(/\n/g, '<br/>') }} />
            </div>
            {/* Display source page if available */}
            {source_page && (
              <div className="flashcard-source-page">(Source: Page {source_page})</div>
            )}
            {/* Display user's incorrect MCQ choice */}
            {question_type === "MCQs" && userSelection && !isCorrect && isFlipped && (
                <p className="flashcard-user-choice">Your choice: {userSelection}</p>
            )}
          </div>

          {/* Container for evaluation controls (result, feedback, next) */}
          {showEvaluation && isCurrent && (
            <div className="flashcard-evaluation-controls">
              <ResultMessage isCorrect={isCorrect} />
              <div className="feedback-section">
                <FeedbackButtons 
                  onFeedbackSelect={handleFeedbackSelect} 
                  selectedFeedback={selectedFeedback}
                  disabled={!showEvaluation}
                />
              </div>
              <div className="navigation-controls">
                <button 
                  className="neumorphism-button" 
                  onClick={handleNext}
                  disabled={!selectedFeedback}
                >
                  Next Card
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Flashcard;