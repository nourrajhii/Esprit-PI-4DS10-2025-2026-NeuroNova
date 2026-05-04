const router = require('express').Router()
const ctrl   = require('../controllers/listingController')
const { authenticate, authorize } = require('../middlewares/auth')
const upload = require('../middlewares/upload')

// Must be before /:id to avoid matching 'mine' as an id
router.get('/mine', authenticate, authorize('seller', 'admin'), ctrl.myListings)

// Public browse (no auth required for viewing active listings)
router.get('/',     ctrl.list)
router.get('/:id',  ctrl.getOne)

router.post('/',
  authenticate,
  authorize('seller', 'admin'),
  upload.array('images', 10),
  ctrl.create
)

router.put('/:id',
  authenticate,
  authorize('seller', 'admin'),
  upload.array('images', 10),
  ctrl.update
)

router.delete('/:id',
  authenticate,
  authorize('seller', 'admin'),
  ctrl.remove
)

module.exports = router
