#!/bin/bash
# Russian OSINT Search Pipeline Runner
# Usage: ./run_russian_pipeline.sh [setup|search|export|report|full]

set -e

BASEPATH="/Volumes/X5/_CODE_PROJECTS/DPRK"
export PYTHONPATH="$BASEPATH"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
CSV_FILE="search_terms/dprk_osint_queries_with_social_and_portals_v1_3.csv"
NUM_RESULTS=10
DELAY=2.0

# Functions
setup() {
    echo -e "${BLUE}Setting up Russian OSINT search database...${NC}"
    python database/create_russian_tables.py
    echo -e "${GREEN}✓ Database setup complete${NC}\n"
}

search() {
    echo -e "${BLUE}Processing Russian OSINT search queries...${NC}"
    echo -e "${YELLOW}CSV: $CSV_FILE${NC}"
    echo -e "${YELLOW}Results per query: $NUM_RESULTS${NC}"
    echo -e "${YELLOW}Delay between queries: ${DELAY}s${NC}\n"

    python scripts/russian/process_russian_searches.py \
        --csv "$CSV_FILE" \
        --num-results "$NUM_RESULTS" \
        --delay "$DELAY"

    echo -e "\n${GREEN}✓ Search processing complete${NC}\n"
}

export_excel() {
    echo -e "${BLUE}Generating Excel export...${NC}"
    
    # Ensure reports directory exists
    mkdir -p reports
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    OUTPUT_FILE="reports/russian_osint_results_${TIMESTAMP}.xlsx"

    python scripts/reporting/export_russian_searches_to_excel.py --output "$OUTPUT_FILE"

    echo -e "${GREEN}✓ Excel export complete: $OUTPUT_FILE${NC}\n"
}

export_html() {
    echo -e "${BLUE}Generating HTML report...${NC}"
    
    # Ensure reports directory exists
    mkdir -p reports
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    OUTPUT_FILE="reports/russian_osint_report_${TIMESTAMP}.html"

    python scripts/reporting/generate_russian_search_report.py --output "$OUTPUT_FILE"

    echo -e "${GREEN}✓ HTML report complete: $OUTPUT_FILE${NC}\n"

    # Ask to open in browser
    read -p "Open report in browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$OUTPUT_FILE"
    fi
}

check_status() {
    echo -e "${BLUE}Checking pipeline status...${NC}\n"

    psql -U postgres -d dprk -c "
        SELECT
            COUNT(*) as total_queries,
            SUM(CASE WHEN search_status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN search_status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN search_status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(results_count) as total_results
        FROM russian_searches;
    "

    echo -e "\n${BLUE}Engine breakdown:${NC}\n"

    psql -U postgres -d dprk -c "
        SELECT
            engine,
            COUNT(*) as queries,
            SUM(results_count) as results,
            ROUND(AVG(results_count), 2) as avg_per_query
        FROM russian_searches
        GROUP BY engine;
    "
}

usage() {
    echo "Russian OSINT Search Pipeline Runner"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  setup     - Create database tables (first time only)"
    echo "  search    - Process search queries from CSV"
    echo "  export    - Generate Excel export"
    echo "  report    - Generate HTML report"
    echo "  full      - Run complete pipeline (search + export + report)"
    echo "  status    - Check current pipeline status"
    echo ""
    echo "Options:"
    echo "  --csv FILE          CSV file to process (default: $CSV_FILE)"
    echo "  --num-results N     Results per query (default: $NUM_RESULTS)"
    echo "  --delay SECONDS     Delay between queries (default: $DELAY)"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 search"
    echo "  $0 search --csv test_queries.csv --num-results 5 --delay 1"
    echo "  $0 full"
    echo "  $0 status"
}

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --csv)
            CSV_FILE="$2"
            shift 2
            ;;
        --num-results)
            NUM_RESULTS="$2"
            shift 2
            ;;
        --delay)
            DELAY="$2"
            shift 2
            ;;
        setup|search|export|report|full|status|help)
            COMMAND="$1"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Default to help if no command
if [ -z "$COMMAND" ]; then
    usage
    exit 0
fi

# Execute command
case $COMMAND in
    setup)
        setup
        ;;
    search)
        search
        ;;
    export)
        export_excel
        ;;
    report)
        export_html
        ;;
    full)
        echo -e "${BLUE}Running complete Russian OSINT pipeline...${NC}\n"
        search
        export_excel
        export_html
        echo -e "${GREEN}✓ Complete pipeline finished!${NC}\n"
        check_status
        ;;
    status)
        check_status
        ;;
    help)
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        usage
        exit 1
        ;;
esac
