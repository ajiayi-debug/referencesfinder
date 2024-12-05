// Processing.jsx or Processing.js
import React, { useState } from "react";
import {
  FaCheckCircle,
  FaSpinner,
  FaTimesCircle,
  FaChevronRight,
} from "react-icons/fa";
import { useNavigate } from "react-router-dom";

function Processing() {
  const [isLoading, setIsLoading] = useState(false);
  const [steps, setSteps] = useState([
    { name: "Embed & Chunk Existing", status: "pending", time: null },
    { name: "Evaluate Existing References", status: "pending", time: null },
    { name: "Clean Existing References", status: "pending", time: null },
    { name: "Search New References", status: "pending", time: null },
    { name: "Embed & Chunk New References", status: "pending", time: null },
    { name: "Evaluate New References", status: "pending", time: null },
    { name: "Clean New References", status: "pending", time: null },
    { name: "Agentic Search", status: "pending", time: null },
    { name: "Expert Presentation", status: "pending", time: null },
  ]);
  const [totalTime, setTotalTime] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const navigate = useNavigate();

  const updateStepStatus = (index, status, stepTime = null) => {
    setSteps((prevSteps) =>
      prevSteps.map((step, i) =>
        i === index ? { ...step, status, time: stepTime } : step
      )
    );
  };

  const handleProcess = async () => {
    setIsLoading(true);
    setTotalTime(null);
    setErrorMessage(null);
    setStartTime(Date.now());

    let allCompleted = true; // Flag to track overall success

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      updateStepStatus(i, "in-progress");

      const stepStartTime = Date.now();

      try {
        let response;
        switch (step.name) {
          case "Embed & Chunk Existing":
            response = await fetch("http://127.0.0.1:8000/embedandchunkexisting", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          case "Evaluate Existing References":
            response = await fetch("http://127.0.0.1:8000/evaluateexisting", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          case "Clean Existing References":
            response = await fetch("http://127.0.0.1:8000/cleanexisting", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          case "Search New References":
            response = await fetch("http://127.0.0.1:8000/search", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          case "Embed & Chunk New References":
            response = await fetch("http://127.0.0.1:8000/embedandchunknew", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          case "Evaluate New References":
            response = await fetch("http://127.0.0.1:8000/evaluatenew", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          case "Clean New References":
            response = await fetch("http://127.0.0.1:8000/cleannew", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          case "Agentic Search":
            response = await fetch("http://127.0.0.1:8000/agenticsearch", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          case "Expert Presentation":
            response = await fetch("http://127.0.0.1:8000/expertpresentation", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ /* any necessary data */ }),
            });
            break;
          default:
            throw new Error(`Unknown step: ${step.name}`);
        }

        if (!response.ok) {
          throw new Error(`Failed at step: ${step.name}`);
        }

        // Optionally handle response data
        const result = await response.json();
        console.log(`${step.name} Result:`, result);

        const stepEndTime = Date.now();
        const stepDuration = ((stepEndTime - stepStartTime) / 1000).toFixed(2); // in seconds

        updateStepStatus(i, "completed", stepDuration);
      } catch (error) {
        console.error(`Error during ${step.name}:`, error);
        updateStepStatus(i, "failed");
        setErrorMessage(error.message);
        allCompleted = false; // Mark that not all steps were successful
        break; // Stop the process on failure
      }
    }

    const endTime = Date.now();
    const totalDuration = ((endTime - startTime) / 1000).toFixed(2); // in seconds
    setTotalTime(totalDuration);
    setIsLoading(false);

    if (allCompleted) {
      navigate("/select"); // Navigate to /select
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <FaCheckCircle className="text-green-500" size={20} />;
      case "failed":
        return <FaTimesCircle className="text-red-500" size={20} />;
      case "in-progress":
        return <FaSpinner className="text-blue-500 animate-spin" size={20} />;
      default:
        return <FaChevronRight className="text-gray-400" size={20} />;
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case "completed":
        return "Completed";
      case "failed":
        return "Failed";
      case "in-progress":
        return "In Progress";
      default:
        return "Pending";
    }
  };

  // Calculate overall progress percentage
  const completedSteps = steps.filter(
    (step) => step.status === "completed"
  ).length;
  const progressPercentage =
    (completedSteps / steps.length) * 100;

  return (
    <div className="bg-gray-50 min-h-screen flex justify-center items-center px-4 py-8">
      <div className="bg-white shadow-xl rounded-2xl p-8 w-full max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-semibold text-gray-800 text-center mb-2">
            Workflow Processing
          </h1>
          <p className="text-gray-600 text-center">
            Click the "Start Processing" button to begin the reference processing workflow.
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className="bg-indigo-600 h-4 rounded-full"
              style={{ width: `${progressPercentage}%` }}
            ></div>
          </div>
          <div className="text-right text-sm text-gray-600 mt-1">
            {completedSteps} / {steps.length} Steps Completed
          </div>
        </div>

        {/* Steps Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full table-auto">
            <thead>
              <tr>
                <th className="px-4 py-2 text-left">Step</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Time Taken (sec)</th>
              </tr>
            </thead>
            <tbody>
              {steps.map((step, index) => (
                <tr
                  key={index}
                  className={`border-t ${
                    index % 2 === 0 ? "bg-white" : "bg-gray-50"
                  }`}
                >
                  <td className="px-4 py-2 flex items-center">
                    <span className="mr-2">{getStatusIcon(step.status)}</span>
                    {step.name}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        step.status === "completed"
                          ? "bg-green-100 text-green-800"
                          : step.status === "failed"
                          ? "bg-red-100 text-red-800"
                          : step.status === "in-progress"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {getStatusText(step.status)}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {step.time ? step.time : "--"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Error Message */}
        {errorMessage && (
          <div className="mt-6 p-4 bg-red-100 text-red-700 rounded-lg">
            {errorMessage}
          </div>
        )}

        {/* Total Time */}
        {totalTime && (
          <div className="mt-4 text-center text-gray-700">
            Total Time Taken: {totalTime} sec
          </div>
        )}

        {/* Start Button */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={handleProcess}
            disabled={isLoading}
            className={`flex items-center justify-center bg-indigo-600 text-white py-2 px-6 rounded-lg hover:bg-indigo-700 transition duration-200 ${
              isLoading ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            {isLoading && (
              <FaSpinner className="animate-spin mr-2" />
            )}
            {isLoading ? "Processing..." : "Start Processing"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Processing;


