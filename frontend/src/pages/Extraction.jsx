// Extraction.jsx
import React, { useState, useEffect } from "react";
import axios from "axios";
import Highlighter from 'react-highlight-words';
import ClipLoader from "react-spinners/ClipLoader";
import _ from 'lodash';
import { v4 as uuidv4 } from 'uuid'; 
import { useNavigate } from 'react-router-dom';

function Extraction() {
  // Existing state variables
  const [content, setContent] = useState(''); // Extracted text content
  const [phrasesToHighlight, setPhrasesToHighlight] = useState([]); // Phrases to highlight
  const [fileData, setFileData] = useState(null); // Uploaded file data
  const [file, setFile] = useState(null); // Selected main file
  const [data, setData] = useState([]); // Extracted data from backend
  const [pdfUrl, setPdfUrl] = useState(null); // URL for PDF viewer
  const [loading, setLoading] = useState(false); // Initial upload loading state
  const [regenerating, setRegenerating] = useState(false); // Regeneration loading state
  const [pdfLoading, setPdfLoading] = useState(false); // PDF loading state
  const [errorMessage, setErrorMessage] = useState(""); // Error messages
  const [isDeleteMode, setIsDeleteMode] = useState(false); // Delete mode state
  const [saving, setSaving] = useState(false); // Saving state
  const navigate = useNavigate();

  // New state variables for Upload References
  const [referenceFiles, setReferenceFiles] = useState([]); // Selected reference files
  const [referencesLoading, setReferencesLoading] = useState(false); // Loading state for references upload
  const [referencesErrorMessage, setReferencesErrorMessage] = useState(""); // Error messages for references
  const [referencesSuccessMessage, setReferencesSuccessMessage] = useState(""); // Success message for references
  const [referencesUploaded, setReferencesUploaded] = useState(false); // Flag to indicate references have been uploaded

  // Handle main file selection
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type !== 'application/pdf') {
      setErrorMessage("Only PDF files are allowed.");
      setFile(null);
      return;
    }
    setFile(selectedFile);
    setErrorMessage("");
    setPhrasesToHighlight([]);
    setContent('');
    // Optionally reset fileData if a new file is selected before processing
    if (fileData) {
      setFileData(null);
      setPdfUrl(null);
      setData([]);
    }
  };

  // Handle reference files selection (updated)
  const handleReferencesFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    const invalidFiles = selectedFiles.filter(file => file.type !== 'application/pdf');
    if (invalidFiles.length > 0) {
      setReferencesErrorMessage("Only PDF files are allowed for references.");
      setReferenceFiles([]);
      return;
    }
    setReferenceFiles(selectedFiles);
    setReferencesErrorMessage("");
    setReferencesSuccessMessage("");
    // Reset referencesUploaded flag when new files are selected
    setReferencesUploaded(false);
  };

  // Upload References
  const handleUploadReferences = async () => {
    if (referenceFiles.length === 0) {
      setReferencesErrorMessage("Please select at least one PDF file to upload as references.");
      return;
    }
    setReferencesLoading(true);
    setReferencesErrorMessage("");
    setReferencesSuccessMessage("");

    const formData = new FormData();
    referenceFiles.forEach((file) => {
      formData.append("files", file); // 'files' matches the backend parameter
    });

    try {
      const response = await axios.post("http://localhost:8000/upload-references/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      console.log("Upload References Response:", response.data);
      setReferencesSuccessMessage("References uploaded successfully!");
      setReferenceFiles([]);
      setReferencesUploaded(true);
    } catch (error) {
      console.error("Upload References failed:", error);
      setReferencesErrorMessage(error.response?.data?.detail || error.message || "An error occurred during references upload.");
    } finally {
      setReferencesLoading(false);
    }
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
    if (!referencesUploaded) {
      setErrorMessage("Please upload reference PDFs before processing the main article.");
      return;
    }
    setLoading(true); // Start initial upload loading
    setErrorMessage("");
    setPhrasesToHighlight([]);
    setContent('');

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Step 1: Upload the main file
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
      const subpath = 'extracted.txt'; // Adjust based on your backend's file storage structure
      const text = await fetchFileContent(subpath);
      setContent(text.replace(/\n/g, ' '));

      // Step 4: Fetch all extracted data (e.g., statements, metadata, etc.)
      const extractionResponse = await axios.get("http://localhost:8000/extraction/");
      console.log("Extraction Data Response:", extractionResponse.data);

      // Assign unique IDs to each data item
      const extractedDataWithIds = (extractionResponse.data || []).map(item => ({
        ...item,
        id: item.id || uuidv4(), // Use existing ID or generate a new one
      }));
      setData(extractedDataWithIds);
      console.log("Set data to:", extractedDataWithIds);

      // Step 5: Prepare payload for matching
      const payload = {
        subpath: subpath, // Relative path to the uploaded file
      };

      // Step 6: Perform matching by calling the /match/ endpoint
      const matchResponse = await axios.post("http://localhost:8000/match/", payload);
      const matches = matchResponse.data.matches;
      console.log("Matches:", matches);

      // Step 7: Update highlight phrases with matches
      // Remove duplicates and empty strings
      const uniquePhrases = _.uniq(matches.filter(phrase => phrase && phrase.trim() !== ""));
      const cleanedPhrases = uniquePhrases.map(phrase => phrase.replace(/\n/g, ' '));
      setPhrasesToHighlight(cleanedPhrases);

      // Step 8: Update fileData state
      setFileData({
        text_content: text || '',
        filename: filename,
      });

    } catch (error) {
      console.error("Upload or extraction failed:", error);
      setErrorMessage(error.response?.data?.detail || error.message || "An error occurred during upload or extraction.");
    } finally {
      setLoading(false); // End initial upload loading
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
    if (saving) return; // Prevent multiple saves
    setSaving(true); // Start saving
    setErrorMessage("");
    try {
      await axios.put("http://localhost:8000/extraction/", data);
      alert("Data saved successfully!");
      navigate('/processing');
    } catch (error) {
      console.error("Error saving data:", error);
      setErrorMessage("Error saving data.");
    } finally {
      setSaving(false); // End saving
    }
  };
  

  // Handle input changes in the extracted data table
  const handleInputChange = (index, field, value) => {
    const updatedData = [...data];
    updatedData[index][field] = value;
    setData(updatedData);
  };

  // Handle adding a new data row
  const handleAddData = () => {
    const newRow = {
      id: uuidv4(), // Generate a unique ID for the new row
      referenceArticleName: "",
      referenceTextInMainArticle: "",
      date: "",
      nameOfAuthors: "",
    };
    setData([...data, newRow]);
  };

  // Handle deleting a data row
  const handleDeleteRow = (id) => {
    const updatedData = data.filter(item => item.id !== id);
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

  // Handle Regenerate action
  const handleRegenerate = async () => {
    if (!file) {
      setErrorMessage("No file available to regenerate.");
      return;
    }
    if (!referencesUploaded) {
      setErrorMessage("Please upload reference PDFs before regenerating.");
      return;
    }
    setRegenerating(true); // Start regeneration loading
    setErrorMessage("");
    setPhrasesToHighlight([]);
    setContent('');
    setData([]);

    try {
      // Re-upload and re-process the file
      const formData = new FormData();
      formData.append("file", file);

      // Step 1: Upload the file again
      const uploadResponse = await axios.post("http://localhost:8000/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      console.log("Regenerate Upload Response:", uploadResponse.data);

      const filename = uploadResponse.data.filename;
      if (!filename) {
        throw new Error("Filename not returned from upload endpoint.");
      }

      // Step 2: Trigger the extraction process
      const extractResponse = await axios.post("http://localhost:8000/extractdata/");
      console.log("Regenerate Extract Response:", extractResponse.data);

      // Step 3: Fetch the extracted text content from the .txt file using the existing /file/{subpath} endpoint
      const subpath = 'extracted.txt'; // Adjust based on your backend's file storage structure
      const text = await fetchFileContent(subpath);
      setContent(text.replace(/\n/g, ' '));

      // Step 4: Fetch all extracted data (e.g., statements, metadata, etc.)
      const extractionResponse = await axios.get("http://localhost:8000/extraction/");
      console.log("Regenerate Extraction Data Response:", extractionResponse.data);

      const extractedData = extractionResponse.data || [];

      // Assign unique IDs to each data item
      const extractedDataWithIds = extractedData.map(item => ({
        ...item,
        id: item.id || uuidv4(), // Use existing ID or generate a new one
      }));

      setData(extractedDataWithIds);
      console.log("Set data to:", extractedDataWithIds);

      // Step 5: Prepare payload for matching
      const payload = {
        subpath: subpath, // Relative path to the uploaded file
      };

      // Step 6: Perform matching by calling the /match/ endpoint
      const matchResponse = await axios.post("http://localhost:8000/match/", payload);
      const matches = matchResponse.data.matches;
      console.log("Regenerate Matches:", matches);

      // Step 7: Update highlight phrases with matches
      // Remove duplicates and empty strings
      const uniquePhrases = _.uniq(matches.filter(phrase => phrase && phrase.trim() !== ""));
      const cleanedPhrases = uniquePhrases.map(phrase => phrase.replace(/\n/g, ' '));
      setPhrasesToHighlight(cleanedPhrases);

      // Step 8: Update fileData state
      setFileData({
        text_content: text || '',
        filename: filename,
      });

    } catch (error) {
      console.error("Regenerate upload or extraction failed:", error);
      setErrorMessage(error.response?.data?.detail || error.message || "An error occurred during regeneration.");
    } finally {
      setRegenerating(false); // End regeneration loading
    }
  };

  // Toggle Delete Mode
  const toggleDeleteMode = () => {
    setIsDeleteMode(!isDeleteMode);
  };

  return (
    <div className="bg-gray-100 min-h-screen flex justify-center items-center p-4">
      <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-6xl">
        <h1 className="text-3xl font-bold text-gray-700 text-center mb-4">
          Welcome to ReferenceFinder
        </h1>
        <p className="text-gray-500 text-center mb-8">
          Easily upload your articles for automated updates using Generative AI.
        </p>

        {/* Upload References Section */}
        {!fileData && (
          <div className="flex flex-col items-center mb-8">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4 text-center">Upload References</h2>
            <div className="flex flex-col sm:flex-row sm:items-center justify-center">
              <label
                className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-2 px-4 rounded-lg shadow-lg text-lg"
                htmlFor="references-upload"
              >
                Select Reference PDFs or Folder
              </label>
              <input
                id="references-upload"
                type="file"
                accept=".pdf"
                multiple
                webkitdirectory="" // Allows folder selection in supported browsers
                directory="" // For cross-browser compatibility
                onChange={handleReferencesFileChange}
                className="hidden"
              />
              {referenceFiles.length > 0 && (
                <div className="mt-4 sm:mt-0 sm:ml-4 flex flex-row items-center space-x-2">
                  <p className="text-gray-700">{referenceFiles.length} file(s) selected</p>
                  <button
                    onClick={handleUploadReferences}
                    className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded-lg shadow-lg text-lg"
                    disabled={referencesLoading}
                  >
                    {referencesLoading ? "Uploading..." : "Upload References"}
                  </button>
                </div>
              )}
            </div>
            {referencesLoading && <ClipLoader size={30} color={"#123abc"} className="mt-4" />}
            {referencesErrorMessage && (
              <p className="text-red-500 mt-4 text-center">{referencesErrorMessage}</p>
            )}
            {referencesSuccessMessage && (
              <p className="text-green-500 mt-4 text-center">{referencesSuccessMessage}</p>
            )}
          </div>
        )}

        {/* Main Upload Section */}
        {!fileData && (
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
            {file && referencesUploaded && (
              <button
                onClick={handleUpload}
                className="mt-6 bg-green-500 hover:bg-green-600 text-white font-bold py-4 px-8 rounded-lg shadow-lg text-lg"
                disabled={loading}
              >
                {loading ? "Processing..." : "Process PDF"}
              </button>
            )}
            {file && !referencesUploaded && (
              <p className="text-gray-500 mt-4">Please upload references to process the PDF.</p>
            )}
            {loading && <ClipLoader size={50} color={"#123abc"} className="mt-4" />}
            {errorMessage && (
              <p className="text-red-500 mt-4">{errorMessage}</p>
            )}
          </div>
        )}

        {/* Display PDF Viewer and Extracted Data after processing */}
        {fileData && (
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
                />
              </div>
            </div>

            {/* Extracted Data Table */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-700">
                Extracted Data {data.length > 0 && <span className="text-sm text-gray-500">({data.length} rows)</span>}
              </h2>
              {regenerating ? (
                <div className="flex justify-center items-center h-48">
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
                        {isDeleteMode && (
                          <th className="border px-4 py-2 text-gray-600">Actions</th> // Conditionally render Actions column
                        )}
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
                          {isDeleteMode && (
                            <td className="border px-4 py-2 text-center">
                              <button
                                onClick={() => handleDeleteRow(item.id)}
                                className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded"
                              >
                                Delete
                              </button>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>No data extracted.</p>
              )}


              <div className="flex flex-col sm:flex-row sm:justify-between items-center mt-4">
              <button
                onClick={handleSave}
                className={`bg-blue-500 hover:bg-blue-600 text-white font-bold py-4 px-8 rounded-lg text-lg flex items-center ${saving ? "opacity-50 cursor-not-allowed" : ""}`}
                disabled={saving}
              >
                {saving ? (
                  <>
                    <ClipLoader size={20} color={"#ffffff"} className="mr-2" />
                    Saving...
                  </>
                ) : (
                  "Save Changes"
                )}
              </button>
                <div className="flex flex-col sm:flex-row sm:items-center">
                  <button
                    onClick={handleAddData}
                    className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded-lg text-md sm:mr-4 mb-2 sm:mb-0"
                  >
                    Add Data
                  </button>
                  <button
                    onClick={handleRegenerate}
                    className="bg-purple-500 hover:bg-purple-600 text-white font-bold py-4 px-8 rounded-lg text-lg"
                    disabled={regenerating}
                  >
                    {regenerating ? "Regenerating..." : "Regenerate"}
                  </button>
                </div>
              </div>
              {/* Delete Mode Toggle Button */}
              <div className="flex justify-end mt-4">
                <button
                  onClick={toggleDeleteMode}
                  className={`${
                    isDeleteMode ? "bg-gray-500 hover:bg-gray-600" : "bg-red-500 hover:bg-red-600"
                  } text-white font-bold py-2 px-4 rounded-lg text-md`}
                >
                  {isDeleteMode ? "Cancel Delete" : "Delete Rows"}
                </button>
              </div>
              {errorMessage && (
                <p className="text-red-500 mt-4">{errorMessage}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Extraction;


