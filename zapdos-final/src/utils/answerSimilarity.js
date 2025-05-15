// src/utils/answerSimilarity.js
import { compareTwoStrings } from 'string-similarity';

const SIMILARITY_THRESHOLD = 0.7; // Adjust as needed (0.7 means 70% similar)

export const checkAnswerSimilarity = (userAnswer, correctAnswer) => {
  if (!userAnswer || !correctAnswer) {
    return false;
  }

  const Preprocess = (text) => {
    return text.toLowerCase().trim().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"").replace(/\s{2,}/g," ");
  }

  const processedUserAnswer = Preprocess(userAnswer);
  const processedCorrectAnswer = Preprocess(correctAnswer);

  if (processedUserAnswer === processedCorrectAnswer) {
    return true;
  }
  
  const similarity = compareTwoStrings(processedUserAnswer, processedCorrectAnswer);
  
  return similarity >= SIMILARITY_THRESHOLD;
};