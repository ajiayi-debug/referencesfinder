import React, { useState } from 'react';

function Udecide() {
  const [view, setView] = useState("sieved");
  const [statementIndex, setStatementIndex] = useState(0);
  const [replaceMode, setReplaceMode] = useState(false);
  const [editMode, setEditMode] = useState(null);
  const [additions, setAdditions] = useState({});

  const data = [
    {
      statement: "Statement 1",
      oldReferences: [
        {
          id: 1,
          articleName: "Old Article A",
          date: 2021,
          sieved: ["Sieved data row 1 for Old Reference A", "Sieved data row 2 for Old Reference A"],
          chunk: ["Chunk data row 1 for Old Reference A"],
          summary: "This is a summary of Old Reference A for Statement 1.",
        },
        {
          id: 2,
          articleName: "Old Article C",
          date: 2020,
          sieved: ["Sieved data row 1 for Old Reference C", "Sieved data row 2 for Old Reference C", "Sieved data row 3 for Old Reference C"],
          chunk: ["Chunk data row 1 for Old Reference C"],
          summary: "This is a summary of Old Reference C for Statement 1.",
        },
      ],
      newReferences: [
        {
          id: 3,
          articleName: "New Article B",
          date: 2022,
          authors: "Author B",
          sentiment: "neutral",
          sieved: ["Sieved data row 1 for New Reference B", "Sieved data row 2 for New Reference B"],
          chunk: ["Chunk data row 1 for New Reference B", "Chunk data row 2 for New Reference B"],
          summary: "This is a summary of New Reference B for Statement 1.",
        },
      ],
    },
    {
      statement: "Statement 2",
      oldReferences: [
        {
          id: 4,
          articleName: "Old Article D",
          date: 2019,
          sieved: ["Sieved data row 1 for Old Reference D"],
          chunk: ["Chunk data row 1 for Old Reference D"],
          summary: "This is a summary of Old Reference D for Statement 2.",
        }
      ],
      newReferences: [
        {
          id: 5,
          articleName: "New Article E",
          date: 2021,
          authors: "Author E",
          sentiment: "positive",
          sieved: ["Sieved data row 1 for New Reference E", "Sieved data row 2 for New Reference E"],
          chunk: ["Chunk data row 1 for New Reference E"],
          summary: "This is a summary of New Reference E for Statement 2.",
        },
      ],
    },
  ];

  const currentData = data[statementIndex];

  const handleToggleView = (newView) => {
    setView(newView);
  };

  const handleNextStatement = () => {
    setStatementIndex((prevIndex) => (prevIndex + 1) % data.length);
  };

  const handlePreviousStatement = () => {
    setStatementIndex((prevIndex) => (prevIndex - 1 + data.length) % data.length);
  };

  const handleReplaceClick = () => {
    setReplaceMode(!replaceMode);
  };

  const handleEditClick = (id) => {
    setEditMode(editMode === id ? null : id); // Toggle edit mode for each reference
  };

  const handleAdditionsChange = (id, text) => {
    setAdditions(prev => ({ ...prev, [id]: text }));
  };

  // Render sieved or chunk data as a table
  const renderTable = (title, dataRows) => (
    <div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full border border-gray-300">
          <thead>
            <tr>
              <th className="px-4 py-2 border-b border-gray-300 bg-gray-100 text-left">Data</th>
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, index) => (
              <tr key={index}>
                <td className="px-4 py-2 border-b border-gray-200">{row}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="p-8 text-center">
      <h1 className="text-2xl font-bold mb-6">Statement Comparison</h1>

      {/* Slider for Statement */}
      <div className="flex justify-center items-center mb-6 gap-4">
        <button
          onClick={handlePreviousStatement}
          className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          Previous
        </button>
        <span className="text-lg font-medium">{currentData.statement}</span>
        <button
          onClick={handleNextStatement}
          className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          Next
        </button>
      </div>

      {/* View Toggle Buttons */}
      <div className="flex justify-center gap-4 mb-8">
        <button onClick={() => handleToggleView("sieved")} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Sieved
        </button>
        <button onClick={() => handleToggleView("chunk")} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Chunk
        </button>
        <button onClick={() => handleToggleView("summary")} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Summary
        </button>
      </div>

      {/* References Side-by-Side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Old References */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Old Reference(s)</h2>
          {currentData.oldReferences.map((ref, index) => (
            <div key={ref.id} className="mb-6">
              {replaceMode && (
                <div className="flex items-center mb-2">
                  <input 
                    type="checkbox" 
                    id={`replace-${ref.id}`} 
                    className="mr-2"
                  />
                  <label htmlFor={`replace-${ref.id}`} className="text-left">Select for Replacement</label>
                </div>
              )}
              <p><strong>Article:</strong> {ref.articleName}</p>
              <p><strong>Date:</strong> {ref.date}</p>
              {view === "summary" && <p className="mt-4"><strong>Summary:</strong> {ref.summary}</p>}
              {view === "sieved" && renderTable("Sieved Data", ref.sieved)}
              {view === "chunk" && renderTable("Chunk Data", ref.chunk)}
            </div>
          ))}
        </div>

        {/* New References */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">New Reference(s)</h2>
          {currentData.newReferences.map((ref, index) => (
            <div key={ref.id} className="mb-6">
              <p><strong>Article:</strong> {ref.articleName}</p>
              <p><strong>Date:</strong> {ref.date}</p>
              <p><strong>Authors:</strong> {ref.authors}</p>
              <p><strong>Sentiment:</strong> {ref.sentiment}</p>
              {view === "summary" && <p className="mt-4"><strong>Summary:</strong> {ref.summary}</p>}
              {view === "sieved" && renderTable("Sieved Data", ref.sieved)}
              {view === "chunk" && renderTable("Chunk Data", ref.chunk)}
              
              {/* Action Buttons */}
              <div className="flex gap-2 mt-4">
                <button 
                  onClick={handleReplaceClick} 
                  className={`px-4 py-2 ${replaceMode ? 'bg-yellow-700' : 'bg-yellow-500'} text-white rounded hover:bg-yellow-600`}
                >
                  Replace
                </button>
                <button 
                  onClick={() => handleEditClick(ref.id)} 
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Edit
                </button>
                <button 
                  className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                >
                  Add
                </button>
              </div>

              {/* Show Additions textbox in Edit mode */}
              {editMode === ref.id && (
                <div className="mt-4">
                  <label htmlFor={`additions-${ref.id}`} className="block text-left font-semibold mb-2">Additions:</label>
                  <textarea
                    id={`additions-${ref.id}`}
                    value={additions[ref.id] || ""}
                    onChange={(e) => handleAdditionsChange(ref.id, e.target.value)}
                    className="w-full border border-gray-300 rounded p-2"
                    placeholder="Type your additions here..."
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Udecide;
