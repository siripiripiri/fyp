// src/components/FlashcardStack.jsx
import { useEffect, useMemo, useState } from 'react';
import useSpacedRepetition from '../hooks/useSpacedRepetition';
import Flashcard from './Flashcard';

const MAX_VISIBLE_CARDS = 3;

const FlashcardStack = ({ initialCards, onStackComplete, currentRepetition }) => {
  const [cards, setCards] = useState([]);
  const [processedCardInfo, setProcessedCardInfo] = useState({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isCompleting, setIsCompleting] = useState(false);

  const { calculateNextReview } = useSpacedRepetition();

  useEffect(() => {
    const stackToReview = initialCards.map(card => ({
      ...card,
      isFlipped: false,
      userAnswer: '',
      showFeedback: false,
    }));
    setCards(stackToReview);
    setCurrentIndex(0);
    setProcessedCardInfo({});
    setIsCompleting(false);
  }, [initialCards]);

  const handleAnswerSubmit = (cardId, isCorrect) => {
    setProcessedCardInfo(prev => ({
      ...prev,
      [cardId]: { ...prev[cardId], isCorrect }
    }));
    setCards(currentCards => currentCards.map(c => 
        c.id === cardId ? { ...c, showFeedback: true } : c
    ));
  };

  const handleNextCard = (cardId, feedback) => {
    const cardToUpdate = cards.find(c => c.id === cardId);
    if (cardToUpdate) {
        const updatedCardWithSM2 = calculateNextReview(cardToUpdate, feedback);
        setProcessedCardInfo(prev => ({
            ...prev,
            [cardId]: { ...prev[cardId], feedback, sm2Data: updatedCardWithSM2 }
        }));
    }
    setIsCompleting(true);
    setTimeout(() => {
      if (currentIndex < cards.length - 1) {
        setCurrentIndex(prev => prev + 1);
        setIsCompleting(false); 
      } else {
        const fullyProcessedCardsThisRound = cards.map(c => {
            const info = processedCardInfo[c.id];
            return (info && info.sm2Data) ? info.sm2Data : c; 
        });
        onStackComplete(fullyProcessedCardsThisRound);
      }
    }, 600);
  };
  
  const currentCardData = cards[currentIndex];
  const totalCardsInStack = cards.length;

  const visibleCardsForStackEffect = useMemo(() => {
    if (!cards.length) return [];
    const display = [];
    for (let i = 0; i < Math.min(MAX_VISIBLE_CARDS, cards.length - currentIndex); i++) {
      if (cards[currentIndex + i]) {
        display.push(cards[currentIndex + i]);
      }
    }
    
    return display.reverse(); 
  }, [cards, currentIndex]);


  if (!currentCardData) { 
    return null; 
  }

  return (
    <div className="flashcard-stack-wrapper"> 
      <div className="flashcard-stack-container">
        {currentRepetition > 0 && totalCardsInStack > 0 && (
            <div className="repetition-counter">
                Round: {currentRepetition}
            </div>
        )}
        
        {visibleCardsForStackEffect.map((card, indexInReversedVisible) => {
          
          const isTheActualTopCard = (card.id === currentCardData.id); 

          const depth = (visibleCardsForStackEffect.length - 1) - indexInReversedVisible;

          let scale = 1 - depth * 0.05;
          let yOffset = depth * -10;
          let xOffset = depth * 10;
          let opacity = 1;
          let current_zIndex = (10 + visibleCardsForStackEffect.length) - depth; // Higher zIndex for cards more "in front"

          let transform = `translateY(${yOffset}px) translateX(${xOffset}px) scale(${scale})`;
          let transition = `transform 0.5s ease-out, opacity 0.5s ease-out`;
          let transitionDelay = '0s';

          if (isCompleting && isTheActualTopCard) {
            opacity = 0;
            transform = `translateX(-120%) translateY(${yOffset + 20}px) rotate(-15deg) scale(${scale * 0.9})`;
            transitionDelay = '0.05s'; 
          }
          
          const cardStyle = {
            transform: transform,
            opacity: opacity,
            transition: transition,
            transitionDelay: transitionDelay,
            
            zIndex: current_zIndex,
          };

          return (
            <Flashcard
              key={card.id} 
              cardData={card}
              onSubmitAnswer={handleAnswerSubmit}
              onNextCard={handleNextCard}
              isCurrent={isTheActualTopCard}
              style={cardStyle}

            />
          );
        })}
      </div>
      {totalCardsInStack > 0 && (
        <div className="flashcard-progress-counter">
          {currentIndex + 1} / {totalCardsInStack}
        </div>
      )}
    </div>
  );
};

export default FlashcardStack;