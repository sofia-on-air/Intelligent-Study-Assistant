import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import './App.css';
import { useState, useEffect } from 'react';
import Quiz from './Quiz';
import Flashcards from './Flashcards';

function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const handleLogin = async (e) => {
    e.preventDefault();

    const loginData = {
      email: email,
      password_hash: password
    };
    try {
      const response = await fetch('http://localhost:8080/user/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginData),
      });

      const result = await response.json();

      if (response.ok && result.status !== "error") {
        localStorage.setItem('userId', result.user_id); 
        alert("Logged in!");
        navigate('/main'); 
      } else if (result.message === "Invalid email or password") {
        const goToSignup = window.confirm(
            "There is no such user or wrong password. Would you like to sign up instead?"
        );
        if (goToSignup) {
            navigate('/signup');
        }
    } else {
        alert("Something went wrong. Try again:(");
    }
    } catch (error) {
      console.error("Error connecting to backend:", error);
    }
  };

  return (
    <div className='login-page'>
      <h1 className='login-instruction'> To start using AI assistant using your account, please enter your email and password</h1>
      <form className='login-form' onSubmit={handleLogin}>
      <label className='login-labels'>Enter email:
          <input 
            className="login-input" 
            type="email" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
          />
        </label> 
        <label className='login-labels'> Enter your password
        <input 
            className="login-input" 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
          />
        </label>
        <button className="btn-auth" type="submit">enter account yeyy!</button>
      </form>
    </div>
  );
}

function SignUpPage() {

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    const userData = {
      email: email,
      password_hash: password
    };
    try {
      const response = await fetch('http://localhost:8080/user/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      const result = await response.json();
      if (response.ok && result.status === "success") {
          alert("Account created! Now you can log in.");
          navigate('/');
      } else {
          alert(result.message || "Something went wrong...");
      }
    } catch (error) {
      console.error("Error connecting to backend:", error);
    }
  };
    return (
      <div className='signup-page'>
        <h1 className='signup-instruction'>To start using AI assistant create account by filling the form below:</h1>
        <form className='signup-form' onSubmit={handleSubmit}>
          <label>Email:
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label> 
          <label>Password:
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <button className="btn-auth" type="submit">Create account!</button>
        </form>
      </div>
    );
}

function EnterPage(){
  const navigate = useNavigate();
  return(
      <div className="welcome-page">
      <h1 className="welcome-title">
        Welcome to the friendly AI assistant for students!
      </h1>
      
      <div className="buttons">
        <div className="auth-signup">
          <p>new here?</p>
          <button className="btn-auth" onClick={() => navigate('/signup')}>Sign up!</button>
        </div>
        
        <div className="auth-login">
          <p>already used before?</p>
          <button className="btn-auth" onClick={() => navigate('/login')}>Log in!</button>
        </div>
      </div>
    </div>   
  );
}

function HomePage(){

  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const userId = localStorage.getItem('userId');
  const navigate = useNavigate();

  const handleFileUpload = async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.txt";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const validExtensions = [".pdf", ".txt"];
      const fileExtension = "." + file.name.split(".").pop().toLowerCase();
      if (!validExtensions.includes(fileExtension)) {
        alert("Oops... it seems that you tried to submit an incorrectly formatted file. You can only submit .pdf and .txt! :)");
        return;
      }
      setLoading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(
          `http://localhost:8080/upload-file?user_id=${userId}`,
          { method: "POST", body: formData }
        );
        const data = await response.json();
        if (data.status === "success") {
          alert(`Success! ${data.message}`);
        } else {
          alert("Upload failed: " + data.message);
        }
      } catch (error) {
        alert("Error connecting to backend.");
      } finally {
        setLoading(false);
      }
    };
    input.click();
  };

  const handleGoogleDriveUpload = async () => {
    const fileId = prompt("Please enter Google Drive File ID:");
    const fileName = prompt("Enter file name (e.g. 'my_notes.pdf'):");
    
    if (!fileId || !fileName) return;

    const validExtensions = [".pdf", ".txt"];
    const fileExtension = "." + fileName.split(".").pop().toLowerCase();
    if (!validExtensions.includes(fileExtension)) {
      alert("Oops... it seems that you tried to submit an incorrectly formatted file. You can only submit .pdf and .txt! :)");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8080/upload-drive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: parseInt(userId),
          file_id: fileId,
          file_name: fileName
        })
      });

      const data = await response.json();

      if (response.ok) {
        alert(`Success! ${data.message}`);
      } else {
        alert("Upload failed: " + (data.message || "Unknown error"));
      }
    } catch (error) {
      console.error("Drive upload error:", error);
      alert("Error connecting to backend.");
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async () => {
    if (!query) return;
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8080/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: query,
          user_id: parseInt(userId)
        })
      });
      const data = await response.json();
      setAnswer(data.answer);
    } catch (error) {
      console.error("AI error:", error);
      setAnswer("Error connecting to AI:(");
    } finally {
      setLoading(false);
    }
  };

  const handleGithubConnect = async () => {
    const token = prompt("Please enter your GitHub Personal Access Token:");
    if (!token) return;

    try {
      const response = await fetch('http://localhost:8080/link-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: parseInt(userId),
          access_token: token
        })
      });

      if (response.ok) {
        alert("GitHub connected successfully!");
      } else {
        alert("Failed to link GitHub. Check backend.");
      }
    } catch (error) {
      console.error("Link error:", error);
    }
  };

  const handleGithubUpload = async () => {
    const repo = prompt("Enter repo name (e.g. 'username/repo'):");
    const path = prompt("Enter file path (e.g. 'main.py'):");
    
    if (!repo || !path) return;

    const validExtensions = [".pdf", ".txt"];
    const fileExtension = "." + path.split(".").pop().toLowerCase();
    if (!validExtensions.includes(fileExtension)) {
      alert("Oops... it seems that you tried to submit an incorrectly formatted file. You can only submit .pdf and .txt! :)");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://localhost:8080/upload-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: parseInt(userId),
          repo_name: repo,
          file_path: path
        })
      });

      const data = await response.json();
      if (response.ok && data.status !== "error") {
        alert(`Success! File uploaded successfully.`);
      } else {
          alert(data.message || "Upload failed. Please connect to GitHub first!");
      }
    } catch (error) {
      console.error("Upload error:( :", error);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLink = async () => {
    try {
      const response = await fetch(`http://localhost:8080/link-google?user_id=${userId}`);
      const data = await response.json();
      
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (error) {
      console.error("Link error:", error);
      alert("Could not get Google Auth URL");
    }
  };

  return (
    <div className='home-page'>
      <nav className="home-navigation">
        <button onClick={() => navigate('/main')}>Home</button>
        <button onClick={() => navigate('/quizzes')}>Quizzes</button>
        <button onClick={() => navigate('/flashcards')}>Flashcards</button>
        <button onClick={() => navigate('/')}>Logout</button>
      </nav>

      <div className="home-page-content">
        <div className="ai-section">
          <textarea 
            placeholder="Ask your question here..." 
            value={query} 
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn-auth" onClick={handleChat} disabled={loading}>
            {loading ? "Thinking..." : "Ask AI"}
          </button>
          
          <div className="response-window">
            <h3>Response:</h3>
            <p>{answer}</p>
          </div>
        </div>

        <div className="tools-section">
          <button className="tool-btn" onClick={handleGoogleDriveUpload}>connect to GoogleDrive</button>
          <button className="tool-btn" onClick={handleGoogleLink}>authorise to GoogleDrive</button>
          <button className="tool-btn" onClick={handleFileUpload}>upload local file</button>
          <button className="tool-btn" onClick={handleGithubConnect}>connect to GitHub</button>
          <button className="tool-btn" onClick={handleGithubUpload}>add document from GitHub</button>
          <p style={{fontSize: '12px'}}>Logged in as User ID: {userId}</p>
        </div>
      </div>
    </div>
  );
}

function GoogleCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const handleGoogleCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const state = urlParams.get('state');
      const userId = localStorage.getItem('userId');

      if (!code || !userId) return;

      try {
        const response = await fetch('http://localhost:8080/google-callback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code: code,
            user_id: parseInt(userId),
            state: state
          })
        });

        const data = await response.json();

        if (data.status === 'success') {
          alert("Google Drive linked successfully!");
        } else {
          alert("Error: " + data.message);
        }

      } catch (error) {
        console.error("Callback error:", error);
      }

      navigate('/main');
    };

    handleGoogleCallback();
  }, [navigate]);

  return (
    <div className="google-callback-page">
      Connecting to Google... Please wait.
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<EnterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/main" element={<HomePage />} />
        <Route path="/quizzes" element={<Quiz />} />
        <Route path="/flashcards" element={<Flashcards />} />
        <Route path="/oauth/google/callback" element={<GoogleCallback />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App