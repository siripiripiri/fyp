// src/hooks/useSpacedRepetition.js
import { useCallback } from 'react';

// SM-2 Algorithm constants
const MIN_EASE_FACTOR = 1.3;

// Map feedback labels to quality scores (q: 0-5)
const feedbackToQuality = {
  repeat: 0,    // Forgot completely
  difficult: 2, // Recalled, but with significant difficulty
  medium: 4,    // Recalled correctly after some thought
  easy: 5,      // Recalled perfectly
};

const useSpacedRepetition = () => {
  const calculateNextReview = useCallback((card, qualityResponse) => {
    let { interval, repetitions, easeFactor, id, question, answer } = card;
    const quality = feedbackToQuality[qualityResponse] !== undefined ? feedbackToQuality[qualityResponse] : 3; // Default to 'hard' if unknown

    if (quality < 3) { // Incorrect or very difficult recall
      repetitions = 0;
      interval = 1; // Review again very soon (next "day" or session cycle)
    } else { // Correct recall
      repetitions += 1;
      if (repetitions === 1) {
        interval = 1;
      } else if (repetitions === 2) {
        interval = 6;
      } else {
        interval = Math.round(interval * easeFactor);
      }
    }

    // Update ease factor
    easeFactor = easeFactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02));
    if (easeFactor < MIN_EASE_FACTOR) {
      easeFactor = MIN_EASE_FACTOR;
    }

    // dueDate is not strictly used for sorting in this immediate session-based app,
    // but good to calculate for a more complete SM-2 implementation.
    // For sorting in this app, we'll prioritize based on quality response primarily.
    const now = new Date();
    const dueDate = new Date(now.setDate(now.getDate() + interval)).toISOString();

    return { ...card, id, question, answer, interval, repetitions, easeFactor, dueDate, lastQuality: quality };
  }, []);


  const getNextStack = useCallback((processedCards) => {
    // processedCards is an array of cards, each having been updated by calculateNextReview
    // and thus having a 'lastQuality' score.

    // Simple sorting for next round:
    // 1. Cards marked as 'repeat' (quality 0-1) or incorrect.
    // 2. Cards marked as 'difficult' (quality 2-3).
    // 3. Cards marked 'medium' (quality 4).
    // 4. Cards marked 'easy' (quality 5).
    
    // For cards with the same quality, you could add secondary sort (e.g., original order, or shuffle)
    // For now, maintain relative order within quality groups.

    const sortedCards = [...processedCards].sort((a, b) => {
      
      const qualityA = a.lastQuality !== undefined ? a.lastQuality : 3;
      const qualityB = b.lastQuality !== undefined ? b.lastQuality : 3;
      
      if (qualityA !== qualityB) {
        return qualityA - qualityB; 
      }

      return 0; 
    });

    return sortedCards.map(card => ({ ...card, isFlipped: false, userAnswer: '', showFeedback: false })); // Reset for next round
  }, []);

  return { calculateNextReview, getNextStack };
};

export default useSpacedRepetition;