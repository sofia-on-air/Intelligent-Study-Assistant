import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./App.css";
import "./Flashcards.css";

export default function Flashcards() {
  const navigate = useNavigate();
  const userId = localStorage.getItem("userId");

  const [sets, setSets] = useState([]);
  const [loadingSets, setLoadingSets] = useState(false);
  const [selectedSetId, setSelectedSetId] = useState(null);

  const [showStep1, setShowStep1] = useState(false);
  const [topic, setTopic] = useState("");
  const [checkingTopic, setCheckingTopic] = useState(false);
  const [topicError, setTopicError] = useState(false);

  const [showStep2, setShowStep2] = useState(false);
  const [setName, setSetName] = useState("");
  const [wordsInput, setWordsInput] = useState("");
  const [generating, setGenerating] = useState(false);

  const [studyCards, setStudyCards] = useState(null);
  const [queue, setQueue] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    fetchSets();
  }, []);

  const fetchSets = async () => {
    setLoadingSets(true);
    try {
      const res = await fetch(`http://localhost:8080/my-flashcards/${userId}`);
      const data = await res.json();
      setSets(data.sets || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSets(false);
    }
  };

  const handleCheckTopic = async () => {
    if (!topic.trim()) return;
    setCheckingTopic(true);
    setTopicError(false);
    try {
      const res = await fetch("http://localhost:8080/generate-flashcards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          name: "__check__",
          words: ["test"],
          user_id: parseInt(userId),
        }),
      });
      const data = await res.json();
      if (data.status === "unknown_topic") {
        setTopicError(true);
      } else {
        setShowStep1(false);
        setShowStep2(true);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setCheckingTopic(false);
    }
  };

  const handleGenerate = async () => {
    const words = [];
    const rawWords = wordsInput.split(", ");
    for (const word of rawWords) {
      if (word.trim()) {
        words.push(word.trim());
      }
    }
    if (!setName.trim() || words.length === 0) return;
    setGenerating(true);
    try {
      const res = await fetch("http://localhost:8080/generate-flashcards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          name: setName,
          words,
          user_id: parseInt(userId),
        }),
      });
      const data = await res.json();
      if (data.status === "success") {
        setShowStep2(false);
        setTopic("");
        setSetName("");
        setWordsInput("");
        await fetchSets();
        
        if (data.not_found && data.not_found.length > 0) {
            alert(`Some words were not found in your materials and were skipped:\n• ${data.not_found.join("\n• ")}`);
        }
        
        startStudy(data.cards);
    } else {
        alert("Something went wrong: " + data.message);
    }
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const startStudy = (cards) => {
    const shuffled = [...cards].sort(() => Math.random() - 0.5);
    setStudyCards(cards);
    setQueue(shuffled);
    setCurrentIdx(0);
    setFlipped(false);
    setDone(false);
  };

  const handleStartExisting = () => {
    const found = sets.find((flashcardSet) => flashcardSet.set_id === selectedSetId);
    if (!found) return;
    startStudy(found.cards);
  };

  const handleKnow = () => {
    const newQueue = queue.filter((_, i) => i !== currentIdx);
    if (newQueue.length === 0) {
      setDone(true);
      return;
    }
    const nextIdx = currentIdx >= newQueue.length ? 0 : currentIdx;
    setQueue(newQueue);
    setCurrentIdx(nextIdx);
    setFlipped(false);
  };

  const handleDontKnow = () => {
    const card = queue[currentIdx];
    const remaining = queue.filter((_, i) => i !== currentIdx);
    if (remaining.length === 0) {
      setQueue([card]);
      setCurrentIdx(0);
      setFlipped(false);
      return;
    }
    const insertAt =
      currentIdx +
      1 +
      Math.floor(Math.random() * Math.max(1, remaining.length - currentIdx));
    const newQueue = [...remaining];
    newQueue.splice(Math.min(insertAt, newQueue.length), 0, card);
    setQueue(newQueue);
    const nextIdx = currentIdx >= newQueue.length ? 0 : currentIdx;
    setCurrentIdx(nextIdx);
    setFlipped(false);
  };// used ai

  const NavBar = () => (
    <nav className="home-navigation">
      <button onClick={() => navigate("/main")}>Home</button>
      <button onClick={() => navigate("/quizzes")}>Quizzes</button>
      <button onClick={() => navigate("/flashcards")}>Flashcards</button>
      <button onClick={() => navigate("/")}>Logout</button>
    </nav>
  );

  if (done) {
    return (
      <div className="home-page">
        <NavBar />
        <h2 className="welcome-title">You know all the cards!</h2>
        <p className="fc-done-text">Great job! All flashcards have been learned.</p>
        <button
          className="btn-auth"
          onClick={() => {
            setStudyCards(null);
            setQueue([]);
            setDone(false);
            fetchSets();
          }}
        >
          Back to Flashcards
        </button>
      </div>
    );
  }

  if (studyCards && queue.length > 0) {
    const card = queue[currentIdx];
    return (
      <div className="home-page">
        <NavBar />
        <p className="fc-study-counter">
          {queue.length} cards remaining
        </p>

        <div className="fc-card" onClick={() => setFlipped(!flipped)}>
          {!flipped ? (
            <div>
              <p className="fc-word">{card.front}</p>
              <p className="fc-hint">tap to see definition</p>
            </div>
          ) : (
            <p className="fc-definition">{card.back}</p>
          )}
        </div>

        {flipped && (
          <div className="fc-study-buttons">
            <button className="fc-btn-dont-know" onClick={handleDontKnow}>
              I don't know
            </button>
            <button className="fc-btn-know" onClick={handleKnow}>
              I know
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="home-page">
      <NavBar />
      {showStep1 && (
        <div className="fc-overlay">
          <div className="fc-popup">
            <h3>Enter topic</h3>
            {topicError ? (
              <>
                <p className="fc-popup-error">
                  Oops! I don't know this topic. Please upload related documents first.
                </p>
                <div className="fc-popup-buttons">
                  <button
                    className="btn-auth"
                    onClick={() => { setTopicError(false); setTopic(""); }}
                  >
                    Try again
                  </button>
                  <button
                    className="tool-btn"
                    onClick={() => { setShowStep1(false); setTopicError(false); setTopic(""); }}
                  >
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                <input
                  type="text"
                  placeholder="e.g. Machine Learning, Photosynthesis..."
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCheckTopic()}
                />
                <div className="fc-popup-buttons">
                  <button
                    className="btn-auth"
                    onClick={handleCheckTopic}
                    disabled={checkingTopic || !topic.trim()}
                  >
                    {checkingTopic ? "Checking..." : "Next →"}
                  </button>
                  <button
                    className="tool-btn"
                    onClick={() => { setShowStep1(false); setTopic(""); }}
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {showStep2 && (
        <div className="fc-overlay">
          <div className="fc-popup">
            <h3>Create flashcard set</h3>
            <label>Set name</label>
            <input
              type="text"
              placeholder="e.g. Biology Chapter 3"
              value={setName}
              onChange={(e) => setSetName(e.target.value)}
            />
            <label>
              Words / phrases <span>(separated by ", ")</span>
            </label>
            <textarea
              placeholder="e.g. photosynthesis, mitosis, DNA replication"
              value={wordsInput}
              onChange={(e) => setWordsInput(e.target.value)}
            />
            <div className="fc-popup-buttons">
              <button
                className="btn-auth"
                onClick={handleGenerate}
                disabled={generating || !setName.trim() || !wordsInput.trim()}
              >
                {generating ? "Generating..." : "Generate!"}
              </button>
              <button
                className="tool-btn"
                onClick={() => { setShowStep2(false); setSetName(""); setWordsInput(""); }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="flashcards-layout">

        <div className="flashcards-left">
          <h1 className="welcome-title">Flashcards</h1>
          <button className="tool-btn" onClick={() => setShowStep1(true)}>
            Generate new flashcards
          </button>
          <button
            className="tool-btn"
            onClick={handleStartExisting}
            disabled={!selectedSetId}
          >
            Take existing flashcards
          </button>
        </div>

        <div className="flashcards-list">
          <h3>My flashcard sets</h3>
          {loadingSets ? (
            <p className="fc-loading">Loading...</p>
          ) : sets.length === 0 ? (
            <p className="fc-empty">No flashcard sets yet. Generate your first one!</p>
          ) : (
            <div className="flashcards-list-inner">
              {sets.map((flashcardSet) => (
                <label
                  key={flashcardSet.set_id}
                  className={`flashcard-set-item ${selectedSetId === flashcardSet.set_id ? "selected" : ""}`}
                >
                  <input
                    type="radio"
                    name="flashcard-set"
                    value={flashcardSet.set_id}
                    checked={selectedSetId === flashcardSet.set_id}
                    onChange={() => setSelectedSetId(flashcardSet.set_id)}
                  />
                  <div>
                    <p className="set-name">{flashcardSet.name}</p>
                    <p className="set-count">{flashcardSet.count} cards</p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}