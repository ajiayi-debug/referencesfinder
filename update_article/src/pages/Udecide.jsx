import React, { useState, useEffect } from "react";
import { useNavigate } from 'react-router-dom';
import ClipLoader from 'react-spinners/ClipLoader';

function Udecide() {
  const [data, setData] = useState([]);
  const [view, setView] = useState("sieved");
  const [statementIndex, setStatementIndex] = useState(0);
  const [replaceMode, setReplaceMode] = useState(false);
  const [selectedReplacements, setSelectedReplacements] = useState({});
  const [selectedReplacementNewRefs, setSelectedReplacementNewRefs] = useState({});
  const [selectedAdditions, setSelectedAdditions] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [editMode, setEditMode] = useState(null);
  const [editText, setEditText] = useState({});
  const [finalizeLoading, setFinalizeLoading] = useState(false);
  const [addLoading, setAddLoading] = useState(false);

  const navigate = useNavigate();

  // Fetch data from backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("http://127.0.0.1:8000/joindata");
        const result = await response.json();
        setData(result);
        setIsLoading(false);
      } catch (error) {
        console.error("Error fetching data:", error);
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const currentData = data[statementIndex] || {};

  // Handle statement navigation
  const handleNextStatement = () => {
    setStatementIndex((prevIndex) => (prevIndex + 1) % data.length);
  };

  const handlePreviousStatement = () => {
    setStatementIndex((prevIndex) => (prevIndex - 1 + data.length) % data.length);
  };

  // Replace functionality
  const handleReplaceClick = (refId) => {
    setSelectedReplacements((prev) => ({
      ...prev,
      [refId]: !prev[refId],
    }));
  };

  const handleReplaceNewClick = (refId) => {
    setSelectedReplacementNewRefs((prev) => ({
      ...prev,
      [refId]: !prev[refId],
    }));
  };

  const handleAddReplacementTask = async () => {
    // Gather all selected old references
    const selectedOldRefs = Object.entries(selectedReplacements)
      .filter(([_, isChecked]) => isChecked)
      .map(([oldRefId]) => {
        const oldRefData = currentData.oldReferences.find((ref) => ref.id === oldRefId);
        return {
          id: oldRefId,
          articleName: oldRefData?.articleName || "",
          authors: oldRefData?.authors || [],
          date: oldRefData?.date || "",
        };
      });

    // Gather all selected new references
    const selectedNewRefs = Object.entries(selectedReplacementNewRefs)
      .filter(([_, isChecked]) => isChecked)
      .map(([newRefId]) => {
        const newRefData = currentData.newReferences.find(
          (ref) => ref.id === newRefId || ref.id?.$oid === newRefId // Handle MongoDB `$oid`
        );
        return {
          id: newRefId,
          articleName: newRefData?.articleName || "",
          authors: newRefData?.authors || [],
          date: newRefData?.date || "",
        };
      });

    if (selectedOldRefs.length === 0 || selectedNewRefs.length === 0) {
      alert("Please select at least one old reference and one new reference for replacement.");
      return;
    }

    try {
      // Send the mapping of many-to-many replacements
      const response = await fetch("http://127.0.0.1:8000/addReplacementTask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          statement: currentData.statement,
          oldReferences: selectedOldRefs, // List of old references
          newReferences: selectedNewRefs, // List of new references
        }),
      });

      if (response.ok) {
        alert("Replacement task successfully added!");
        setReplaceMode(false);
        setSelectedReplacements({});
        setSelectedReplacementNewRefs({});
      } else {
        console.error("Failed to add replacement task");
      }
    } catch (error) {
      console.error("Error sending replacement task:", error);
    }
  };

  // Addition functionality
  const handleAddClick = (refId) => {
    setSelectedAdditions((prev) => ({
      ...prev,
      [refId]: !prev[refId],
    }));
  };

  const handleAddAdditionTask = async () => {
    setAddLoading(true); // Start loading
  
    const selectedRefs = Object.entries(selectedAdditions)
      .filter(([_, isChecked]) => isChecked)
      .map(([refId]) => {
        const refData = currentData.newReferences.find(
          (ref) => ref.id === refId || ref.id?.$oid === refId
        );
        return {
          id: refId,
          articleName: refData?.articleName || "",
          authors: refData?.authors || [],
          date: refData?.date || "",
        };
      });
  
    if (selectedRefs.length === 0) {
      alert("No references selected for addition!");
      setAddLoading(false); // Stop loading
      return;
    }
  
    try {
      const response = await fetch("http://127.0.0.1:8000/addAdditionTask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          statement: currentData.statement,
          newReferences: selectedRefs,
        }),
      });
  
      if (response.ok) {
        alert("Addition task successfully added!");
        setSelectedAdditions({}); // Reset selections
      } else {
        console.error("Failed to add addition task");
        alert("Failed to add addition task");
      }
    } catch (error) {
      console.error("Error sending addition task:", error);
      alert("Error sending addition task");
    } finally {
      setAddLoading(false); // Stop loading
    }
  };
  

  // Edit functionality
  const handleEditClick = (statement, newRefId) => {
    setEditMode(editMode === `${statement}-${newRefId}` ? null : `${statement}-${newRefId}`); // Combine statement and newRefId
  };

  const handleEditTextChange = (statement, newRefId, text) => {
    setEditText((prev) => ({ ...prev, [`${statement}-${newRefId}`]: text })); // Key by statement-newRefId
  };

  const handleAddEditTask = async (statement, newRefId) => {
    const editKey = `${statement}-${newRefId}`;
    if (!editText[editKey] || editText[editKey].trim() === "") {
      alert("Please type some text before adding an edit task.");
      return;
    }
  
    const newReference = currentData.newReferences.find((ref) => ref.id === newRefId);
  
    if (!newReference) {
      alert("New reference not found!");
      return;
    }
  
    const payload = {
      statement: statement,
      edits: editText[editKey],
      newReferences: [newReference], // Send as a list
    };
  
    // Log the payload to verify its structure
    console.log("Payload being sent to backend:", payload);
  
    try {
      const response = await fetch("http://127.0.0.1:8000/addEditTask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
  
      if (response.ok) {
        alert("Edit task successfully added!");
        setEditMode(null);
        setEditText((prev) => ({ ...prev, [editKey]: "" }));
      } else {
        const errorData = await response.json();
        console.error("Failed to add edit task:", errorData);
        alert(`Failed to add edit task: ${errorData.detail || "Unknown error."}`);
      }
    } catch (error) {
      console.error("Error sending edit task:", error);
      alert("Error sending edit task.");
    }
  };
  

  const handleFinalizeClick = async () => {
    setFinalizeLoading(true);
    try {
      // Call the first API
      const response = await fetch("http://127.0.0.1:8000/finalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
  
      if (!response.ok) {
        alert("Finalize failed. Please try again.");
        console.error("Failed to finalize");
        return; // Exit early if the first API fails
      }
  
      console.log("First API call succeeded.");
  
      // Optionally, process the response from the first API
      const finalizeResult = await response.json();
      console.log("Finalize response:", finalizeResult);
  
      // Call the second API
      const secondApiResponse = await fetch("http://127.0.0.1:8000/send_finalize_data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Optionally send data in the body of the second API
        body: JSON.stringify({ finalizeResult }), // Replace with actual data if needed
      });
  
      if (!secondApiResponse.ok) {
        alert("Second API call failed. Please try again.");
        console.error("Failed to call the second API");
        return; // Exit early if the second API fails
      }
  
      console.log("Second API call succeeded.");
      const secondApiResult = await secondApiResponse.json();
      console.log("Second API response:", secondApiResult);
  
      // Navigate after successful completion of both API calls
      navigate("/fileviewer");
    } catch (error) {
      console.error("Error during API calls:", error);
      alert("An error occurred during the process.");
    } finally {
      setFinalizeLoading(false); // Stop loading spinner/message
    }
  };
  
  // Spinner for global loading or Finalize processing
  if (isLoading || finalizeLoading) {
    return (
      <div className="fixed inset-0 bg-white bg-opacity-80 flex items-center justify-center z-50">
        <ClipLoader color="#123abc" loading={true} size={50} />
      </div>
    );
  }

  // Render tables
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

  if (isLoading) {
    return <div className="text-center p-8">Loading...</div>;
  }

  // Determine if at least one old and one new reference are selected
  const hasOldSelection = Object.values(selectedReplacements).some((val) => val);
  const hasNewSelection = Object.values(selectedReplacementNewRefs).some((val) => val);

  return (
    <div className="p-8 text-center">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Statement Comparison</h1>
        <div className="flex gap-4">
          <button
            onClick={() => {
              if (!replaceMode) {
                setReplaceMode(true);
              } else {
                handleAddReplacementTask();
              }
            }}
            className={`px-4 py-2 text-white rounded ${
              replaceMode ? "bg-green-500 hover:bg-green-600" : "bg-green-500 hover:bg-green-600"
            }`}
            disabled={replaceMode && (!hasOldSelection || !hasNewSelection)}
          >
            {replaceMode ? "Submit Replacement" : "Replace"}
          </button>
          <button
            onClick={handleAddAdditionTask}
            className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center justify-center ${
              addLoading ? "opacity-50 cursor-not-allowed" : ""
            }`}
            disabled={addLoading || Object.values(selectedAdditions).every((val) => !val)}
          >
            {addLoading ? (
              <ClipLoader color="#fff" loading={true} size={20} />
            ) : (
              "Add Addition Task"
            )}
          </button>
          <button
            onClick={handleFinalizeClick}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
            disabled={finalizeLoading} // Disable Finalize button while loading
          >
            {finalizeLoading ? "Finalizing..." : "Finalize"} {/* Dynamic button text */}
          </button>
        </div>
      </div>
      {/* Add Toggle Buttons */}
      <div className="flex justify-center mb-6">
        <button
          onClick={() => setView("summary")}
          className={`px-4 py-2 mx-2 rounded ${
            view === "summary" ? "bg-blue-500 text-white" : "bg-gray-200 hover:bg-gray-300"
          }`}
        >
          Summary
        </button>
        <button
          onClick={() => setView("sieved")}
          className={`px-4 py-2 mx-2 rounded ${
            view === "sieved" ? "bg-blue-500 text-white" : "bg-gray-200 hover:bg-gray-300"
          }`}
        >
          Sieved
        </button>
        <button
          onClick={() => setView("chunk")}
          className={`px-4 py-2 mx-2 rounded ${
            view === "chunk" ? "bg-blue-500 text-white" : "bg-gray-200 hover:bg-gray-300"
          }`}
        >
          Chunk
        </button>
      </div>

      <div className="flex justify-center items-center mb-6 gap-4">
        <button
          onClick={handlePreviousStatement}
          className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          Previous
        </button>
        <span className="text-lg font-medium">
          {currentData.statement || "No statement available"}
        </span>
        <button
          onClick={handleNextStatement}
          className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          Next
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Old References */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Old Reference(s)</h2>
          {(currentData.oldReferences || []).map((ref) => (
            <div key={ref.id} className="mb-6 border border-black p-4 rounded-md">
              {replaceMode && (
                <div className="flex items-center mb-2">
                  <input
                    type="checkbox"
                    id={`replace-${ref.id}`}
                    className="mr-2"
                    onChange={() => handleReplaceClick(ref.id)}
                  />
                  <label htmlFor={`replace-${ref.id}`} className="text-left">
                    Select for Replacement
                  </label>
                </div>
              )}
              <p>
                <strong>Article:</strong> {ref.articleName}
              </p>
              <p>
                <strong>Date:</strong> {ref.date}
              </p>
              <p>
                <strong>Authors:</strong> {ref.authors}
              </p>
              {view === "summary" && (
                <p>
                  <strong>Summary:</strong> {ref.summary}
                </p>
              )}
              {view === "sieved" && renderTable("Sieved Data", ref.sieved)}
              {view === "chunk" && renderTable("Chunk Data", ref.chunk)}
            </div>
          ))}
        </div>

        {/* New References */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">New Reference(s)</h2>
          {(currentData.newReferences || []).map((ref) => (
            <div key={ref.id} className="mb-6 border border-black p-4 rounded-md">
              {replaceMode && (
                <div className="flex items-center mb-2">
                  <input
                    type="checkbox"
                    id={`replace-new-${ref.id}`}
                    className="mr-2"
                    onChange={() => handleReplaceNewClick(ref.id)}
                  />
                  <label htmlFor={`replace-new-${ref.id}`} className="text-left">
                    Select for Replacement
                  </label>
                </div>
              )}
              <p>
                <strong>Article:</strong> {ref.articleName}
              </p>
              <p>
                <strong>Date:</strong> {ref.date}
              </p>
              <p>
                <strong>Authors:</strong> {ref.authors}
              </p>
              <p>
                <strong>Sentiment:</strong> {ref.sentiment}
              </p>
              {view === "summary" && (
                <p>
                  <strong>Summary:</strong> {ref.summary}
                </p>
              )}
              {view === "sieved" && renderTable("Sieved Data", ref.sieved)}
              {view === "chunk" && renderTable("Chunk Data", ref.chunk)}
              <div className="mt-4 flex gap-4 justify-center">
                <button
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                  onClick={() => handleAddClick(ref.id)}
                >
                  Add
                </button>
                <button
                  className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
                  onClick={() => handleEditClick(currentData.statement, ref.id)} // Pass both parameters
                >
                  Edit
                </button>
                {editMode === `${currentData.statement}-${ref.id}` && ( // Use ref.id
                  <div className="mt-4 flex gap-4 items-center">
                    <input
                      type="text"
                      className="border border-gray-300 p-2 rounded w-full"
                      placeholder="Type your edit here..."
                      value={editText[`${currentData.statement}-${ref.id}`] || ""}
                      onChange={(e) =>
                        handleEditTextChange(currentData.statement, ref.id, e.target.value) // Use ref.id
                      }
                    />
                    <button
                      className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                      onClick={() => handleAddEditTask(currentData.statement, ref.id)} // Use ref.id
                    >
                      Add Edit Task
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Udecide;
