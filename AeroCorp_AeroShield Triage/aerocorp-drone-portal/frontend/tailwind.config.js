/** Palette taken from aeronautical charts: pale chart-blue paper, navy ink, one magenta route line. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        chart: "#E6EDF2", // page background
        paper: "#F5F8FA", // raised panels and inputs
        ink: "#0F2540", // text and strong lines
        soft: "#46607C", // secondary text
        rule: "#AEBFCE", // hairlines
        route: "#B0125A", // the one accent: flight route, links, primary action
        routedark: "#8A0E47",
        sky: "#1B6AA5", // focus ring
      },
      fontFamily: {
        display: ['"Barlow Condensed"', '"Arial Narrow"', "sans-serif"],
        body: ['"Source Serif 4"', "Georgia", "serif"],
      },
      borderRadius: { DEFAULT: "2px", sm: "2px", md: "3px", lg: "4px" },
      maxWidth: { measure: "64ch" },
    },
  },
  plugins: [],
};
