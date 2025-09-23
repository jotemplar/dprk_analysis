"""Combined search terms for DPRK image capture - original + themed exploitation searches"""

from dprk_images_search_terms import search_terms_comprehensive
from dprk_images_search_terms_2 import (
    theme_construction_exploitation,
    theme_dorms_living,
    theme_handlers,
    theme_community,
    theme_financial
)

# Create combined list with theme metadata
search_terms_with_themes = []

# Add original search terms
for term in search_terms_comprehensive:
    search_terms_with_themes.append({
        'term': term,
        'theme': 'general',
        'source': 'original'
    })

# Add themed exploitation search terms
for term in theme_construction_exploitation:
    search_terms_with_themes.append({
        'term': term,
        'theme': 'construction_exploitation',
        'source': 'themed'
    })

for term in theme_dorms_living:
    search_terms_with_themes.append({
        'term': term,
        'theme': 'dorms_living',
        'source': 'themed'
    })

for term in theme_handlers:
    search_terms_with_themes.append({
        'term': term,
        'theme': 'handlers_oversight',
        'source': 'themed'
    })

for term in theme_community:
    search_terms_with_themes.append({
        'term': term,
        'theme': 'community_mistreatment',
        'source': 'themed'
    })

for term in theme_financial:
    search_terms_with_themes.append({
        'term': term,
        'theme': 'financial_exploitation',
        'source': 'themed'
    })

# Summary statistics
def print_summary():
    """Print summary of combined search terms"""
    themes = {}
    for item in search_terms_with_themes:
        theme = item['theme']
        themes[theme] = themes.get(theme, 0) + 1

    print("\n" + "=" * 60)
    print("COMBINED SEARCH TERMS SUMMARY")
    print("=" * 60)
    print(f"Total search terms: {len(search_terms_with_themes)}")
    print("\nBreakdown by theme:")
    for theme, count in sorted(themes.items()):
        print(f"  {theme}: {count} terms")
    print("=" * 60)

if __name__ == "__main__":
    print_summary()