import React from "react";
import Plot from "react-plotly.js";


const ChartDisplay = ({ chartData, chartType }) => {

    if (!chartData) return null;

    return (
        <div style={{
            background   : "rgba(255,255,255,0.03)",
            border       : "1px solid rgba(255,255,255,0.08)",
            borderRadius : "12px",
            padding      : "16px",
            marginTop    : "12px"
        }}>
            {/* Chart type label */}
            <div style={{
                fontSize     : "11px",
                color        : "#606070",
                textTransform: "uppercase",
                letterSpacing: "1px",
                marginBottom : "12px"
            }}>
                📊 {chartType} chart
            </div>

            <Plot
                data   = {chartData.data}
                layout = {{
                    ...chartData.layout,
                    // Dark theme
                    paper_bgcolor: "rgba(0,0,0,0)",
                    plot_bgcolor : "rgba(0,0,0,0)",
                    font         : { color: "#a0a0b0", family: "Arial" },
                    margin       : { l: 40, r: 20, t: 30, b: 40 },
                    xaxis        : {
                        ...chartData.layout?.xaxis,
                        gridcolor: "rgba(255,255,255,0.05)",
                        color    : "#606070"
                    },
                    yaxis: {
                        ...chartData.layout?.yaxis,
                        gridcolor: "rgba(255,255,255,0.05)",
                        color    : "#606070"
                    }
                }}
                config = {{
                    displayModeBar     : true,    
                    displaylogo        : false,   
                    modeBarButtonsToRemove: ["lasso2d", "select2d"]
                }}
                style  = {{ width: "100%", minHeight: "300px" }}
            />
        </div>
    );
};

export default ChartDisplay;