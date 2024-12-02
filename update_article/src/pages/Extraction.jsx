import React, { useState, useEffect } from "react";
import axios from "axios";

function Extraction() {
  const [fileData, setFileData] = useState(null);
  const [file, setFile] = useState(null);
  const [data, setData] = useState([]);
  const [pdfUrl, setPdfUrl] = useState(null);

  // Handle file selection
  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  // Upload and process PDF
  const handleUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8000/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFileData(response.data);
      setData(response.data.extracted_data);
    } catch (error) {
      console.error("Upload failed:", error);
    }
  };

  // Fetch the PDF URL
  const fetchPdfUrl = async (filename) => {
    try {
      const response = await axios.get(`http://localhost:8000/pdf/${filename}`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "application/pdf" });
      setPdfUrl(URL.createObjectURL(blob));
    } catch (error) {
      console.error("Error fetching PDF:", error);
    }
  };

  // Save edited data
  const handleSave = async () => {
    try {
      await axios.put("http://localhost:8000/extraction/", data);
      alert("Data saved successfully!");
    } catch (error) {
      console.error("Error saving data:", error);
    }
  };

  // Handle input changes in the table
  const handleInputChange = (index, field, value) => {
    const updatedData = [...data];
    updatedData[index][field] = value;
    setData(updatedData);
  };

  useEffect(() => {
    if (fileData?.filename) {
      fetchPdfUrl(fileData.filename);
    }
  }, [fileData]);

  return (
    <div className="bg-gray-100 min-h-screen flex justify-center items-center">
      <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-4xl">
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
              >
                Process PDF
              </button>
            )}
          </div>
        ) : (
          <div>
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-700">PDF Viewer</h2>
              {pdfUrl ? (
                <iframe
                  src={pdfUrl}
                  className="w-full h-96 border rounded-lg"
                  title="PDF Viewer"
                ></iframe>
              ) : (
                <p className="text-gray-500">Loading PDF...</p>
              )}
            </div>
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-700">Extracted Text</h2>
              <textarea
                value={fileData.text_content}
                readOnly
                className="w-full h-48 p-4 border rounded-lg bg-gray-50"
              ></textarea>
            </div>
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-700">Extracted Data</h2>
              <table className="table-auto w-full border-collapse border border-gray-200 shadow-sm rounded-lg">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border px-4 py-2 text-gray-600">Statement</th>
                    <th className="border px-4 py-2 text-gray-600">Citation</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((item, index) => (
                    <tr key={item._id || index} className="bg-white hover:bg-gray-50">
                      <td className="border px-4 py-2">
                        <input
                          type="text"
                          value={item.statement}
                          onChange={(e) =>
                            handleInputChange(index, "statement", e.target.value)
                          }
                          className="w-full border rounded-md p-2"
                        />
                      </td>
                      <td className="border px-4 py-2">
                        <input
                          type="text"
                          value={item.citation}
                          onChange={(e) =>
                            handleInputChange(index, "citation", e.target.value)
                          }
                          className="w-full border rounded-md p-2"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button
                onClick={handleSave}
                className="mt-4 bg-blue-500 hover:bg-blue-600 text-white font-bold py-4 px-8 rounded-lg shadow-lg text-lg"
              >
                Save Changes
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Extraction;



