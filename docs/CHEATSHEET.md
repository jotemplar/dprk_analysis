# DPRK System - Command Cheatsheet

## 🚀 Most Used Commands

### Start Working
```bash
cd /Volumes/X5/_CODE_PROJECTS/DPRK
ollama serve                    # Start LLM (in separate terminal)
./run.sh test                   # Quick test run
```

### Full Pipeline
```bash
./run.sh full                   # Process all search terms
```

## 📊 Check Results

### Database Queries
```bash
# Count captured images
psql -U postgres -d dprk -c "SELECT COUNT(*) FROM captured_images;"

# Count analyzed images
psql -U postgres -d dprk -c "SELECT COUNT(*) FROM content_analysis;"

# View high concern images
psql -U postgres -d dprk -c "SELECT file_path FROM captured_images ci JOIN content_analysis ca ON ci.result_id = ca.result_id WHERE ca.concern_level IN ('high', 'critical');"

# Search queries by language
psql -U postgres -d dprk -c "SELECT language, COUNT(*) FROM search_queries GROUP BY language;"
```

### File System
```bash
# Today's images
ls captured_data/images/$(date +%Y-%m-%d)/

# Count all images
find captured_data/images -type f | wc -l

# Latest screenshots
ls -lt captured_data/screenshots/*/* | head -10
```

## 🔧 Troubleshooting

### Quick Fixes
```bash
# System not working?
./run.sh basic                  # Check all components

# Database error?
uv run --no-project python init_database.py

# Ollama not responding?
pkill ollama && ollama serve

# Missing dependencies?
uv pip install -r requirements.txt
```

### Reset Everything
```bash
# Complete reset
dropdb dprk
createdb dprk
uv run --no-project python init_database.py
rm -rf captured_data/*/*
./run.sh test
```

## 📈 Monitor Progress

### Real-time Monitoring
```bash
# Watch image downloads (in new terminal)
watch -n 5 'find captured_data/images -type f | wc -l'

# Monitor database growth
watch -n 10 'psql -U postgres -d dprk -c "SELECT (SELECT COUNT(*) FROM search_results) as results, (SELECT COUNT(*) FROM captured_images) as images, (SELECT COUNT(*) FROM content_analysis) as analyzed;"'

# Check disk usage
watch -n 60 'du -sh captured_data/*'
```

### Session Status
```bash
# Latest session info
psql -U postgres -d dprk -c "SELECT * FROM search_sessions ORDER BY started_at DESC LIMIT 1;"

# Failed downloads
psql -U postgres -d dprk -c "SELECT COUNT(*) FROM search_results WHERE image_download_status='failed';"
```

## 🔑 Key Paths

```bash
# Important files
.env                            # API keys and config
dprk_images_search_terms.py     # Search terms (47 total)
main.py                         # Main pipeline script

# Data locations
captured_data/images/           # Downloaded images
captured_data/screenshots/      # Page screenshots
logs/                           # System logs
reports/                        # Generated reports
```

## 💡 Pro Tips

```bash
# Run in background
nohup ./run.sh full > pipeline.log 2>&1 &

# Follow log output
tail -f pipeline.log

# Quick backup
pg_dump -U postgres dprk > backup_$(date +%Y%m%d_%H%M%S).sql
tar -czf images_$(date +%Y%m%d).tar.gz captured_data/

# Find images by concern level
psql -U postgres -d dprk -c "SELECT ci.file_path, ca.concern_level FROM captured_images ci JOIN content_analysis ca ON ci.result_id = ca.result_id WHERE ca.concern_level != 'low' ORDER BY ca.concern_level DESC;"

# Export results to CSV
psql -U postgres -d dprk -c "\COPY (SELECT * FROM content_analysis) TO 'analysis_export.csv' WITH CSV HEADER;"
```

## ⚡ Speed Run

```bash
# Complete pipeline in 3 commands
ollama serve &                  # 1. Start LLM
./setup.sh                       # 2. Setup everything
./run.sh test                   # 3. Test run
```

## 📱 Status Indicators

- ✅ All systems go: `./run.sh basic` shows all PASS
- ⚠️  Ollama issue: Check with `curl http://localhost:11434/api/tags`
- ❌ Database issue: Check with `psql -U postgres -d dprk -c "SELECT 1;"`
- 📊 Storage full: Check with `df -h captured_data/`

---

**Remember**: Use `uv run --no-project` prefix for all Python scripts!