import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./App.css";
import "./Quiz.css";

export default function Quiz() {
  const navigate = useNavigate();
  const userId = localStorage.getItem("userId");

  const [tab, setTab] = useState("my");
  const [myQuizzes, setMyQuizzes] = useState([]);
  const [loadingQuizzes, setLoadingQuizzes] = useState(false);
  const [topic, setTopic] = useState("");
  const [numQ, setNumQ] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [quizId, setQuizId] = useState(null);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);
  const [answers, setAnswers] = useState([]);

  useEffect(() => {
    if (tab === "my") fetchMyQuizzes();
  }, [tab]);

  const fetchMyQuizzes = async () => {
    setLoadingQuizzes(true);
    try {
      const res = await fetch(`http://localhost:8080/my-quizzes/${userId}`);
      const data = await res.json();
      setMyQuizzes(data.quizzes || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingQuizzes(false);
    }
  };

  const handleGenerate = async () => {
    if (!topic) return;
    setGenerating(true);
    try {
      const res = await fetch("http://localhost:8080/generate-quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, num_questions: numQ, user_id: parseInt(userId) }),
      });
      const data = await res.json();
      if (data.quiz && data.quiz.length > 0 && !data.quiz[0].error){
        startQuiz(data.quiz, data.quiz_id);
      } else if (data.error === "Could not generate relevant quiz") {
        alert("This amount of questions is impossible to do! Pick a less amount of questions.");
      } else {
        alert("Oops! I don't have information about this topic in your documents. Please upload relevant materials first!");
      }
    } catch (e) {
      console.error(e);
      alert("Error connecting to backend.");
    } finally {
      setGenerating(false);
    }
  };

  const startQuiz = (questions, id = null) => {
    setActiveQuiz(questions);
    setQuizId(id);
    setCurrent(0);
    setSelected(null);
    setConfirmed(false);
    setScore(0);
    setFinished(false);
    setAnswers([]);
  };

  const handleConfirm = () => {
    if (selected === null) return;
    const currentQuestion = activeQuiz[current];
    const isCorrect = selected === currentQuestion.correct_answer;
    setConfirmed(true);
    if (isCorrect) setScore(score + 1);
    setAnswers((prev) => [
      ...prev,
      {
        question: currentQuestion.question,
        chosen: selected,
        correct: currentQuestion.correct_answer,
        explanation: currentQuestion.explanation || "",
        isCorrect,
      },
    ]);
  };// use of ai

  const handleNext = () => {
    const isLastQuestion = current + 1 >= activeQuiz.length;
    if (isLastQuestion) {
      if (quizId) {
        fetch("http://localhost:8080/update-quiz-score", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ quiz_id: quizId, score: score }),
        });
      }
      setFinished(true);
    } else {
      setCurrent(current + 1);
      setSelected(null);
      setConfirmed(false);
    }
  };

  const resetQuiz = () => {
    setActiveQuiz(null);
    setFinished(false);
    setTab("my");
    fetchMyQuizzes();
  };

  const getOptionClassName = (opt) => {
    if (!confirmed) {
      return selected === opt ? "selected" : "";
    }
    const currentQuestion = activeQuiz[current];
    if (opt === currentQuestion.correct_answer) return "correct";
    if (opt === selected) return "wrong";
    return "";
  };// use of ai

  const NavBar = () => (
    <nav className="home-navigation">
      <button onClick={() => navigate("/main")}>Home</button>
      <button onClick={() => navigate("/quizzes")}>Quizzes</button>
      <button onClick={() => navigate("/flashcards")}>Flashcards</button>
      <button onClick={() => navigate("/")}>Logout</button>
    </nav>
  );

  if (activeQuiz && !finished) {
    const currentQuestion = activeQuiz[current];
    const progress = (current / activeQuiz.length) * 100;
    return (
      <div className="home-page">
        <NavBar />
        <div className="active-quiz-container">

          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>

          <p className="quiz-counter">{current + 1} / {activeQuiz.length}</p>

          <h2 className="quiz-question">{currentQuestion.question}</h2>

          <div className="quiz-options">
            {currentQuestion.options.map((opt, i) => (
              <button
                key={i}
                className={`option-btn ${getOptionClassName(opt)}`}
                onClick={() => !confirmed && setSelected(opt)}
                disabled={confirmed}
              >
                {opt}
              </button>
            ))}
          </div>

          {confirmed && currentQuestion.explanation && (
            <div className="quiz-explanation">
              <strong>Explanation:</strong> {currentQuestion.explanation}
            </div>
          )}

          {!confirmed ? (
            <button
              className={`btn-auth ${!selected ? "btn-disabled" : ""}`}
              onClick={handleConfirm}
              disabled={!selected}
            >
              Confirm answer
            </button>
          ) : (
            <button className="btn-auth" onClick={handleNext}>
              {current + 1 >= activeQuiz.length ? "See results" : "Next question"}
            </button>
          )}

        </div>
      </div>
    );
  }

  if (finished) {
    const pct = Math.round((score / activeQuiz.length) * 100);
    return (
      <div className="home-page">
        <NavBar />
        <div className="active-quiz-container">
          <h2 className="welcome-title">Quiz complete!</h2>

          <div className="score-circle">
            <span className="score-big">{pct}%</span>
            <span className="score-small">{score}/{activeQuiz.length} correct</span>
          </div>

          <div className="results-list">
            {answers.map((answer, i) => (
              <div
                key={i}
                className={`result-item ${answer.isCorrect ? "result-correct" : "result-wrong"}`}
              >
                <p className="result-question">{i + 1}. {answer.question}</p>
                <p className={answer.isCorrect ? "result-text-correct" : "result-text-wrong"}>
                  Your answer: {answer.chosen}
                </p>
                {!answer.isCorrect && (
                  <p className="result-text-correct">Correct: {answer.correct}</p>
                )}
                {answer.explanation && (
                  <p className="result-explanation">{answer.explanation}</p>
                )}
              </div>
            ))}
          </div>

          <button className="btn-auth" onClick={resetQuiz}>Back to quizzes</button>
        </div>
      </div>
    );
  }

  return (
    <div className="home-page">
      <NavBar />
      <div className="quiz-container">
        <h1 className="welcome-title">Quizzes</h1>

        <div className="quiz-tabs">
          <button
            className={`quiz-tab ${tab === "my" ? "active" : ""}`}
            onClick={() => setTab("my")}
          >
            My quizzes
          </button>
          <button
            className={`quiz-tab ${tab === "generate" ? "active" : ""}`}
            onClick={() => setTab("generate")}
          >
            Generate new
          </button>
        </div>

        {tab === "my" && (
          <div className="quiz-tab-content">
            {loadingQuizzes ? (
              <p className="quiz-loading">Loading...</p>
            ) : myQuizzes.length === 0 ? (
              <p className="quiz-empty">No quizzes yet. Generate your first one!</p>
            ) : (
              myQuizzes.map((quizz) => (
                <div key={quizz.quiz_id} className="quiz-card">
                  <div>
                    <p className="quiz-card-title">{quizz.topic || `Quiz #${quizz.quiz_id}`}</p>
                    <p className="quiz-card-meta">
                      {quizz.quiz_data ? quizz.quiz_data.length : 0} questions
                    </p>
                  </div>
                  <button className="take-btn" onClick={() => startQuiz(quizz.quiz_data, quizz.quiz_id)}>
                    Take quiz
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "generate" && (
          <div className="quiz-tab-content">
            <label className="quiz-label">Topic</label>
            <input
              className="quiz-input"
              type="text"
              placeholder="e.g. Machine Learning, French Revolution..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
            <label className="quiz-label">Number of questions</label>
            <select
              className="quiz-input"
              value={numQ}
              onChange={(e) => setNumQ(parseInt(e.target.value))}
            >
              <option value={3}>3 questions</option>
              <option value={5}>5 questions</option>
              <option value={7}>7 questions</option>
            </select>
            <button
              className={`quiz-main-btn ${!topic ? "btn-disabled" : ""}`}
              onClick={handleGenerate}
              disabled={generating || !topic}
            >
              {generating ? "Generating..." : "Generate quiz"}
            </button>
          </div>
        )}

      </div>
    </div>
  );
}