// src/components/FeedbackButtons.jsx

const FEEDBACK_OPTIONS = [
  { label: "Repeat", value: "repeat" },
  { label: "Difficult", value: "difficult" },
  { label: "Medium", value: "medium" },
  { label: "Easy", value: "easy" },
];

const FeedbackButtons = ({ onFeedbackSelect, selectedFeedback, disabled }) => {
  return (
    <div className="feedback-buttons-container">
      <p style={{width: '100%', textAlign: 'center', marginBottom: '5px', fontSize: '0.9rem', color: '#555'}}>How did you find this card?</p>
      {FEEDBACK_OPTIONS.map(option => (
        <button
          key={option.value}
          className={`neumorphism-button ${selectedFeedback === option.value ? 'selected' : ''}`}
          onClick={() => onFeedbackSelect(option.value)}
          disabled={disabled}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
};

export default FeedbackButtons;