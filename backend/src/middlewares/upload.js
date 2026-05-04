const multer = require('multer')
const path = require('path')
const fs = require('fs')

const uploadDir = path.join(__dirname, '../../', process.env.UPLOAD_DIR || 'uploads')
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true })

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadDir),
  filename: (req, file, cb) => {
    const unique = Date.now() + '-' + Math.round(Math.random() * 1e9)
    cb(null, unique + path.extname(file.originalname))
  },
})

const fileFilter = (req, file, cb) => {
  const allowed = /jpeg|jpg|png|webp/
  if (allowed.test(file.mimetype)) return cb(null, true)
  cb(new Error('Seuls les fichiers images sont acceptés (jpg, png, webp)'))
}

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: parseInt(process.env.MAX_FILE_SIZE || '5242880') },
})

module.exports = upload
