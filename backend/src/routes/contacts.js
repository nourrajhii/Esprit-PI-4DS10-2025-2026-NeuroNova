const router = require('express').Router()
const ctrl = require('../controllers/contactController')
const { authenticate, authorize } = require('../middlewares/auth')

// Send a contact request on a listing
router.post('/',          authenticate, authorize('user', 'investor', 'seller', 'admin'), ctrl.send)

// Sender: see what I sent
router.get('/sent',       authenticate, ctrl.mySent)

// Seller: see requests received on my listings
router.get('/received',   authenticate, authorize('seller', 'admin'), ctrl.myReceived)

// Admin: all contacts
router.get('/',           authenticate, authorize('admin'), ctrl.all)

// Update status (seller or admin)
router.patch('/:id/status', authenticate, authorize('seller', 'admin'), ctrl.updateStatus)

module.exports = router
