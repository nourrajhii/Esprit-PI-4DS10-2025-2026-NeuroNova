import Link from 'next/link'
import { Building2, Facebook, Instagram, Linkedin, Twitter } from 'lucide-react'

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <div className="site-footer" style={{ fontFamily: "'Work Sans', sans-serif" }}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

          {/* Col 1 — Contact */}
          <div className="widget">
            <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Building2 style={{ width: 18, height: 18, color: '#00204a' }} />
              <span style={{ fontWeight: 700, color: '#00204a', fontSize: 15, letterSpacing: '0.05em' }}>EstateMind</span>
            </Link>
            <h3>Contact</h3>
            <address style={{ fontStyle: 'normal', marginBottom: 12, fontSize: 13, lineHeight: 1.6 }}>
              Tunis, Tunisie
            </address>
            <ul className="list-unstyled links">
              <li>
                <a href="tel:+21653192623">+216 53 192 623</a>
              </li>
              <li>
                <a href="mailto:contact@estatemind.tn">contact@estatemind.tn</a>
              </li>
            </ul>
          </div>

          {/* Col 2 — Navigation */}
          <div className="widget">
            <h3>Navigation</h3>
            <div style={{ display: 'flex', gap: 24 }}>
              <ul className="list-unstyled links">
                {[
                  { label: 'Accueil',    href: '/' },
                  { label: 'Rechercher', href: '/search' },
                  { label: 'Marché',     href: '/forecast' },
                  { label: 'Agents IA',  href: '/predict' },
                  { label: 'Villa 3D',   href: '/villa3d' },
                  { label: 'Comparer',   href: '/compare' },
                ].map(({ label, href }) => (
                  <li key={label}><Link href={href}>{label}</Link></li>
                ))}
              </ul>
              <ul className="list-unstyled links">
                {[
                  { label: 'Devis',       href: '/devis' },
                  { label: 'Juridique',   href: '/legal' },
                  { label: 'Lifestyle',   href: '/lifestyle' },
                  { label: 'Conseiller',  href: '/advisor' },
                  { label: 'Abonnement',  href: '/subscription' },
                  { label: 'Connexion',   href: '/auth/login' },
                ].map(({ label, href }) => (
                  <li key={label}><Link href={href}>{label}</Link></li>
                ))}
              </ul>
            </div>
          </div>

          {/* Col 3 — Liens utiles + Social */}
          <div className="widget">
            <h3>Liens utiles</h3>
            <ul className="list-unstyled links">
              {[
                { label: 'À propos',                        href: '#' },
                { label: 'Devenir Investisseur',            href: '/subscription' },
                { label: 'Publier une annonce',             href: '/dashboard/new' },
                { label: 'Mentions légales',                href: '#' },
                { label: 'Politique de confidentialité',    href: '#' },
                { label: 'CGU',                             href: '#' },
              ].map(({ label, href }) => (
                <li key={label}><Link href={href}>{label}</Link></li>
              ))}
            </ul>

            {/* Social icons — using lucide icons styled as template circles */}
            <ul className="list-unstyled social" style={{ marginTop: 16 }}>
              {[
                { icon: Facebook,  href: '#', label: 'Facebook' },
                { icon: Instagram, href: '#', label: 'Instagram' },
                { icon: Linkedin,  href: '#', label: 'LinkedIn' },
                { icon: Twitter,   href: '#', label: 'Twitter' },
              ].map(({ icon: Icon, href, label }) => (
                <li key={label} style={{ display: 'inline-block', marginRight: 6 }}>
                  <a href={href} aria-label={label} className="footer-social-icon"
                    style={{
                      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      width: 38, height: 38, borderRadius: '40%',
                      background: '#ccc', color: '#fff', textDecoration: 'none',
                    }}
                  >
                    <Icon style={{ width: 16, height: 16 }} />
                  </a>
                </li>
              ))}
            </ul>
          </div>

        </div>

        {/* Bottom bar */}
        <div style={{ borderTop: '1px solid #ddd', marginTop: 40, paddingTop: 24, textAlign: 'center', fontSize: 12, color: '#aaa' }}>
          <p>
            &copy; {year} EstateMind. Tous droits réservés. &mdash;{' '}
            Plateforme immobilière intelligente de Tunisie
          </p>
        </div>
      </div>
    </div>
  )
}
