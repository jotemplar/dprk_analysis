#!/usr/bin/env python3
"""Test search functionality to debug duplicate issue"""

from search.serp_image_client import SerpImageClient

client = SerpImageClient()
results = client.search_images('"North Korean workers" AND Russia Far East image 2023', num_results=20)

print(f"Total results: {len(results)}")

# Check for duplicate URLs
urls = [r.get('source_url', '') for r in results]
unique_urls = set(urls)

print(f"Unique URLs: {len(unique_urls)}")

if len(urls) != len(unique_urls):
    print("\nDuplicates found:")
    seen = set()
    for url in urls:
        if url in seen:
            print(f"  - {url}")
        seen.add(url)
else:
    print("No duplicates in search results")

# Show first 3 results
print("\nFirst 3 results:")
for i, r in enumerate(results[:3], 1):
    print(f"{i}. {r.get('title', 'No title')[:50]}...")
    print(f"   URL: {r.get('source_url', '')[:50]}...")
    print(f"   Image: {r.get('image_url', '')[:50]}...")