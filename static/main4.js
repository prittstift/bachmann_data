
// Load the data
queue()
    .defer(d3.csv, "static/autorinnen.csv")
    .await(compileData);

function compileData(error, autorData) {
    // Make sure no error loading data
    if (error){
        return console.log(error);
    }

    // 347 albums
    // {albumID, title, artistID}
    console.log("author data", autorData);

    // Iterate through the albums and count the occurences of an artistID
    // it's an array of {key, value}, 204 items
    let countByWohnort = d3.nest()
        .key(function(datum) {
          if (datum.wohnort.includes(",")) {
            l = datum.wohnort.split(",")
            return l[0], l[1]}
          else {return datum.wohnort}
          })
        .rollup(function(leaves) {
            return leaves.length
        }) // the leaves are an array full of the objects with the corresponding key
        .entries(autorData);

    // Sort the data in ascending order
    countByWohnort.sort(function(a,b) {
       return a.value - b.value;
    });

    // Now that the data has laoded, we can make the visualization
    createVis("chart-display-col", countByWohnort, autorData);


}

function createVis(parentElement, countData, autorData) {
    // Configure margins
    let margin = { top: 20, right: 20, bottom: 90, left: 30 };

    // Cofigure height and width of the visualization
    let width = $("#" + parentElement).width() - margin.left - margin.right,
        height = $("#" + parentElement).height() - margin.top - margin.bottom;

    // SVG drawing area
    let svg = d3.select("#" + parentElement).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    // Create scales
    // Use ordinal scale since the x axis isn't numerical
    let xOrdinalScale = d3.scaleBand()
        .rangeRound([0, width])
        .padding(.1)
        .domain(countData.map(function(datum){return datum.key}));

    let yScale = d3.scaleLinear()
        .range([height - margin.bottom, margin.top]) // we could also set this to height and 0, but would need to translate axis
        .domain([0, d3.max(countData, function(datum){ return datum.value})]);

    // Now set up the axis
    let barYAxis = d3.axisLeft()
        .scale(yScale);

    let barXAxis = d3.axisBottom()
        .scale(xOrdinalScale);


    // Append the axes to the svg
    let barYAxisGroup = svg.append("g")
        .attr("class", "axis bar-y-axis")
        .call(barYAxis);

    let barXAxisGroup = svg.append("g")
        .attr("class", "axis bar-x-axis")
        .attr("transform", "translate(0," + (height - margin.bottom) + ")")
        .call(barXAxis)
        .selectAll("text")
        .attr("y", 0)
        .attr("x", 9)
        .attr("dy", ".35em")
        .attr("transform", "rotate(90)") // allows us to rotate the text
        .style("text-anchor", "start");

    // Draw the bars
    let bars = svg.selectAll("rect")
        .data(countData)
        .enter()
        .append("rect")
        .attr("class","count-bar")
        .attr("fill","lightblue")
        .attr("width", xOrdinalScale.bandwidth())
        .attr("height", function(datum) {
            return yScale(0) - yScale(datum.value);
        })
        .attr("y", function(datum){
            return yScale(datum.value);
        })
        .attr("x", function(datum){
            return xOrdinalScale(datum.key);
        })
        .on("click", function(datum){
            getAutorInfo(datum.key, autorData);
        });

}

function getAutorInfo(wohnortname, autorData){
    // Get artist name
    document.querySelector("#wohnort-span").innerHTML = wohnortname;


    // Construct list of albums for that artist
    let ul_list = "<table class=\"table table-striped\"><thead><tr><th scope=\"col\">Autor</th><th scope=\"col\">Preis</th><th scope=\"col\">Jahr</th><th scope=\"col\">*</th></tr></thead><tbody>";
  autorData.forEach(function(autor){
        if (autor.wohnort.includes(wohnortname)  && autor.preis_gewonnen === "True") {
          ul_list += "<tr><td>" + autor.autorinnenname +  "</td><td>" +  autor.preis +  "</td><td>" +  autor.teilnahmejahr + "</td><td><a class=\"btn btn-primary\" href=\"/text/" + autor.id + "\" role=\"button\">Details</a></tr>";
        }
    })
    ul_list += "</tbody></table>";

    // Put that html string into the dom
    document.querySelector("#autorinnen").innerHTML = ul_list;

}
