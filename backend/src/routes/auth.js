const router = require('express').Router()
const { register, login, refresh, logout, me } = require('../controllers/authController')
const { authenticate } = require('../middlewares/auth')

router.post('/register', register)
router.post('/login',    login)
router.post('/refresh',  refresh)
router.post('/logout',   authenticate, logout)
router.get('/me',        authenticate, me)

module.exports = router
