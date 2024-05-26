document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded and parsed');  // Debug: Confirm DOM content is loaded

    // Check if D3.js is loaded
    if (typeof d3 === 'undefined') {
        console.error('D3.js is not loaded.');
        return;
    } else {
        console.log('D3.js is loaded.');
    }

    // Function to load and render the graph
    function loadGraph() {
        console.log('Load Graph function called');  // Debug: Confirm function call

        fetch('/foaf_graph_data')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(function(data) {
                console.log("Fetched data:", data);  // Debug: Print the fetched data to the console

                const width = window.innerWidth;
                const height = window.innerHeight;

                // Remove any existing SVG element
                d3.select("#graph-container").select("svg").remove();

                // Create an SVG container with zoom functionality
                const svg = d3.select("#graph-container")
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height)
                    .call(d3.zoom().on("zoom", function(event) {
                        svg.attr("transform", event.transform);
                    }))
                    .append("g");

                console.log("SVG created");  // Debug: Confirm SVG creation

                // Initialize the force simulation
                const simulation = d3.forceSimulation(data.nodes)
                    .force("link", d3.forceLink(data.links).id(d => d.id).distance(250))  // Increased distance for readability
                    .force("charge", d3.forceManyBody().strength(-300))  // Increased repulsion for spacing
                    .force("center", d3.forceCenter(width / 2, height / 2));

                // Create links with different colors based on relationship type
                const link = svg.append("g")
                    .attr("class", "links")
                    .selectAll("line")
                    .data(data.links)
                    .enter().append("line")
                    .attr("stroke-width", 1.5)
                    .attr("stroke", d => {
                        if (d.relationship === 'both') return '#ff5733'; // Both mutual friends and shared interests
                        if (d.relationship === 'mutual') return '#337ab7'; // Mutual friends
                        if (d.relationship === 'interest') return '#5cb85c'; // Shared interests
                        return '#999'; // Default color
                    })
                    .attr("class", d => d.relationship); // Add class for filtering

                console.log("Links created");  // Debug: Confirm links creation

                // Create nodes
                const node = svg.append("g")
                    .attr("class", "nodes")
                    .selectAll("circle")
                    .data(data.nodes)
                    .enter().append("circle")
                    .attr("r", 10)  // Increased node size
                    .attr("fill", "#69b3a2")
                    .call(d3.drag()
                        .on("start", dragstarted)
                        .on("drag", dragged)
                        .on("end", dragended))
                    .on("mouseover", function(event, d) {
                        tooltip.transition()
                            .duration(200)
                            .style("opacity", .9);
                        tooltip.html(d.label)
                            .style("left", (event.pageX + 5) + "px")
                            .style("top", (event.pageY - 28) + "px");
                    })
                    .on("mouseout", function(d) {
                        tooltip.transition()
                            .duration(500)
                            .style("opacity", 0);
                    });

                console.log("Nodes created");  // Debug: Confirm nodes creation

                // Create labels
                const label = svg.append("g")
                    .attr("class", "labels")
                    .selectAll("text")
                    .data(data.nodes)
                    .enter().append("text")
                    .attr("dy", -10)  // Adjusted label position
                    .attr("dx", 12)
                    .attr("font-size", 12)  // Increased font size
                    .text(d => d.label);

                console.log("Labels created");  // Debug: Confirm labels creation

                // Define the ticked function to update positions
                function ticked() {
                    link
                        .attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);

                    node
                        .attr("cx", d => d.x)
                        .attr("cy", d => d.y);

                    label
                        .attr("x", d => d.x)
                        .attr("y", d => d.y);
                }

                // Add simulation event listeners
                simulation
                    .nodes(data.nodes)
                    .on("tick", ticked);

                simulation.force("link")
                    .links(data.links);

                // Define drag event functions
                function dragstarted(event, d) {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                }

                function dragged(event, d) {
                    d.fx = event.x;
                    d.fy = event.y;
                }

                function dragended(event, d) {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }

                // Create a tooltip
                const tooltip = d3.select("body").append("div")
                    .attr("class", "tooltip")
                    .style("opacity", 0);

                // Create a legend
                const legendData = [
                    { label: "Mutual Friends", color: "#337ab7" },
                    { label: "Shared Interests", color: "#5cb85c" },
                    { label: "Both", color: "#ff5733" }
                ];

                const legend = svg.append("g")
                    .attr("class", "legend")
                    .selectAll("g")
                    .data(legendData)
                    .enter().append("g")
                    .attr("transform", (d, i) => `translate(0,${i * 20})`);

                legend.append("rect")
                    .attr("x", width - 150)
                    .attr("width", 18)
                    .attr("height", 18)
                    .attr("fill", d => d.color);

                legend.append("text")
                    .attr("x", width - 120)
                    .attr("y", 9)
                    .attr("dy", "0.35em")
                    .attr("text-anchor", "start")
                    .text(d => d.label);

                console.log("Legend created");  // Debug: Confirm legend creation

                // Add filters
                document.getElementById('filter-mutual').addEventListener('change', function() {
                    const checked = this.checked;
                    svg.selectAll('.mutual').style('display', checked ? 'inline' : 'none');
                });

                document.getElementById('filter-interest').addEventListener('change', function() {
                    const checked = this.checked;
                    svg.selectAll('.interest').style('display', checked ? 'inline' : 'none');
                });

                document.getElementById('filter-both').addEventListener('change', function() {
                    const checked = this.checked;
                    svg.selectAll('.both').style('display', checked ? 'inline' : 'none');
                });
            })
            .catch(error => console.error('Error fetching FOAF graph data:', error));
    }

    // Call the loadGraph function to render the graph
    loadGraph();
});
