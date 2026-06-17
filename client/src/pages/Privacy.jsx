import { Helmet } from 'react-helmet-async'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import './Legal.css'

export default function Privacy() {
  return (
    <div className="legal-page">
      <Helmet>
        <title>Privacy Policy | Ayura AI</title>
      </Helmet>

      <Link to="/" className="legal-back">
        <ArrowLeft size={16} /> Back to Home
      </Link>

      <div className="legal-header">
        <h1>Privacy Policy</h1>
        <p>Last Updated: {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</p>
      </div>

      <div className="legal-content">
        <p>
          At Ayura AI, we take your privacy and the security of your health data extremely seriously. This Privacy Policy explains how we collect, use, and protect your information.
        </p>

        <h2>1. Information We Collect</h2>
        <ul>
          <li><strong>Account Information:</strong> Name, email address, phone number, and authentication data (such as Google or GitHub profile info).</li>
          <li><strong>Health & Wellness Data:</strong> Information you provide during onboarding, including age, weight, height, gender, dosha quiz responses, medical history, allergies, and fitness goals.</li>
          <li><strong>Usage Data:</strong> AI chat transcripts, generated wellness plans, weekly check-in logs, and feedback submissions.</li>
          <li><strong>Technical Data:</strong> IP addresses, browser types, and device information for security and rate-limiting purposes.</li>
        </ul>

        <h2>2. How We Use Your Information</h2>
        <p>
          We use your data strictly to provide and improve the Ayura AI service:
        </p>
        <ul>
          <li>To generate highly personalized Ayurvedic wellness, diet, and fitness plans.</li>
          <li>To customize the AI chat assistant's responses to your specific health context.</li>
          <li>To monitor and improve the accuracy of our AI models through user feedback.</li>
          <li>To secure your account and prevent abuse.</li>
        </ul>

        <h2>3. Data Sharing and Third Parties</h2>
        <p>
          <strong>We do not sell your personal or health data to data brokers or advertisers.</strong>
        </p>
        <p>
          We share your data only with essential third-party service providers required to operate the platform:
        </p>
        <ul>
          <li><strong>AI Providers:</strong> We send anonymized context to Microsoft Azure OpenAI and Google Gemini to generate plans. We do not use your data to train their foundational models.</li>
          <li><strong>Cloud Infrastructure:</strong> Your data is stored securely in MongoDB databases hosted on reputable cloud infrastructure.</li>
        </ul>

        <h2>4. Data Security</h2>
        <p>
          We implement industry-standard security measures, including HTTPS encryption, secure cookies, and password hashing, to protect your personal information from unauthorized access or disclosure.
        </p>

        <h2>5. Your Rights</h2>
        <p>
          You have the right to access, update, or delete your personal information. You can permanently delete your account and all associated health data directly from the Settings page in the Ayura AI dashboard.
        </p>

        <h2>6. Changes to This Policy</h2>
        <p>
          We may update our Privacy Policy from time to time. We will notify you of any significant changes by posting the new Privacy Policy on this page and updating the "Last Updated" date.
        </p>
      </div>
    </div>
  )
}
