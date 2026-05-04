require('dotenv').config({ path: require('path').join(__dirname, '../.env') })
const mongoose = require('mongoose')
const { seedAdmin } = require('./seedAdmin')
const Listing = require('../src/models/Listing')
const User    = require('../src/models/User')

const IMGS = {
  apt: [
    'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800',
    'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800',
    'https://images.unsplash.com/photo-1554995207-c18c203602cb?w=800',
    'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800',
    'https://images.unsplash.com/photo-1565182999561-18d7dc61c393?w=800',
    'https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=800',
    'https://images.unsplash.com/photo-1560185893-a55cbc8c57e8?w=800',
    'https://images.unsplash.com/photo-1484154218962-a197022b5858?w=800',
  ],
  villa: [
    'https://images.unsplash.com/photo-1613977257363-707ba9348227?w=800',
    'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800',
    'https://images.unsplash.com/photo-1575517111839-3a3843ee7f5d?w=800',
    'https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800',
    'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800',
    'https://images.unsplash.com/photo-1600607688969-a5bfcd646154?w=800',
    'https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=800',
    'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800',
  ],
  land: [
    'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800',
    'https://images.unsplash.com/photo-1628624747186-a941c476b7ef?w=800',
  ],
  commercial: [
    'https://images.unsplash.com/photo-1497366754035-f200968a6e72?w=800',
    'https://images.unsplash.com/photo-1497366216548-37526070297c?w=800',
  ],
}

function pick(arr, n = 1) { return arr.slice(0, n).concat(arr.slice(1, n + 1)) }

const LISTINGS = [
  // ── TUNIS ────────────────────────────────────────────────────────────────
  { title: 'Appartement S+2 moderne — Lac 2', type: 'vente',    price: 320000, surface: 110, rooms: 3, city: 'Tunis', address: 'Lac 2, Tunis',              images: pick(IMGS.apt, 2),        description: 'Appartement lumineux avec vue lac, cuisine équipée, parking sous-sol.' },
  { title: 'Penthouse panoramique — Gammarth', type: 'vente',   price: 1200000,surface: 280, rooms: 5, city: 'Tunis', address: 'Gammarth, Tunis',           images: pick(IMGS.villa, 2),      description: 'Penthouse exceptionnel, terrasse 80m², vue mer et montagne 360°.' },
  { title: 'Duplex S+3 — Menzah 5',           type: 'vente',   price: 480000, surface: 185, rooms: 4, city: 'Tunis', address: 'Menzah 5, Tunis',           images: pick(IMGS.apt, 2),        description: 'Duplex spacieux résidence sécurisée, terrasse 40m², 2 SDB.' },
  { title: 'Local commercial — La Marsa',     type: 'vente',   price: 290000, surface: 80,  rooms: 2, city: 'Tunis', address: 'La Marsa, Tunis',           images: pick(IMGS.commercial, 2), description: 'Local RDC vitrine rue principale, idéal commerce ou bureau.' },
  { title: 'Appartement S+3 — Carthage',      type: 'location',price: 2500,   surface: 160, rooms: 3, city: 'Tunis', address: 'Carthage Présidence, Tunis', images: pick(IMGS.villa, 2),      description: 'Haut standing vue mer, finitions premium, gardien 24h, piscine.' },
  { title: 'Studio meublé — Montplaisir',     type: 'location',price: 700,    surface: 40,  rooms: 1, city: 'Tunis', address: 'Montplaisir, Tunis',         images: pick(IMGS.apt),           description: 'Studio entièrement meublé, proche métro léger.' },
  { title: 'Appartement neuf S+2 — Manouba', type: 'vente',   price: 215000, surface: 105, rooms: 2, city: 'Manouba',address: 'Manouba Centre',            images: pick(IMGS.apt, 2),        description: 'Livraison immédiate, résidence neuve, parking et cave inclus.' },
  { title: 'Villa R+1 — La Soukra',          type: 'vente',   price: 720000, surface: 300, rooms: 5, city: 'Ariana', address: 'La Soukra, Ariana',         images: pick(IMGS.villa, 2),      description: 'Villa avec jardin 400m², piscine, garage, quartier résidentiel.' },
  { title: 'Appartement S+1 — Ariana Ville', type: 'location',price: 700,    surface: 65,  rooms: 1, city: 'Ariana', address: 'Ariana Ville',               images: pick(IMGS.apt),           description: 'Rénové, cuisine américaine, balcon, parking résidentiel.' },
  { title: 'Appartement S+2 — Ben Arous',    type: 'vente',   price: 185000, surface: 95,  rooms: 2, city: 'Ben Arous',address: 'Ben Arous Centre',        images: pick(IMGS.apt),           description: 'Premier achat, bien entretenu, proche toutes commodités.' },

  // ── SOUSSE ────────────────────────────────────────────────────────────────
  { title: 'Studio meublé — Centre Sousse',  type: 'location',price: 650,    surface: 38,  rooms: 1, city: 'Sousse', address: 'Centre Ville, Sousse',      images: pick(IMGS.apt),           description: 'Idéal étudiant, proche université et commerces.' },
  { title: 'Villa avec piscine — Sahloul',   type: 'vente',   price: 680000, surface: 270, rooms: 5, city: 'Sousse', address: 'Sahloul 3, Sousse',          images: pick(IMGS.villa, 2),      description: 'Villa R+1, piscine chauffée, jardin paysagé, alarme.' },
  { title: 'Appartement S+2 — Khézama',      type: 'vente',   price: 260000, surface: 110, rooms: 3, city: 'Sousse', address: 'Khézama Est, Sousse',        images: pick(IMGS.apt, 2),        description: 'Lumineux, 3ème étage avec ascenseur, résidence récente.' },
  { title: 'Local bureau 120m² — Sousse',    type: 'location',price: 1800,   surface: 120, rooms: 4, city: 'Sousse', address: 'Avenue Habib Bourguiba',     images: pick(IMGS.commercial),   description: 'Open-space climatisé, salle de réunion, parking.' },
  { title: 'Villa S+4 bord de mer — Chott',  type: 'vente',   price: 950000, surface: 380, rooms: 6, city: 'Sousse', address: 'Chott Mariem, Sousse',       images: pick(IMGS.villa, 2),      description: 'Accès direct à la plage, terrasse panoramique, cuisine de chef.' },
  { title: 'Appartement S+1 — Sousse Nord',  type: 'location',price: 550,    surface: 60,  rooms: 1, city: 'Sousse', address: 'Sousse Nord',                images: pick(IMGS.apt),           description: 'Calme, lumineux, proche zone touristique.' },

  // ── SFAX ──────────────────────────────────────────────────────────────────
  { title: 'Appartement S+2 — Sfax Centre',  type: 'location',price: 800,    surface: 95,  rooms: 2, city: 'Sfax',   address: 'Centre Ville, Sfax',         images: pick(IMGS.apt),           description: '2ème étage sans ascenseur, calme et lumineux.' },
  { title: 'Villa R+1 — Sfax El Ain',        type: 'vente',   price: 480000, surface: 240, rooms: 4, city: 'Sfax',   address: 'El Ain, Sfax',               images: pick(IMGS.villa, 2),      description: 'Quartier résidentiel calme, finitions soignées, jardin.' },
  { title: 'Local commercial 200m² — Sfax',  type: 'vente',   price: 320000, surface: 200, rooms: 3, city: 'Sfax',   address: 'Avenue du 14 Janvier, Sfax', images: pick(IMGS.commercial, 2), description: 'Emplacement stratégique, forte visibilité, 2 entrées.' },
  { title: 'Appartement neuf S+3 — Sfax',    type: 'vente',   price: 310000, surface: 135, rooms: 3, city: 'Sfax',   address: 'Sfax Ville',                 images: pick(IMGS.apt, 2),        description: 'Résidence récente, ascenseur, parking double.' },
  { title: 'Studio étudiant — Sfax',         type: 'location',price: 400,    surface: 35,  rooms: 1, city: 'Sfax',   address: 'Sfax Médina',                images: pick(IMGS.apt),           description: 'Proche faculté de droit, entièrement rénové.' },

  // ── NABEUL ───────────────────────────────────────────────────────────────
  { title: 'Villa S+3 bord de mer — Nabeul', type: 'vente',   price: 620000, surface: 230, rooms: 4, city: 'Nabeul', address: 'Zone Touristique, Nabeul',   images: pick(IMGS.villa, 2),      description: 'Villa plain-pied, terrasse, jardin, 3 min plage.' },
  { title: 'Appartement S+2 — Hammamet',     type: 'location',price: 900,    surface: 90,  rooms: 2, city: 'Hammamet',address: 'Hammamet Centre',           images: pick(IMGS.apt),           description: 'Résidence touristique, piscine commune, gardien.' },
  { title: 'Villa de luxe — Hammamet Nord',  type: 'vente',   price: 1500000,surface: 500, rooms: 7, city: 'Hammamet',address: 'Hammamet Nord',             images: pick(IMGS.villa, 2),      description: 'Domaine 1000m², piscine olympique, spa, cinéma.' },
  { title: 'Terrain 800m² — Nabeul',         type: 'vente',   price: 180000, surface: 800, rooms: 0, city: 'Nabeul', address: 'Nabeul Sud',                 images: pick(IMGS.land),          description: 'Zone résidentielle, viabilisé, titre foncier net.' },
  { title: 'Appartement S+1 — Kélibia',      type: 'vente',   price: 150000, surface: 70,  rooms: 1, city: 'Nabeul', address: 'Kélibia, Nabeul',            images: pick(IMGS.apt),           description: 'Vue mer, rénové, idéal résidence secondaire.' },

  // ── BIZERTE ──────────────────────────────────────────────────────────────
  { title: 'Villa avec vue mer — Bizerte',   type: 'vente',   price: 540000, surface: 220, rooms: 4, city: 'Bizerte',address: 'Corniche, Bizerte',          images: pick(IMGS.villa, 2),      description: 'Vue panoramique sur le golfe, terrasse, garage.' },
  { title: 'Appartement S+2 — Bizerte',      type: 'location',price: 600,    surface: 85,  rooms: 2, city: 'Bizerte',address: 'Centre Bizerte',             images: pick(IMGS.apt),           description: 'Proche port, 3ème étage, lumineux.' },
  { title: 'Terrain bord de lac — Bizerte',  type: 'vente',   price: 220000, surface: 1200,rooms: 0, city: 'Bizerte',address: 'Lac de Bizerte',             images: pick(IMGS.land),          description: 'Exceptionnel bord de lac, constructible, vue dégagée.' },

  // ── MONASTIR ──────────────────────────────────────────────────────────────
  { title: 'Appartement S+3 — Monastir',     type: 'vente',   price: 285000, surface: 120, rooms: 3, city: 'Monastir',address: 'Centre Monastir',          images: pick(IMGS.apt, 2),        description: 'Proche medina, lumineux, vue partielle sur mer.' },
  { title: 'Villa S+2 — Skanes',             type: 'vente',   price: 450000, surface: 200, rooms: 3, city: 'Monastir',address: 'Skanes, Monastir',          images: pick(IMGS.villa),         description: 'Quartier résidentiel, proche aéroport, jardin.' },
  { title: 'Studio meublé — Monastir',       type: 'location',price: 500,    surface: 40,  rooms: 1, city: 'Monastir',address: 'Monastir Centre',           images: pick(IMGS.apt),           description: 'Entièrement meublé, climatisé, proche plage.' },

  // ── MAHDIA ───────────────────────────────────────────────────────────────
  { title: 'Villa S+3 vue mer — Mahdia',     type: 'vente',   price: 520000, surface: 240, rooms: 4, city: 'Mahdia', address: 'Zone Touristique, Mahdia',   images: pick(IMGS.villa, 2),      description: 'Vue mer exceptionnelle, piscine, jardin tropical.' },
  { title: 'Appartement S+2 — Mahdia',       type: 'vente',   price: 195000, surface: 95,  rooms: 2, city: 'Mahdia', address: 'Mahdia Ville',               images: pick(IMGS.apt),           description: 'Résidence récente, proche médina et plages.' },

  // ── GABÈS / MÉDENINE ─────────────────────────────────────────────────────
  { title: 'Appartement S+3 — Gabès',        type: 'vente',   price: 165000, surface: 115, rooms: 3, city: 'Gabès',  address: 'Gabès Centre',               images: pick(IMGS.apt),           description: 'Proche hôpital régional, bien entretenu.' },
  { title: 'Villa S+2 — Médenine',           type: 'vente',   price: 280000, surface: 175, rooms: 3, city: 'Médenine',address: 'Médenine Ville',            images: pick(IMGS.villa),         description: 'Maison de maître, patio, idéal famille.' },
  { title: 'Terrain constructible — Jerba',  type: 'vente',   price: 350000, surface: 2000,rooms: 0, city: 'Médenine',address: 'Djerba Midoun',             images: pick(IMGS.land),          description: 'Terrain en zone touristique Djerba, bord de route.' },

  // ── KAIROUAN / GAFSA ─────────────────────────────────────────────────────
  { title: 'Villa traditionnelle — Kairouan',type: 'vente',   price: 220000, surface: 200, rooms: 4, city: 'Kairouan',address: 'Kairouan Centre',           images: pick(IMGS.villa),         description: 'Architecture traditionnelle restaurée, patio, puits.' },
  { title: 'Appartement S+2 — Gafsa',        type: 'vente',   price: 140000, surface: 95,  rooms: 2, city: 'Gafsa',  address: 'Gafsa Centre',               images: pick(IMGS.apt),           description: 'Investissement locatif, quartier universitaire.' },

  // ── JENDOUBA / ZAGHOUAN ──────────────────────────────────────────────────
  { title: 'Terrain constructible — Aïn Draham',type:'vente',  price: 120000, surface: 500, rooms: 0, city: 'Jendouba',address: 'Aïn Draham, Jendouba',     images: pick(IMGS.land),          description: 'Zone résidentielle, vue forêt, viabilisé.' },
  { title: 'Ferme avec oliviers — Zaghouan',  type: 'vente',  price: 380000, surface: 5000,rooms: 3, city: 'Zaghouan',address: 'Zaghouan Campagne',         images: pick(IMGS.land),          description: '500 oliviers, maison de gardien, eau de source.' },

  // ── TOZEUR / TATAOUINE ────────────────────────────────────────────────────
  { title: 'Maison traditionnelle — Tozeur', type: 'vente',   price: 180000, surface: 160, rooms: 4, city: 'Tozeur', address: 'Tozeur Médina',              images: pick(IMGS.villa),         description: 'Architecture authentique, patio palmier, idéal gîte.' },
  { title: 'Terrain palmeraie — Tozeur',     type: 'vente',   price: 90000,  surface: 3000,rooms: 0, city: 'Tozeur', address: 'Oasis, Tozeur',              images: pick(IMGS.land),          description: 'Palmeraie 200 palmiers, projet agro-touristique possible.' },

  // ── TUNIS supplémentaires ─────────────────────────────────────────────────
  { title: 'Appartement S+4 — Les Berges du Lac',type:'vente', price: 680000, surface: 220, rooms: 5, city: 'Tunis', address: 'Berges du Lac 1, Tunis',    images: pick(IMGS.apt, 2),        description: 'Standing exceptionnel, terrasse 60m², parking double.' },
  { title: 'Bureau aménagé 180m² — Lac 2',    type: 'location',price: 3500,   surface: 180, rooms: 5, city: 'Tunis', address: 'Lac 2, Tunis',              images: pick(IMGS.commercial, 2), description: 'Plateau bureau haut de gamme, salle de conf, accueil.' },
  { title: 'Appartement S+1 — Menzah 9',      type: 'location',price: 850,    surface: 72,  rooms: 1, city: 'Tunis', address: 'Menzah 9, Tunis',           images: pick(IMGS.apt),           description: 'Idéal jeune couple, rénové, cave, proche commerces.' },
  { title: 'Villa d\'architecte — Sidi Bou Saïd',type:'vente', price: 3500000,surface: 650, rooms: 7, city: 'Tunis', address: 'Sidi Bou Saïd, Tunis',      images: pick(IMGS.villa, 2),      description: 'Vue mer exceptionnelle, piscine à débordement, domaine 1200m².' },
  { title: 'Appartement S+2 — El Aouina',     type: 'vente',   price: 280000, surface: 105, rooms: 3, city: 'Tunis', address: 'El Aouina, Tunis',           images: pick(IMGS.apt, 2),        description: 'Proche aéroport, résidence récente, vue dégagée.' },
  { title: 'Studio — Bab Souika',             type: 'location',price: 450,    surface: 35,  rooms: 1, city: 'Tunis', address: 'Bab Souika, Tunis',          images: pick(IMGS.apt),           description: 'Proche medina, entièrement rénové, meublé.' },
  { title: 'Appartement S+3 — Mutuelleville', type: 'vente',   price: 420000, surface: 150, rooms: 4, city: 'Tunis', address: 'Mutuelleville, Tunis',       images: pick(IMGS.apt, 2),        description: 'Quartier huppé, ascenseur, cave, gardien.' },
  { title: 'Local commercial — Avenue Habib Bourguiba',type:'location',price:5000, surface: 300,rooms:3,city:'Tunis',address:'Avenue Habib Bourguiba',      images: pick(IMGS.commercial, 2), description: 'Artère principale de Tunis, très haute visibilité.' },
  { title: 'Villa S+3 — Ennasr 2',            type: 'vente',   price: 560000, surface: 250, rooms: 4, city: 'Ariana', address: 'Ennasr 2, Ariana',          images: pick(IMGS.villa, 2),      description: 'Résidence fermée, piscine commune, sécurité 24h.' },
  { title: 'Appartement S+2 — Riadh El Andalous',type:'vente', price: 245000, surface: 100, rooms: 3, city: 'Ariana', address: 'Riadh El Andalous',         images: pick(IMGS.apt),           description: 'Excellent état, lumineux, proche Metro.' },
]

async function seedListings() {
  if (mongoose.connection.readyState === 0) {
    await mongoose.connect(process.env.MONGODB_URI)
  }

  await seedAdmin()

  const seller = await User.findOne({ email: 'admin@estatemind.com' })

  // Remove old seeded listings from admin, keep user-added ones
  await Listing.deleteMany({ seller: seller._id })

  let created = 0
  for (const data of LISTINGS) {
    await Listing.create({ ...data, seller: seller._id, status: 'active' })
    created++
  }

  console.log(`✅ ${created} annonces créées avec images (${LISTINGS.length} au total)`)

  if (require.main === module) {
    await mongoose.disconnect()
  }
}

module.exports = { seedListings }

if (require.main === module) {
  seedListings().catch(err => {
    console.error('❌ Erreur seedListings:', err)
    process.exit(1)
  })
}
