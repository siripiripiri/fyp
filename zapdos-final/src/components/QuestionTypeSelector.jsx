// src/components/QuestionTypeSelector.jsx

const QUESTION_TYPES = [
  { label: "Multiple Choice (MCQs)", value: "MCQs" },
  { label: "Short Answer", value: "Short Answer" },
  { label: "Fill-in-the-Blanks", value: "Fill-in-the-Blanks" },
  { label: "One-word Answer", value: "One-word Answer" },
  { label: "True or False", value: "True or False" },
];

const QuestionTypeSelector = ({ selectedType, onTypeChange, disabled }) => {
  return (
    <div className="question-type-selector neumorphism-card" style={{ padding: '20px', marginBottom: '20px' }}>
      <h3 style={{ marginTop: '0', marginBottom: '15px', color: '#4a5a70' }}>Select Question Type:</h3>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', justifyContent: 'center' }}>
        {QUESTION_TYPES.map(type => (
          <button
            key={type.value}
            className={`neumorphism-button ${selectedType === type.value ? 'selected' : ''}`}
            onClick={() => onTypeChange(type.value)}
            disabled={disabled}
          >
            {type.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuestionTypeSelector;