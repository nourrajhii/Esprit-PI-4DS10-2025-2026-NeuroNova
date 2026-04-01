import { Link } from 'react-router-dom'

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="site-footer__brand">
          <span className="site-footer__name">REAL</span>
          <span className="site-footer__tag">property intelligence</span>
        </div>
        <nav className="site-footer__nav" aria-label="Footer">
          <Link to="/browse">Explore</Link>
          <Link to="/map">Map</Link>
          <Link to="/contact">Contact</Link>
        </nav>
        <p className="site-footer__copy">
          Demo UI for investors — replace with your legal links and company details.
        </p>
      </div>
    </footer>
  )
}
