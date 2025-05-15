// src/components/ResultMessage.jsx
import { FaCheckCircle, FaTimesCircle } from 'react-icons/fa';

const ResultMessage = ({ isCorrect }) => {
  if (isCorrect === null) return null;

  return (
    <div className={`result-message ${isCorrect ? 'correct' : 'incorrect'}`}>
      {isCorrect ? 'Correct' : 'Wrong'}
      {isCorrect ? <FaCheckCircle /> : <FaTimesCircle />}
    </div>
  );
};

export default ResultMessage;