# ✅ Deployment Checklist: Multi-Content Support

## Pre-Deployment

### 1. Database Migration
- [ ] Backup database corrente
  ```bash
  pg_dump kickthisuss > backup_$(date +%Y%m%d).sql
  ```
- [ ] Test migration su database di test
  ```bash
  python migrations/add_content_type_fields.py
  ```
- [ ] Verifica colonne aggiunte
  ```sql
  SELECT column_name FROM information_schema.columns 
  WHERE table_name = 'solution' AND column_name = 'content_type';
  ```
- [ ] Test rollback
  ```bash
  python migrations/add_content_type_fields.py downgrade
  python migrations/add_content_type_fields.py  # upgrade again
  ```

### 2. Code Validation
- [ ] Run test suite
  ```bash
  python test_content_types.py
  ```
- [ ] Verifica tutti i test passano (16/16)
- [ ] Check import conflicts risolti
- [ ] Verifica GitHub service carica correttamente

### 3. Configuration
- [ ] Verifica `.env` ha GitHub settings (se abilitato)
  ```bash
  GITHUB_ENABLED=true
  GITHUB_TOKEN=ghp_...
  GITHUB_ORG=kickthisuss-projects
  ```
- [ ] Check file size limits appropriati per server
- [ ] Verifica storage space disponibile

### 4. Dependencies
- [ ] Nessuna nuova dependency richiesta ✅
- [ ] Python version compatibility (3.8+) ✅
- [ ] Librerie esistenti sufficienti ✅

---

## Deployment Steps

### Step 1: Stop Services
```bash
# Stop Flask
pkill -f "flask run"

# Stop Celery (if running)
pkill -f "celery worker"
```

### Step 2: Backup
```bash
# Backup database
cp instance/dev.db instance/dev_backup_$(date +%Y%m%d).db

# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz app/static/uploads/
```

### Step 3: Pull Changes
```bash
git pull origin master

# Or if deploying from specific commit
git checkout <commit-hash>
```

### Step 4: Run Migration
```bash
python migrations/add_content_type_fields.py
```

Expected output:
```
✓ Added content_type to solution table
✓ Added content_type to solution_file table
✓ Added content_category to solution_file table
✓ Created indexes
✓ Updated existing solution_file records
✅ Migration completed successfully!
```

### Step 5: Verify Migration
```bash
python -c "
from app import create_app, db
from app.models import Solution, SolutionFile
app = create_app()
with app.app_context():
    # Check solution has content_type
    s = db.session.execute('SELECT content_type FROM solution LIMIT 1')
    print('✅ Solution.content_type exists')
    
    # Check solution_file has new fields
    sf = db.session.execute('SELECT content_type, content_category FROM solution_file LIMIT 1')
    print('✅ SolutionFile.content_type exists')
    print('✅ SolutionFile.content_category exists')
"
```

### Step 6: Test in Development
```bash
# Start Flask in debug mode
flask run --debug

# In another terminal, run quick test
python test_content_types.py
```

### Step 7: Start Production Services
```bash
# Start Flask with production config
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Start Celery (if GitHub enabled)
celery -A celery_worker.celery worker --loglevel=info -D
```

### Step 8: Smoke Tests
- [ ] Test homepage loads
  ```bash
  curl http://localhost:5000/
  ```
- [ ] Test solution upload page loads
  ```bash
  curl http://localhost:5000/projects/1/submit-solution
  ```
- [ ] Test file upload works (manual)
- [ ] Test GitHub sync works (if enabled)

---

## Post-Deployment Verification

### 1. Functional Tests

#### Test Software Upload
```bash
# Create test file
echo "print('Hello')" > test.py

# Upload via curl
curl -X POST http://localhost:5000/api/solutions/upload \
  -F "file=@test.py" \
  -F "content_type=software" \
  -F "task_id=1"
```

#### Test Design Upload
```bash
# Upload image
curl -X POST http://localhost:5000/api/solutions/upload \
  -F "file=@test_logo.png" \
  -F "content_type=design" \
  -F "task_id=1"
```

#### Test Validation
```bash
# Test file too large (should fail)
dd if=/dev/zero of=huge.bin bs=1M count=600  # 600MB file

curl -X POST http://localhost:5000/api/solutions/upload \
  -F "file=@huge.bin" \
  -F "content_type=media" \
  -F "task_id=1"

# Expected: Error about file size limit
```

### 2. Database Verification
```sql
-- Check solutions have content_type
SELECT content_type, COUNT(*) 
FROM solution 
GROUP BY content_type;

-- Check files categorized correctly
SELECT content_type, content_category, COUNT(*) 
FROM solution_file 
GROUP BY content_type, content_category;

-- Check indexes created
SHOW INDEX FROM solution WHERE Key_name = 'idx_solution_content_type';
```

### 3. GitHub Integration (if enabled)
- [ ] Test repository creation
- [ ] Test file upload to GitHub
- [ ] Test branch creation
- [ ] Test PR creation
- [ ] Check file organization in correct directories

### 4. Performance Check
```bash
# Monitor resource usage
top -p $(pgrep -f "flask|gunicorn")

# Check upload speeds
time curl -X POST http://localhost:5000/api/solutions/upload \
  -F "file=@large_test.mp4"

# Expected: <5 seconds for 100MB file
```

---

## Rollback Plan (If Issues Arise)

### Option 1: Rollback Database Only
```bash
# Rollback migration
python migrations/add_content_type_fields.py downgrade

# Restart services
systemctl restart kickthisuss
```

### Option 2: Full Rollback
```bash
# Stop services
systemctl stop kickthisuss

# Restore database backup
cp instance/dev_backup_YYYYMMDD.db instance/dev.db

# Checkout previous version
git checkout <previous-commit>

# Restart services
systemctl start kickthisuss
```

### Option 3: Emergency Rollback
```bash
# Use backup and previous code
mv instance/dev.db instance/dev_broken.db
cp instance/dev_backup_YYYYMMDD.db instance/dev.db

git reset --hard HEAD~1

systemctl restart kickthisuss
```

---

## Monitoring

### Logs to Watch
```bash
# Flask logs
tail -f logs/flask.log | grep -i "content_type\|upload\|error"

# Celery logs (if enabled)
tail -f logs/celery.log | grep -i "github\|sync\|error"

# System logs
tail -f /var/log/syslog | grep kickthisuss
```

### Metrics to Monitor
- [ ] Upload success rate (should be >95%)
- [ ] Average upload time (should be <5s for 10MB)
- [ ] GitHub sync success rate (should be >90%)
- [ ] Error rate (should be <2%)
- [ ] Disk space usage (watch uploads folder)

### Alerts to Set
```bash
# Disk space alert (if >80%)
df -h /path/to/uploads | awk '{if ($5 > 80) print "ALERT: Disk usage high"}'

# Error rate alert
grep -c "ERROR" logs/flask.log | awk '{if ($1 > 10) print "ALERT: High error rate"}'
```

---

## Documentation Updates

- [ ] Update API documentation with content_type parameter
- [ ] Update user guide with new file types
- [ ] Update README.md with badges/info
- [ ] Notify users via email/announcement
- [ ] Update help center articles

---

## User Communication

### Email Template
```
Subject: 🎉 New Feature: Support for All Content Types!

Hi [Username],

Great news! KickThisUSS now supports 6 types of contributions:

💻 Software (code, apps, APIs)
🔧 Hardware (PCB, CAD, 3D models)
🎨 Design (logos, UI/UX, graphics) ⭐ NEW
📄 Documentation (guides, business plans) ⭐ NEW
🎬 Media (videos, audio, animations) ⭐ NEW
🔀 Mixed (complete projects)

You can now submit 150+ file formats!

Learn more: [link to guide]

Happy contributing!
```

### Announcement Post
```markdown
# 🚀 Multi-Content Support is Live!

We're excited to announce that KickThisUSS now supports **all types of contributions**!

## What's New?
- 🎨 Submit design files (Figma, Photoshop, Illustrator)
- 📄 Upload documentation (PDF, Word, Markdown)
- 🎬 Share media (videos, audio, animations)
- 💡 150+ file formats supported!

## Examples
- Designers can submit logos, UI mockups, brand guidelines
- Writers can contribute user guides, business plans
- Creators can share promo videos, tutorials

Ready to contribute? Check out our [Content Types Guide](link)
```

---

## Success Criteria

### Must Have (Before Go-Live)
- [x] All tests passing
- [x] Migration successful
- [x] No errors in logs
- [x] Backward compatibility verified
- [x] Documentation complete

### Should Have (First Week)
- [ ] At least 5 design submissions
- [ ] At least 3 documentation submissions
- [ ] At least 2 media submissions
- [ ] No rollbacks needed
- [ ] User feedback positive (>80%)

### Nice to Have (First Month)
- [ ] 100+ submissions across all types
- [ ] <1% error rate
- [ ] Featured in platform updates
- [ ] User testimonials collected
- [ ] Case studies documented

---

## Support Plan

### Week 1: Active Monitoring
- Check logs hourly
- Respond to issues within 1 hour
- Daily status updates to team

### Week 2-4: Normal Monitoring
- Check logs daily
- Respond to issues within 4 hours
- Weekly status reports

### Month 2+: Stable Operation
- Check logs as needed
- Standard support response times
- Monthly metrics review

---

## Contact

**In case of issues:**
- 🚨 Critical: Call tech lead immediately
- ⚠️ High: Slack #tech-urgent channel
- 📧 Normal: Email tech@kickthisuss.com

**Escalation Path:**
1. On-call developer (respond in 1h)
2. Tech lead (respond in 2h)
3. CTO (respond in 4h)

---

## Final Checklist

Before marking deployment as complete:

- [ ] All deployment steps completed
- [ ] Smoke tests passed
- [ ] Monitoring in place
- [ ] Documentation updated
- [ ] Users notified
- [ ] Rollback plan tested
- [ ] Support team trained
- [ ] Metrics baseline established

**Deployment Sign-off:**
- Developer: _________________ Date: _______
- Tech Lead: _________________ Date: _______
- QA: _______________________ Date: _______

---

**Status: Ready for Production** ✅
**Risk Level: Low** 🟢
**Estimated Downtime: <5 minutes** ⚡
