import { Helmet } from 'react-helmet-async'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import './Legal.css'

// Bump this by hand whenever the text below changes — and only then. It was
// previously `new Date()`, which made the page claim it had been revised today,
// every day, regardless of whether a word had changed. A policy's stated
// revision date is a factual representation to users and regulators, so it has
// to track real edits.
const LAST_UPDATED = '4 August 2026'

const CONTACT_EMAIL = 'privacy@ayuraai.in'

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
        <p>Last Updated: {LAST_UPDATED}</p>
      </div>

      <div className="legal-content">
        <p>
          Ayura AI processes health and wellness information, which is sensitive personal data. This policy explains what we collect, why, how long we keep it, who it is shared with, and the rights you can exercise over it. It is written to meet our obligations under India&apos;s Digital Personal Data Protection Act, 2023 (&quot;DPDP Act&quot;) and the Information Technology Rules, 2021.
        </p>

        <h2>1. Information We Collect</h2>
        <ul>
          <li><strong>Account Information:</strong> Name, email address, phone number, and authentication data (such as Google or GitHub profile info).</li>
          <li><strong>Health &amp; Wellness Data:</strong> Information you provide during onboarding, including age, weight, height, gender, dosha quiz responses, medical history, current medications, allergies, pregnancy or nursing status, and fitness goals.</li>
          <li><strong>Usage Data:</strong> AI chat transcripts, generated wellness plans, weekly check-in logs, adverse-reaction reports, community posts, and feedback submissions.</li>
          <li><strong>Technical Data:</strong> IP addresses, browser types, and device information for security and rate-limiting purposes.</li>
          <li><strong>Product Analytics:</strong> Which pages you visit and which milestones you reach (for example, that a plan was generated). See section 5.</li>
        </ul>

        <h2>2. How We Use Your Information</h2>
        <p>We use your data strictly to provide and improve the Ayura AI service:</p>
        <ul>
          <li>To generate personalised Ayurvedic wellness, diet, and fitness plans.</li>
          <li>To customise the AI chat assistant&apos;s responses to your specific health context.</li>
          <li>To screen for contraindications — for example, excluding therapies unsuitable during pregnancy, or flagging herb–medicine interactions.</li>
          <li>To monitor and improve the accuracy of our recommendations through your feedback.</li>
          <li>To secure your account, prevent abuse, and diagnose faults.</li>
        </ul>

        <h2>3. Legal Basis and Consent</h2>
        <p>
          We process your health data on the basis of the consent you give when you create an account and complete onboarding. You may withdraw that consent at any time by deleting your account (section 7). Withdrawing consent does not affect processing already carried out, and it will end your ability to use the personalised features of the Service.
        </p>

        <h2>4. Data Sharing and Third Parties</h2>
        <p>
          <strong>We do not sell your personal or health data to data brokers or advertisers.</strong>
        </p>
        <p>We share data only with service providers required to operate the platform:</p>
        <ul>
          <li><strong>AI Providers:</strong> Microsoft Azure OpenAI and Google Gemini receive the health context needed to generate your plan and answer your questions. Your data is not used to train their foundational models.</li>
          <li><strong>Cloud Infrastructure:</strong> Your data is stored in MongoDB Atlas and on our hosting provider&apos;s servers.</li>
          <li><strong>Email Delivery:</strong> Our email provider processes your address to send verification, password-reset, and notification messages.</li>
          <li><strong>Error Monitoring:</strong> If enabled, Sentry receives technical diagnostics when something breaks. Text content is masked before transmission.</li>
          <li><strong>Product Analytics:</strong> If enabled, PostHog receives the events described in section 5.</li>
        </ul>
        <p>
          Some of these providers process data on servers outside India. We may also disclose data where compelled by law or where necessary to protect someone&apos;s life or safety.
        </p>

        <h2>5. Cookies and Analytics</h2>
        <p>
          We use strictly necessary cookies to keep you signed in. Authentication tokens are stored in HTTP-only cookies (<code>ayura_access</code> and <code>ayura_refresh</code>), which JavaScript cannot read. We do not use advertising or cross-site tracking cookies.
        </p>
        <p>
          Our analytics are deliberately constrained. We record which pages are visited and which milestones are reached — such as completing onboarding or generating a plan — together with counts, such as how many conditions were selected. We do <strong>not</strong> send your dosha results, conditions, symptoms, medicines, chat messages, or plan contents to any analytics provider, we do not record your screen, and we honour your browser&apos;s &quot;Do Not Track&quot; setting.
        </p>

        <h2>6. Data Retention</h2>
        <p>
          We keep your account and health data for as long as your account is active. If you delete your account, your personal and health data is erased from our live systems within 30 days, except where we are required to retain records by law. Encrypted backups are cycled out within 90 days. Anonymised, aggregated statistics that cannot identify you may be kept indefinitely.
        </p>

        <h2>7. Your Rights</h2>
        <p>Under the DPDP Act you have the right to:</p>
        <ul>
          <li><strong>Access</strong> the personal data we hold about you, and obtain a copy. Settings → Account Actions → Export Data provides this as a downloadable file.</li>
          <li><strong>Correct or complete</strong> inaccurate data, from your Profile and Settings pages.</li>
          <li><strong>Erase</strong> your data by deleting your account from Settings. Deletion cascades to your plans, timeline, reminders, check-ins, and community contributions.</li>
          <li><strong>Withdraw consent</strong> to processing, as described in section 3.</li>
          <li><strong>Nominate</strong> another individual to exercise these rights on your behalf in the event of death or incapacity. Contact us to record a nomination.</li>
          <li><strong>Complain</strong> to the Data Protection Board of India if you believe your rights have been infringed.</li>
        </ul>

        <h2>8. Data Security</h2>
        <p>
          We use HTTPS throughout, hash passwords with a modern algorithm, store session tokens in HTTP-only cookies, rate-limit sensitive endpoints, and validate uploaded files. No system is perfectly secure, but we work to protect your information against unauthorised access, alteration, and disclosure.
        </p>

        <h2>9. Breach Notification</h2>
        <p>
          If a personal data breach occurs, we will notify you and the Data Protection Board of India without undue delay, describing the nature of the breach, its likely consequences, and the steps we are taking in response.
        </p>

        <h2>10. Children</h2>
        <p>
          Ayura AI is not intended for children. You must be at least 18 years old to create an account. We do not knowingly collect data from children; if we learn that we have, we will delete it. If you believe a child has provided us data, please contact us.
        </p>

        <h2>11. Changes to This Policy</h2>
        <p>
          We may update this policy from time to time. Significant changes will be notified to you in the app or by email, and the &quot;Last Updated&quot; date above will be revised. Continued use after a change constitutes acceptance of the updated policy.
        </p>

        <div className="legal-important">
          <strong>GRIEVANCE OFFICER &amp; CONTACT</strong>
          <p style={{ marginBottom: 0, color: 'inherit' }}>
            In accordance with the Information Technology Act, 2000 and the rules made thereunder, and the DPDP Act, 2023, questions, data-rights requests, and grievances may be directed to our Grievance Officer and Data Protection contact at{' '}
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. We acknowledge grievances within 24 hours and aim to resolve them within 15 days.
          </p>
        </div>
      </div>
    </div>
  )
}
