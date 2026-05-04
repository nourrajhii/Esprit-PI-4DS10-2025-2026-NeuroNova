import os, sys
os.environ['RECOMMENDER_URL'] = 'http://localhost:8001'
os.environ['DEVIS_URL']       = 'http://localhost:8002'
os.environ['LEGAL_URL']       = 'http://localhost:8003'
os.environ['FORECAST_URL']    = 'http://localhost:8004'
os.environ['PRICE_URL']       = 'http://localhost:8005'
os.environ['INVESTMENT_URL']  = 'http://localhost:8006'
os.environ['GEO_URL']         = 'http://localhost:8007'
os.environ['LIFESTYLE_URL']   = 'http://localhost:8010'
os.environ['DHIA_URL']        = 'http://localhost:8055'
os.environ['REDIS_URL']       = 'redis://localhost:6379'
sys.path.insert(0, '.')
import uvicorn
uvicorn.run('main:app', host='0.0.0.0', port=8000)
