import { useState } from 'react'
import { Mail, MapPinned, Phone } from 'lucide-react'

export function Contact() {
  const [sent, setSent] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSent(true)
  }

  return (
    <div className="page-contact">
      <header className="page-head">
        <h1>Contact</h1>
        <p>Reach the team — this form is a demo; connect it to your CRM or email API.</p>
      </header>

      <div className="contact-grid">
        <section className="contact-card">
          <h2>Offices</h2>
          <ul className="contact-facts">
            <li>
              <MapPinned size={18} aria-hidden />
              <span>Paris · Lyon · Marseille (demo)</span>
            </li>
            <li>
              <Phone size={18} aria-hidden />
              <span>+33 1 23 45 67 89</span>
            </li>
            <li>
              <Mail size={18} aria-hidden />
              <span>hello@real-estate.demo</span>
            </li>
          </ul>
        </section>

        <section className="contact-card">
          <h2>Message</h2>
          {sent ? (
            <p className="success-inline">
              Thanks — in production this would send email or create a lead ticket.
            </p>
          ) : (
            <form className="contact-form" onSubmit={handleSubmit}>
              <label className="field">
                <span>Name</span>
                <input required placeholder="Your name" />
              </label>
              <label className="field">
                <span>Email</span>
                <input type="email" required placeholder="you@company.com" />
              </label>
              <label className="field">
                <span>Message</span>
                <textarea rows={4} required placeholder="Project, budget, timeline…" />
              </label>
              <button type="submit" className="btn btn--primary">
                Send
              </button>
            </form>
          )}
        </section>
      </div>
    </div>
  )
}
