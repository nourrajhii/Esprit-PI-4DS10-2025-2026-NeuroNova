# EstateMind — Redeploy Notes (May 2026)

This update includes:
1. **Fix for http://158.158.44.182/** (port 80 routing)
2. **Detailed prediction agent** at `/predict` — real numeric breakdown, ROI charts, CSV/Excel export

---

## 1. Why http://158.158.44.182/ doesn't work but :3001 does

Your nginx reverse-proxy container listens on port 80 inside Docker and is mapped to host port 80 (see `docker-compose.azure.yml` → `nginx` service → `ports: ["80:80"]`). The mapping is correct.

The most likely cause is that **the Azure NSG (Network Security Group) for `estatemind-vm` does not have an inbound rule for TCP/80**. Port 3001 works because that rule was opened during initial deployment, but port 80 was never added.

### Fix from your local machine (Azure CLI)

```bash
# Make sure you're logged in
az login

# Find your NSG name (usually <vm-name>NSG)
az network nsg list -g estatemind-spain-rg --query "[].name" -o tsv

# Allow inbound TCP/80
az network nsg rule create \
  --resource-group estatemind-spain-rg \
  --nsg-name estatemind-vmNSG \
  --name AllowHTTP \
  --priority 320 \
  --access Allow --protocol Tcp --direction Inbound \
  --source-address-prefixes '*' --source-port-ranges '*' \
  --destination-address-prefixes '*' --destination-port-ranges 80
```

### Verify
After the rule is added, on the VM:

```bash
ssh azureuser@158.158.44.182
docker ps | grep nginx                        # immo-nginx must be running
docker logs immo-nginx --tail 50              # check for errors
curl -I http://localhost/                     # should return 200/301 from nginx
```

Then from your laptop: `curl -I http://158.158.44.182/` should also return 200.

---

## 2. Deploy the new prediction agent + UI

### On your local machine

```bash
cd "C:\Users\yosri\Desktop\Estate Mind"
git add viagra/main.py nginx.azure.conf frontend/src/app/\(main\)/predict/page.tsx REDEPLOY-NOTES.md
git commit -m "feat(predict): detailed numeric breakdown, ROI charts, CSV export + nginx port-80 NSG note"
git push origin <your-branch-name>
```

### On the Azure VM

```bash
ssh azureuser@158.158.44.182
cd ~/EstateMind   # or wherever you cloned it
git pull

# Rebuild only the two services that changed (faster than full rebuild)
docker-compose -f docker-compose.azure.yml build viagra frontend
docker-compose -f docker-compose.azure.yml up -d viagra frontend nginx

# Verify
docker logs immo-viagra   --tail 30
docker logs immo-frontend --tail 30
curl -s http://localhost/health/viagra
```

Then visit:
- **http://158.158.44.182/predict** (after the NSG rule above)
- or **http://158.158.44.182:3001/predict** (works today)

---

## 3. What changed in `/predict`

### Backend (`viagra/main.py` — `/dhia/predict`)
The endpoint now returns a much richer payload:

| Field | Description |
|---|---|
| `ml_price` | Point estimate (TND) |
| `price_low`, `price_high` | Estimation range (±12% / +15%) |
| `price_per_m2` | TND/m² for the property |
| `city_avg_per_m2` | Average TND/m² in the chosen city |
| `national_avg_per_m2` | National average baseline (2000 TND/m²) |
| `city_multiplier` | Localisation coefficient (e.g. Tunis = 1.6×) |
| `rental_yield_pct` | Estimated gross yield (%) |
| `monthly_rent_tnd`, `annual_rent_tnd` | Estimated rent |
| `annual_appreciation_pct` | Yearly appreciation estimate |
| `market_position` | `above` / `average` / `below` city median |
| `roi_projection` | Array of 11 points (year 0–10) with `value_tnd`, `cumulative_rent_tnd`, `total_gain_tnd`, `roi_pct` |
| `comparables` | 4 reference points (city median, national avg, low, high) |
| `report` | Markdown narrative (Gemini if available, else heuristic) |

### Frontend (`/predict` page)
- **Hero card** with main estimate + range + market-position badge
- **6 KPI cards**: prix au m², moyenne ville, moyenne nationale, loyer mensuel, rendement, appréciation /an
- **ROI projection line chart** (10 years) — property value + cumulative rent
- **Comparables bar chart** — your bien vs city median vs national average
- **Detailed comparables table** with % delta vs estimate
- **Markdown report** (existing Gemini analysis)
- **"Télécharger Excel/CSV" button** — downloads a UTF-8 BOM CSV that opens cleanly in Excel with all numbers + projections + comparables

The investment-scoring panel and the market-scanner are **untouched** — they keep working exactly as before.

---

## 4. Files modified

```
viagra/main.py                                   (+~75 lines)
nginx.azure.conf                                 (+8 lines — NSG note)
frontend/src/app/(main)/predict/page.tsx         (+~280 lines)
REDEPLOY-NOTES.md                                (new — this file)
```

No new dependencies required — `recharts` is already in `frontend/package.json`.
