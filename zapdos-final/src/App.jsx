// src/App.jsx
import { useEffect, useRef, useState } from 'react'; // Added useEffect and useRef
import './App.css';
import FileUpload from './components/FileUpload';
import FlashcardStack from './components/FlashcardStack';
import QuestionTypeSelector from './components/QuestionTypeSelector';
import useSpacedRepetition from './hooks/useSpacedRepetition';
import { uploadFileAndGetFlashcards } from './services/api';

function App() {
  const [flashcards, setFlashcards] = useState([]);
  const [currentStack, setCurrentStack] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [showFlashcardsView, setShowFlashcardsView] = useState(false);
  const [isFileSelectedForProcessing, setIsFileSelectedForProcessing] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedQuestionType, setSelectedQuestionType] = useState('');
  
  const [repetitionRound, setRepetitionRound] = useState(0);
  const [stackKey, setStackKey] = useState(0);

  // For the loading timer
  const [elapsedTime, setElapsedTime] = useState(0);
  const timerIntervalRef = useRef(null); // To store the interval ID

  const { getNextStack } = useSpacedRepetition();

  // Effect to manage the loading timer
  useEffect(() => {
    if (isLoading) {
      setElapsedTime(0); // Reset timer
      const startTime = Date.now();
      timerIntervalRef.current = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000); // Update every second
    } else {
      clearInterval(timerIntervalRef.current); // Clear interval when not loading
      timerIntervalRef.current = null;
    }

    // Cleanup function to clear interval if component unmounts while loading
    return () => {
      clearInterval(timerIntervalRef.current);
    };
  }, [isLoading]); // Dependency array: only re-run if isLoading changes


  const handleFileSelected = (file) => {
    setSelectedFile(file);
    setIsFileSelectedForProcessing(true);
    setSelectedQuestionType('');
    setShowFlashcardsView(false);
    setFlashcards([]);
    setCurrentStack([]);
    setError(null);
    setRepetitionRound(0);
  };

  const handleProcessRequest = async () => {
    if (!selectedFile || !selectedQuestionType) {
      setError("Please select a file and a question type to proceed.");
      return;
    }
    // setIsLoading(true) will trigger the timer effect
    setIsLoading(true);
    setError(null);
    setShowFlashcardsView(false); 
    try {
      const generatedFlashcards = await uploadFileAndGetFlashcards(selectedFile, selectedQuestionType);
      
      if (generatedFlashcards && generatedFlashcards.length > 0) {
        setFlashcards(generatedFlashcards); 
        setCurrentStack(generatedFlashcards); 
        setRepetitionRound(1);
        setStackKey(prev => prev + 1);
        setShowFlashcardsView(true);
        setIsFileSelectedForProcessing(false);
      } else {
        setError("No flashcards were generated. The file might be empty or the content unsuitable.");
        setFlashcards([]);
        setCurrentStack([]);
      }
    } catch (err) {
      console.error("Failed to process file and generate flashcards:", err);
      setError(err.message || "Failed to load flashcards. Please check your file or settings and try again.");
      setFlashcards([]);
      setCurrentStack([]);
    } finally {
      // setIsLoading(false) will stop the timer via the effect
      setIsLoading(false);
    }
  };

  const handleStackComplete = (processedCardsFromStack) => {
    setFlashcards(processedCardsFromStack); 
    setShowFlashcardsView(false);
  };

  const handleStartNextRound = () => {
    if (!flashcards.length) return;
    
    const newStackOrdered = getNextStack(flashcards);
    const reorderedAndResetCards = newStackOrdered.map(card => ({
        ...card,
        isFlipped: false,
        userAnswer: '',
        showFeedback: false,
    }));

    setFlashcards(reorderedAndResetCards);
    setCurrentStack(reorderedAndResetCards);
    setRepetitionRound(prev => prev + 1);
    setStackKey(prev => prev + 1);
    setShowFlashcardsView(true);
  };

  const resetAppForNewFile = () => {
    setFlashcards([]);
    setCurrentStack([]);
    setShowFlashcardsView(false);
    setIsFileSelectedForProcessing(false);
    setSelectedFile(null);
    setSelectedQuestionType('');
    setError(null);
    setRepetitionRound(0);
    setStackKey(0);
  };

  const formatTime = (totalSeconds) => {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="loading-gif-container neumorphism-card">
          <img src="/zapdos.gif" alt="Loading..." className="loading-gif" />
          <p>Generating your flashcards, please wait...</p>
          <p className="loading-timer">{formatTime(elapsedTime)}</p> {/* Display formatted time */}
          <p className="loading-subtext">(Zapdos is working hard!)</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="error-message-container neumorphism-card">
          <p style={{fontSize: '1.2rem', fontWeight: 'bold'}}>Oops! Something went wrong.</p>
          <p>{error}</p>
          <button onClick={resetAppForNewFile} className="neumorphism-button" style={{marginTop: '20px'}}>
            Try Uploading Again
          </button>
        </div>
      );
    }

    if (showFlashcardsView && currentStack.length > 0) {
      return (
        <FlashcardStack
          key={`stack-${stackKey}`}
          initialCards={currentStack}
          onStackComplete={handleStackComplete}
          currentRepetition={repetitionRound}
        />
      );
    }

    if (!showFlashcardsView && flashcards.length > 0 && !isFileSelectedForProcessing) {
      return (
        <div className="flashcard-stack-empty neumorphism-card" style={{ padding: '40px', marginTop: '30px' }}>
          <h2>All cards reviewed for this round!</h2>
          <div style={{marginTop: '20px', display: 'flex', gap: '15px', justifyContent: 'center'}}>
            <button onClick={handleStartNextRound} className="neumorphism-button" style={{padding: '15px 25px'}}>
              Let's Go Again! (Round {repetitionRound + 1})
            </button>
            <button onClick={resetAppForNewFile} className="neumorphism-button" style={{backgroundColor: '#f0f2f5', padding: '15px 25px'}}>
              Upload New File
            </button>
          </div>
        </div>
      );
    }
    
    if (isFileSelectedForProcessing) {
      return (
        <>
          {selectedFile && <p style={{marginBottom: '15px', fontSize: '1.1rem', color: '#555'}}>File selected: <strong>{selectedFile.name}</strong></p>}
          <QuestionTypeSelector
            selectedType={selectedQuestionType}
            onTypeChange={setSelectedQuestionType}
            disabled={isLoading}
          />
          <div style={{marginTop: '20px', display: 'flex', gap: '15px', justifyContent: 'center'}}>
            <button 
              onClick={handleProcessRequest} 
              className="neumorphism-button" 
              disabled={isLoading || !selectedQuestionType}
              style={{padding: '15px 30px', fontSize: '1.1rem'}}
            >
              Generate Flashcards
            </button>
            <button 
              onClick={resetAppForNewFile} 
              className="neumorphism-button" 
              style={{backgroundColor: '#e9ecef'}}
            >
              Cancel
            </button>
          </div>
        </>
      );
    }

    return <FileUpload onFileUpload={handleFileSelected} isLoading={isLoading} />;
  };

  return (
    <div className="App">
      <header style={{ marginBottom: '30px'}}>
        <h1 style={{ fontSize: '2.5rem', color: '#4a5a70', fontWeight: '600', margin: '0'}}>
          Recallium - ZAPDOS
        </h1>
        <p style={{color: '#6b7b90', marginTop: '5px'}}>Upload a file, select question type, and master the content.</p>
      </header>
      {renderContent()}
    </div>
  );
}

export default App;