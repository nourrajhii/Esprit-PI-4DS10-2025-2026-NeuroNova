import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen relative">
      {/* Full-bleed real-estate background */}
      <div
        className="fixed inset-0 -z-10"
        style={{
          backgroundImage: `
            linear-gradient(135deg, rgba(2,6,23,0.97) 0%, rgba(15,23,42,0.95) 40%, rgba(30,27,75,0.93) 100%),
            url('https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1920&auto=format&fit=crop&q=60')
          `,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundAttachment: 'fixed',
        }}
      />
      {/* Subtle grid overlay */}
      <div
        className="fixed inset-0 -z-10 opacity-[0.03]"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.4) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />
      <Navbar />
      <main className="flex-1 w-full">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-8">
          <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl shadow-black/20 p-6 min-h-[70vh]">
            {children}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}
