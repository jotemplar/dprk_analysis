#!/usr/bin/env python3
import json

# Read the JSON data
with open('dashboard_data.json', 'r') as f:
    data = json.load(f)

# Create the complete HTML with properly escaped template literals
html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DPRK Image Analysis Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .fade-in { animation: fadeIn 0.3s ease-out; }
        .glass-effect {
            background: rgba(17, 25, 40, 0.75);
            backdrop-filter: saturate(180%) blur(12px);
        }
        .line-clamp-2 {
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
    </style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen">
    <div id="root"></div>

    <script>
        // Embedded dashboard data
        window.dashboardData = %s;
    </script>

    <script type="text/babel">
        const { useState, useMemo } = React;

        // Use the embedded data
        const dashboardData = window.dashboardData;

        function Badge({ children, variant = "default", className = "" }) {
            const variants = {
                default: "bg-gray-700 text-gray-100",
                success: "bg-green-900 text-green-200",
                warning: "bg-yellow-900 text-yellow-200",
                danger: "bg-red-900 text-red-200",
                info: "bg-blue-900 text-blue-200"
            };

            return React.createElement('span', {
                className: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]} ${className}`
            }, children);
        }

        function Card({ children, className = "", onClick }) {
            return React.createElement('div', {
                className: `bg-gray-900 rounded-lg shadow-xl border border-gray-800 ${className}`,
                onClick: onClick
            }, children);
        }

        function StatCard({ title, value, total, color = "blue" }) {
            const percentage = total ? Math.round((value / total) * 100) : 0;
            const bgColor = color === 'blue' ? 'bg-blue-500' :
                          color === 'green' ? 'bg-green-500' :
                          color === 'purple' ? 'bg-purple-500' : 'bg-yellow-500';

            return React.createElement(Card, { className: "p-6 fade-in" },
                React.createElement('div', null,
                    React.createElement('p', { className: "text-sm text-gray-400 mb-1" }, title),
                    React.createElement('p', { className: "text-3xl font-bold text-gray-100" }, value.toLocaleString()),
                    React.createElement('div', { className: "mt-2" },
                        React.createElement('div', { className: "w-full bg-gray-800 rounded-full h-2" },
                            React.createElement('div', {
                                className: `h-2 rounded-full transition-all duration-500 ${bgColor}`,
                                style: { width: `${percentage}%` }
                            })
                        ),
                        React.createElement('span', { className: "ml-2 text-xs text-gray-400" }, `${percentage}%`)
                    )
                )
            );
        }

        function ImageCard({ item, onSelect }) {
            const getConcernBadgeVariant = (level) => {
                switch(level?.toLowerCase()) {
                    case "critical": return "danger";
                    case "high": return "danger";
                    case "medium": return "warning";
                    case "low": return "success";
                    default: return "default";
                }
            };

            const thumbnailUrl = item.thumbnail ?
                `data:image/jpeg;base64,${item.thumbnail}` :
                "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='200' height='200' fill='%23374151'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%239CA3AF' font-size='14'%3ENo Image%3C/text%3E%3C/svg%3E";

            return React.createElement(Card, {
                className: "overflow-hidden hover:ring-2 hover:ring-blue-500 transition-all cursor-pointer fade-in",
                onClick: () => onSelect(item)
            },
                React.createElement('div', { className: "aspect-video bg-gray-800 relative" },
                    React.createElement('img', {
                        src: thumbnailUrl,
                        alt: item.file_name,
                        className: "w-full h-full object-cover"
                    }),
                    React.createElement('div', { className: "absolute top-2 right-2 flex gap-1" },
                        item.has_llava && React.createElement(Badge, { variant: "info" }, "LLaVA"),
                        item.has_gemma && React.createElement(Badge, { variant: "info" }, "Gemma")
                    )
                ),
                React.createElement('div', { className: "p-4" },
                    React.createElement('p', { className: "text-xs text-gray-400 mb-2 truncate" }, item.file_name),
                    item.source_domain && React.createElement('p', { className: "text-xs text-blue-400 mb-2 truncate" }, `📍 ${item.source_domain}`),
                    React.createElement('div', { className: "flex items-center justify-between mb-2" },
                        React.createElement(Badge, { variant: getConcernBadgeVariant(item.concern_level) }, item.concern_level),
                        item.personnel_count > 0 && React.createElement('span', { className: "text-xs text-gray-400" }, `👥 ${item.personnel_count}`)
                    ),
                    React.createElement('p', { className: "text-xs text-gray-300 line-clamp-2" },
                        item.scene_description || item.gemma_description || "No description available"
                    )
                )
            );
        }

        function Dashboard() {
            const [searchTerm, setSearchTerm] = useState("");
            const [concernFilter, setConcernFilter] = useState("all");
            const [selectedItem, setSelectedItem] = useState(null);

            const filteredData = useMemo(() => {
                return dashboardData.data.filter(item => {
                    const matchesSearch = searchTerm === "" ||
                        item.file_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        item.scene_description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        item.gemma_description?.toLowerCase().includes(searchTerm.toLowerCase());

                    const matchesConcern = concernFilter === "all" ||
                        item.concern_level?.toLowerCase() === concernFilter.toLowerCase() ||
                        item.gemma_concern_level?.toLowerCase() === concernFilter.toLowerCase();

                    return matchesSearch && matchesConcern;
                });
            }, [searchTerm, concernFilter]);

            return React.createElement('div', { className: "min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950" },
                React.createElement('header', { className: "glass-effect border-b border-gray-800 sticky top-0 z-40" },
                    React.createElement('div', { className: "container mx-auto px-4 py-6" },
                        React.createElement('h1', { className: "text-2xl md:text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent" },
                            "DPRK Image Analysis Dashboard"
                        ),
                        React.createElement('p', { className: "text-sm text-gray-400 mt-1" },
                            "Humanitarian concern assessment using LLaVA and Gemma models"
                        )
                    )
                ),

                React.createElement('div', { className: "container mx-auto px-4 py-8" },
                    React.createElement('div', { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8" },
                        React.createElement(StatCard, { title: "Total Images", value: dashboardData.stats.total_images, total: dashboardData.stats.total_images, color: "blue" }),
                        React.createElement(StatCard, { title: "Total Analyses", value: dashboardData.stats.total_analyses, total: dashboardData.stats.total_images, color: "green" }),
                        React.createElement(StatCard, { title: "LLaVA Processed", value: dashboardData.stats.llava_count, total: dashboardData.stats.total_images, color: "purple" }),
                        React.createElement(StatCard, { title: "Gemma Processed", value: dashboardData.stats.gemma_count, total: dashboardData.stats.total_images, color: "yellow" })
                    ),

                    React.createElement(Card, { className: "p-4 mb-8" },
                        React.createElement('div', { className: "grid grid-cols-1 md:grid-cols-3 gap-4" },
                            React.createElement('input', {
                                type: "text",
                                placeholder: "Search images...",
                                className: "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                                value: searchTerm,
                                onChange: (e) => setSearchTerm(e.target.value)
                            }),
                            React.createElement('select', {
                                className: "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                                value: concernFilter,
                                onChange: (e) => setConcernFilter(e.target.value)
                            },
                                React.createElement('option', { value: "all" }, "All Levels"),
                                React.createElement('option', { value: "critical" }, "Critical"),
                                React.createElement('option', { value: "high" }, "High"),
                                React.createElement('option', { value: "medium" }, "Medium"),
                                React.createElement('option', { value: "low" }, "Low")
                            ),
                            React.createElement('button', {
                                className: "w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition",
                                onClick: () => {
                                    setSearchTerm("");
                                    setConcernFilter("all");
                                }
                            }, "Clear Filters")
                        )
                    ),

                    React.createElement('p', { className: "text-sm text-gray-400 mb-4" },
                        `Showing ${filteredData.length} of ${dashboardData.data.length} images`
                    ),

                    React.createElement('div', { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" },
                        filteredData.map((item) =>
                            React.createElement(ImageCard, { key: item.id, item: item, onSelect: setSelectedItem })
                        )
                    ),

                    selectedItem && React.createElement('div', {
                        className: "fixed inset-0 z-50 overflow-y-auto bg-black/75",
                        onClick: () => setSelectedItem(null)
                    },
                        React.createElement('div', { className: "flex min-h-screen items-center justify-center p-4" },
                            React.createElement('div', {
                                className: "relative bg-gray-900 rounded-xl shadow-2xl max-w-4xl w-full p-6",
                                onClick: (e) => e.stopPropagation()
                            },
                                React.createElement('button', {
                                    onClick: () => setSelectedItem(null),
                                    className: "absolute top-4 right-4 text-gray-400 hover:text-white"
                                }, "✕"),
                                React.createElement('h2', { className: "text-xl font-semibold mb-4" }, "Analysis Details"),
                                React.createElement('div', { className: "space-y-4" },
                                    React.createElement('p', { className: "text-sm text-gray-400" }, selectedItem.file_name),
                                    selectedItem.source_url && React.createElement('div', { className: "mb-4" },
                                        React.createElement('p', { className: "text-xs text-gray-400 mb-1" }, "Source:"),
                                        React.createElement('a', {
                                            href: selectedItem.source_url,
                                            target: "_blank",
                                            rel: "noopener noreferrer",
                                            className: "text-xs text-blue-400 hover:text-blue-300 break-all"
                                        }, selectedItem.source_url)
                                    ),
                                    selectedItem.scene_description && React.createElement('div', null,
                                        React.createElement('h3', { className: "text-sm font-medium text-gray-400 mb-2" }, "LLaVA Analysis"),
                                        React.createElement('p', { className: "text-sm text-gray-300" }, selectedItem.scene_description)
                                    ),
                                    selectedItem.gemma_description && React.createElement('div', null,
                                        React.createElement('h3', { className: "text-sm font-medium text-gray-400 mb-2" }, "Gemma Analysis"),
                                        React.createElement('p', { className: "text-sm text-gray-300" }, selectedItem.gemma_description)
                                    )
                                )
                            )
                        )
                    )
                )
            );
        }

        ReactDOM.render(React.createElement(Dashboard), document.getElementById("root"));
    </script>
</body>
</html>"""

# Insert the JSON data using format()
final_html = html_template.replace('%s', json.dumps(data))

# Write the file
with open('dprk_dashboard_final.html', 'w', encoding='utf-8') as f:
    f.write(final_html)

print(f"✅ Created dprk_dashboard_final.html")
print(f"📊 Includes {len(data['data'])} images with thumbnails")
print(f"📈 Stats: {data['stats']['total_images']} total images")
print(f"🔵 LLaVA: {data['stats']['llava_count']} processed")
print(f"🟡 Gemma: {data['stats']['gemma_count']} processed")