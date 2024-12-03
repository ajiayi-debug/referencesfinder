import React, { useState, useEffect } from "react";
import axios from "axios";
import Highlighter from 'react-highlight-words';
import ClipLoader from "react-spinners/ClipLoader";
import _ from 'lodash';

function Extraction() {
  const [content, setContent] = useState(''); // Extracted text content
  const [phrasesToHighlight, setPhrasesToHighlight] = useState([]); // Phrases to highlight
  const [fileData, setFileData] = useState(null); // Uploaded file data
  const [file, setFile] = useState(null); // Selected file
  const [data, setData] = useState([]); // Extracted data from backend
  const [pdfUrl, setPdfUrl] = useState(null); // URL for PDF viewer
  const [loading, setLoading] = useState(false); // General loading state
  const [pdfLoading, setPdfLoading] = useState(false); // PDF loading state
  const [dataLoading, setDataLoading] = useState(false); // Data loading state
  const [errorMessage, setErrorMessage] = useState(""); // Error messages
  const [matchedData, setMatchedData] = useState([]); // Matched results from MongoDB

  // Function to normalize text (optional, can be customized)
  const normalizeText = (text) => {
    return text
      .toLowerCase() // Convert to lowercase
      .replace(/[^\w\s]|_/g, "") // Remove punctuation
      .replace(/\s+/g, " ") // Remove extra whitespace
      .trim(); // Trim leading/trailing whitespace
  };
  
  // Handle file selection
  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setErrorMessage("");
    setMatchedData([]);
    setPhrasesToHighlight([]);
    setContent('');
  };

  // Fetch file content using the existing /file/{subpath} endpoint
  const fetchFileContent = async (subpath) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/file/${subpath}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch file: ${subpath} (Status: ${response.status})`);
      }
      const text = await response.text();
      return text;
    } catch (error) {
      console.error(error);
      return 'Error loading file content.';
    }
  };

  // Handle file upload and subsequent processing
  const handleUpload = async () => {
    if (!file) {
      setErrorMessage("Please select a file to upload.");
      return;
    }
    setLoading(true);
    setErrorMessage("");
    setMatchedData([]);
    setPhrasesToHighlight([]);
    setContent('');

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Step 1: Upload the file
      const uploadResponse = await axios.post("http://localhost:8000/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      console.log("Upload Response:", uploadResponse.data);

      const filename = uploadResponse.data.filename;
      if (!filename) {
        throw new Error("Filename not returned from upload endpoint.");
      }

      // Step 2: Trigger the extraction process
      const extractResponse = await axios.post("http://localhost:8000/extractdata/");
      console.log("Extract Response:", extractResponse.data);

      // Step 3: Fetch the extracted text content from the .txt file using the existing /file/{subpath} endpoint
      const subpath ='extracted.txt'; // Adjust based on your backend's file storage structure
      const text = await fetchFileContent(subpath);
      setContent(text);

      // Step 4: Fetch all extracted data (e.g., statements, metadata, etc.)
      const extractionResponse = await axios.get("http://localhost:8000/extraction/");
      console.log("Extraction Data Response:", extractionResponse.data);

      const extractedData = extractionResponse.data || [];
      setData(extractedData);
      console.log("Set data to:", extractedData);

      // Step 5: Prepare payload for matching
      const payload = {
        subpath: subpath, // Relative path to the uploaded file
      };

      // Step 6: Perform matching by calling the /match/ endpoint
      const matchResponse = await axios.post("http://localhost:8000/match/", payload);
      const matches = matchResponse.data.matches;
      console.log("Matches:", matches);

      // Step 7: Update highlight phrases with matched sentences, dates, authors, and reference names
      const highlightPhrases = [
        ...matches.flatMap(doc => doc.matched_sentences),
        ...matches.flatMap(doc => doc.matched_dates),
        ...matches.flatMap(doc => doc.matched_authors),
        ...matches.flatMap(doc => doc.matched_reference_names),
      ];
      
      // Remove duplicates and empty strings
      const uniquePhrases = _.uniq(highlightPhrases.filter(phrase => phrase && phrase.trim() !== ""));
      setPhrasesToHighlight(uniquePhrases);

      // Step 8: Update matched data for display
      setMatchedData(matches);

      // Step 9: Update fileData state
      setFileData({
        text_content: text || '',
        filename: filename,
      });

    } catch (error) {
      console.error("Upload or extraction failed:", error);
      setErrorMessage(error.response?.data?.detail || error.message || "An error occurred during upload or extraction.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch PDF URL for viewing
  const fetchPdfUrl = async (filename) => {
    setPdfLoading(true);
    try {
      console.log(`Fetching PDF for filename: ${filename}`);
      const response = await axios.get(`http://localhost:8000/pdf/${filename}`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "application/pdf" });
      setPdfUrl(URL.createObjectURL(blob));
      console.log("PDF fetched successfully");
    } catch (error) {
      console.error("Error fetching PDF:", error);
      setErrorMessage("Error fetching PDF.");
    } finally {
      setPdfLoading(false);
    }
  };

  // Save changes to the extracted data back to the backend
  const handleSave = async () => {
    try {
      await axios.put("http://localhost:8000/extraction/", data);
      alert("Data saved successfully!");
    } catch (error) {
      console.error("Error saving data:", error);
      setErrorMessage("Error saving data.");
    }
  };

  // Handle input changes in the extracted data table
  const handleInputChange = (index, field, value) => {
    const updatedData = [...data];
    updatedData[index][field] = value;
    setData(updatedData);
  };

  // Fetch PDF URL when fileData is updated
  useEffect(() => {
    if (fileData && fileData.filename) {
      fetchPdfUrl(fileData.filename);
    }
  }, [fileData]);

  // Optional: Log fileData updates for debugging
  useEffect(() => {
    console.log("fileData updated:", fileData);
  }, [fileData]);

  return (
    <div className="bg-gray-100 min-h-screen flex justify-center items-center">
      <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-6xl">
        <h1 className="text-3xl font-bold text-gray-700 text-center mb-4">
          Welcome to UpdateArticle
        </h1>
        <p className="text-gray-500 text-center mb-8">
          Easily upload your articles for automated updates using Generative AI.
        </p>
        {!fileData ? (
          <div className="flex flex-col items-center">
            <label
              className="cursor-pointer bg-blue-500 hover:bg-blue-600 text-white font-bold py-4 px-6 rounded-lg shadow-lg text-lg"
              htmlFor="file-upload"
            >
              Upload PDF
            </label>
            <input
              id="file-upload"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
            />
            {file && (
              <button
                onClick={handleUpload}
                className="mt-6 bg-green-500 hover:bg-green-600 text-white font-bold py-4 px-8 rounded-lg shadow-lg text-lg"
                disabled={loading}
              >
                {loading ? "Processing..." : "Process PDF"}
              </button>
            )}
            {loading && <ClipLoader size={50} color={"#123abc"} />}
            {errorMessage && (
              <p className="text-red-500 mt-4">{errorMessage}</p>
            )}
          </div>
        ) : (
          <div>
            {/* PDF Viewer Section */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-700">PDF Viewer</h2>
              {pdfLoading ? (
                <div className="flex justify-center items-center">
                  <ClipLoader size={50} color={"#123abc"} />
                </div>
              ) : pdfUrl ? (
                <iframe
                  src={pdfUrl}
                  className="w-full h-96 border rounded-lg"
                  title="PDF Viewer"
                ></iframe>
              ) : (
                <p className="text-gray-500">PDF not available.</p>
              )}
            </div>

            {/* Extracted Text Section with Highlighting */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-700">Extracted Text</h2>
              <div className="w-full h-48 p-4 border rounded-lg bg-gray-50 overflow-y-auto">
                <Highlighter
                  highlightClassName="highlight"
                  searchWords={phrasesToHighlight}
                  textToHighlight={content}
                  autoEscape={true}
                  sanitize={str => str} // Optional: Add sanitization if needed
                />
              </div>
            </div>

            {/* Extracted Data Table */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-700">Extracted Data</h2>
              {dataLoading ? (
                <div className="flex justify-center items-center">
                  <ClipLoader size={50} color={"#123abc"} />
                </div>
              ) : data && data.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="table-auto w-full border-collapse border border-gray-200 shadow-sm rounded-lg">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border px-4 py-2 text-gray-600">Reference Article Name</th>
                        <th className="border px-4 py-2 text-gray-600">Reference Text in Main Article</th>
                        <th className="border px-4 py-2 text-gray-600">Date</th>
                        <th className="border px-4 py-2 text-gray-600">Name of Authors</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.map((item, index) => (
                        <tr key={item.id || index} className="bg-white hover:bg-gray-50">
                          <td className="border px-4 py-2">
                            <input
                              type="text"
                              value={item.referenceArticleName || ""}
                              onChange={(e) =>
                                handleInputChange(index, "referenceArticleName", e.target.value)
                              }
                              className="w-full border rounded-md p-2"
                            />
                          </td>
                          <td className="border px-4 py-2">
                            <input
                              type="text"
                              value={item.referenceTextInMainArticle || ""}
                              onChange={(e) =>
                                handleInputChange(index, "referenceTextInMainArticle", e.target.value)
                              }
                              className="w-full border rounded-md p-2"
                            />
                          </td>
                          <td className="border px-4 py-2">
                            <input
                              type="text"
                              value={item.date || ""}
                              onChange={(e) => handleInputChange(index, "date", e.target.value)}
                              className="w-full border rounded-md p-2"
                            />
                          </td>
                          <td className="border px-4 py-2">
                            <input
                              type="text"
                              value={item.nameOfAuthors || ""}
                              onChange={(e) =>
                                handleInputChange(index, "nameOfAuthors", e.target.value)
                              }
                              className="w-full border rounded-md p-2"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>No data extracted.</p>
              )}
              <button
                onClick={handleSave}
                className="mt-4 bg-blue-500 hover:bg-blue-600 text-white font-bold py-4 px-8 rounded-lg shadow-lg text-lg"
              >
                Save Changes
              </button>
            </div>

            {/* Matched Results Section */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-700">Matched Results</h2>
              {matchedData && matchedData.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="table-auto w-full border-collapse border border-gray-200 shadow-sm rounded-lg">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border px-4 py-2 text-gray-600">Document ID</th>
                        <th className="border px-4 py-2 text-gray-600">Matched Sentences</th>
                        <th className="border px-4 py-2 text-gray-600">Matched Dates</th>
                        <th className="border px-4 py-2 text-gray-600">Matched Authors</th>
                        <th className="border px-4 py-2 text-gray-600">Matched Reference Names</th>
                      </tr>
                    </thead>
                    <tbody>
                      {matchedData.map((item) => (
                        <tr key={item.id} className="bg-white hover:bg-gray-50">
                          <td className="border px-4 py-2">{item.id}</td>
                          <td className="border px-4 py-2">
                            {item.matched_sentences.length > 0 ? (
                              <ul className="list-disc list-inside">
                                {item.matched_sentences.map((sentence, idx) => (
                                  <li key={idx}>{sentence}</li>
                                ))}
                              </ul>
                            ) : (
                              "N/A"
                            )}
                          </td>
                          <td className="border px-4 py-2">
                            {item.matched_dates.length > 0 ? item.matched_dates.join(", ") : "N/A"}
                          </td>
                          <td className="border px-4 py-2">
                            {item.matched_authors.length > 0 ? item.matched_authors.join(", ") : "N/A"}
                          </td>
                          <td className="border px-4 py-2">
                            {item.matched_reference_names.length > 0 ? item.matched_reference_names.join(", ") : "N/A"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>No matches found.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Extraction;

