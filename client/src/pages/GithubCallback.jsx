import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../providers/AuthContext';
import LoadingScreen from '../components/LoadingScreen';

function GithubCallback() {
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { loginWithGithub } = useAuth();

  useEffect(() => {
    const processGithubAuth = async () => {
      const searchParams = new URLSearchParams(location.search);
      const code = searchParams.get('code');
      const state = searchParams.get('state');

      if (!code) {
        setError("No authorization code found in URL.");
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      try {
        await loginWithGithub(code, state);
        navigate('/dashboard');
      } catch (err) {
        console.error("GitHub Auth Error:", err);
        setError(err.response?.data?.detail || "Failed to authenticate with GitHub. Please try again.");
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    processGithubAuth();
  }, [location, navigate, loginWithGithub]);

  if (error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <h2>Authentication Failed</h2>
        <p style={{ color: 'red' }}>{error}</p>
        <p>Redirecting back to login...</p>
      </div>
    );
  }

  return <LoadingScreen message="Connecting your GitHub account..." />;
}

export default GithubCallback;
