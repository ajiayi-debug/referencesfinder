import React, { useState, useEffect } from 'react';
import CardComponent from './components/CardComponent';

function App() {
  const [cardDataList, setCardDataList] = useState(null);
  const [selectedCards, setSelectedCards] = useState([]);
  const [globalViewMode, setGlobalViewMode] = useState("summary");
  const [globalOverride, setGlobalOverride] = useState(true);
  const [sentimentFilter, setSentimentFilter] = useState("all");

  useEffect(() => {
    fetch('http://127.0.0.1:8000/data')
      .then(response => response.json())
      .then(data => {
        const transformedData = data.map((item) => ({
          id: item._id,
          statement: item['Reference text in main article'] || "No statement provided",
          articleName: item["Reference article name"] || "No article name",
          date: item['Date'] || "Unknown date",
          authors: item['authors'] || "Unknown authors",
          sentiment: item['Sentiment'] || "Neutral",
          rating: item['score'] || "N/A",
          summary: item['Summary'] || "No summary available",
          sievingByGPT4o: item["Sieving by gpt 4o"] || [],
          chunk: item['Chunk'] || []
        }));
        setCardDataList(transformedData);
      })
      .catch(error => {
        console.error("Error fetching data:", error);
        setCardDataList([]);
      });
  }, []);

  const handleSelectChange = (id, isSelected) => {
    setSelectedCards(prevSelected => 
      isSelected ? [...prevSelected, id] : prevSelected.filter(cardId => cardId !== id)
    );
  };

  const handleSendToBackend = () => {
    const selectedArticles = cardDataList
      .filter(card => selectedCards.includes(card.id))
      .map(card => ({
        id: card.id,
        statement: card.statement,
        articleName: card.articleName,
        date: card.date,
        authors: card.authors,
        sentiment: card.sentiment,
        rating: card.rating,
        summary: card.summary,
        sievingByGPT4o: card.sievingByGPT4o,
        chunk: card.chunk
      }));

    console.log("Data being sent:", JSON.stringify(selectedArticles, null, 2));

    fetch('http://127.0.0.1:8000/save_selected_articles', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(selectedArticles)
    })
    .then(response => {
      if (response.ok) {
        console.log("Selected articles successfully sent to the backend.");
        alert("Selected articles successfully sent!");
      } else {
        console.error("Failed to send selected articles to the backend.");
        alert("Failed to send selected articles.");
      }
    })
    .catch(error => console.error("Error:", error));
  };

  // Reset function to clear all selected cards
  const resetSelections = () => {
    setSelectedCards([]); // Clear selectedCards state
  };

  const filteredCardDataList = sentimentFilter === "all"
    ? cardDataList
    : cardDataList.filter(card => card.sentiment.toLowerCase() === sentimentFilter);

  if (cardDataList === null) {
    return <div>Loading data...</div>;
  }

  return (
    <div>
      <h1>Results</h1>
      <div className="global-controls">
        <button onClick={() => setGlobalViewMode("summary")}>Summary</button>
        <button onClick={() => setGlobalViewMode("sieving")}>Sieving by GPT-4o</button>
        <button onClick={() => setGlobalViewMode("chunk")}>Chunk</button>
        <button onClick={() => setGlobalViewMode("both")}>Both</button>
        <label>
          <input 
            type="checkbox" 
            checked={globalOverride} 
            onChange={() => setGlobalOverride(!globalOverride)} 
          />
          Override All with Global Mode
        </label>
      </div>
      <div className="sentiment-filter">
        <button onClick={() => setSentimentFilter("all")}>Show All</button>
        <button onClick={() => setSentimentFilter("oppose")}>Show Oppose Only</button>
        <button onClick={() => setSentimentFilter("support")}>Show Support Only</button>
      </div>
      <button onClick={handleSendToBackend}>Send selected papers to update article</button>
      <button onClick={resetSelections}>Clear All Selections</button> {/* New button to reset selections */}

      {filteredCardDataList.length === 0 ? (
        <div>No data available or loading failed.</div>
      ) : (
        filteredCardDataList.map((data) => (
          <CardComponent
            key={data.id}
            {...data}
            globalViewMode={globalViewMode}
            globalOverride={globalOverride}
            onSelectChange={(isSelected) => handleSelectChange(data.id, isSelected)}
            isReset={selectedCards.length === 0} // Pass a reset signal to CardComponent
          />
        ))
      )}
    </div>
  );
}

export default App;
