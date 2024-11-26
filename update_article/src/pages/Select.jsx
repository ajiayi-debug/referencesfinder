import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ClipLoader from 'react-spinners/ClipLoader';
import CardComponent from '../components/CardComponent';

function Select() {
  const [cardDataList, setCardDataList] = useState(null);
  const [selectedCards, setSelectedCards] = useState([]);
  const [globalViewMode, setGlobalViewMode] = useState("summary");
  const [globalOverride, setGlobalOverride] = useState(true);
  const [sentimentFilter, setSentimentFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

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
    if (selectedCards.length === 0) {
      alert("Please select at least one paper before proceeding.");
      return; // Prevent further execution if no papers are selected
    }
    setLoading(true);
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

    fetch('http://127.0.0.1:8000/save_selected_articles', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(selectedArticles)
    })
    .then(response => {
      setLoading(false);
      if (response.ok) {
        navigate("/udecide");
      } else {
        alert("Failed to send selected articles.");
      }
    })
    .catch(error => {
      console.error("Error:", error);
      setLoading(false);
      alert("An error occurred while sending data.");
    });
  };

  const resetSelections = () => {
    setSelectedCards([]);
  };

  const filteredCardDataList = sentimentFilter === "all"
    ? cardDataList
    : cardDataList.filter(card => card.sentiment.toLowerCase() === sentimentFilter);

  if (cardDataList === null) {
    return <div>Loading data...</div>;
  }

  return (
    <div className="max-w-6xl mx-auto p-8 text-center">
      <h1 className="text-2xl font-bold mb-6">Results</h1>

      {/* Loading Spinner */}
      {loading && (
        <div className="fixed inset-0 bg-white bg-opacity-80 flex items-center justify-center z-50">
          <ClipLoader color="#123abc" loading={loading} size={50} />
        </div>
      )}

      <div className="flex flex-wrap justify-center gap-4 mb-6">
        <button onClick={() => setGlobalViewMode("summary")} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Summary
        </button>
        <button onClick={() => setGlobalViewMode("sieving")} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Sieving by GPT-4o
        </button>
        <button onClick={() => setGlobalViewMode("chunk")} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Chunk
        </button>
        <button onClick={() => setGlobalViewMode("both")} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Both
        </button>
        <label className="flex items-center gap-2">
          <input 
            type="checkbox" 
            checked={globalOverride} 
            onChange={() => setGlobalOverride(!globalOverride)} 
            className="h-4 w-4"
          />
          Override All with Global Mode
        </label>
      </div>
      
      <div className="flex flex-wrap justify-center gap-4 mb-6">
        <button onClick={() => setSentimentFilter("all")} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">
          Show All
        </button>
        <button onClick={() => setSentimentFilter("oppose")} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">
          Show Oppose Only
        </button>
        <button onClick={() => setSentimentFilter("support")} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">
          Show Support Only
        </button>
      </div>
      
      <div className="flex justify-center gap-4 mb-8">
        <button 
          onClick={handleSendToBackend} 
          disabled={loading} 
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          Send selected papers to update article
        </button>
        <button 
          onClick={resetSelections} 
          disabled={loading} 
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          Clear All Selections
        </button>
      </div>

      {filteredCardDataList.length === 0 ? (
        <div className="text-gray-500">No data available or loading failed.</div>
      ) : (
        filteredCardDataList.map((data) => (
          <CardComponent
            key={data.id}
            {...data}
            globalViewMode={globalViewMode}
            globalOverride={globalOverride}
            onSelectChange={(isSelected) => handleSelectChange(data.id, isSelected)}
            isReset={selectedCards.length === 0}
          />
        ))
      )}
    </div>
  );
}

export default Select;
