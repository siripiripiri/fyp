
import { useEffect, useState } from 'react';

const AnswerInput = ({ onSubmit, disabled, initialValue = '' }) => {
  const [answer, setAnswer] = useState(initialValue);

  useEffect(() => {
    setAnswer(initialValue);
  }, [initialValue]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (answer.trim() || disabled) { 
      onSubmit(answer);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="answer-input-container">
      <textarea
        className="neumorphism-input"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Type your answer here..."
        rows="3"
        disabled={disabled}
      />
      <button 
        type="submit" 
        className="neumorphism-button" 
        disabled={disabled || !answer.trim()}
      >
        Submit Answer
      </button>
    </form>
  );
};

export default AnswerInput;