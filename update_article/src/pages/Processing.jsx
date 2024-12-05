// Processing.jsx
import React, { useState, useEffect } from "react";
import {
  FaCheckCircle,
  FaSpinner,
  FaTimesCircle,
  FaChevronRight,
  FaRedoAlt,
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
  const [totalTime, setTotalTime] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const [email, setEmail] = useState("");
  const [showEmailModal, setShowEmailModal] = useState(false);

  const navigate = useNavigate();

  // Function to update the status and time of a specific step
  const updateStepStatus = (index, status, stepTime = null) => {
    setSteps((prevSteps) =>
      prevSteps.map((step, i) =>
        i === index ? { ...step, status, time: stepTime } : step
      )
    );
  };

  // Main processing function
  const handleProcess = async (userEmail) => {
    setIsLoading(true);
    setErrorMessage(null);

    let allCompleted = true; // Flag to track overall success
    let failureError = null; // To store the error message if any step fails

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];

      // Skip steps that are already completed
      if (step.status === "completed") continue;

      updateStepStatus(i, "in-progress");

      const stepStartTime = Date.now();

      try {
        let response;
        // Determine the endpoint based on the step name
        switch (step.name) {
          case "Embed & Chunk Existing":
            response = await fetch("http://127.0.0.1:8000/embedandchunkexisting", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
            });
            break;
          case "Evaluate Existing References":
            response = await fetch("http://127.0.0.1:8000/evaluateexisting", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
            });
            break;
          case "Clean Existing References":
            response = await fetch("http://127.0.0.1:8000/cleanexisting", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
            });
            break;
          case "Search New References":
            response = await fetch("http://127.0.0.1:8000/search", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
            });
            break;
          case "Embed & Chunk New References":
            response = await fetch("http://127.0.0.1:8000/embedandchunknew", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
            });
            break;
          case "Evaluate New References":
            response = await fetch("http://127.0.0.1:8000/evaluatenew", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
            });
            break;
          case "Clean New References":
            response = await fetch("http://127.0.0.1:8000/cleannew", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
            });
            break;
          case "Agentic Search":
            response = await fetch("http://127.0.0.1:8000/agenticsearch", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
            });
            break;
          case "Expert Presentation":
            response = await fetch("http://127.0.0.1:8000/expertpresentation", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: userEmail }),
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

        updateStepStatus(i, "completed", parseFloat(stepDuration));
      } catch (error) {
        console.error(`Error during ${step.name}:`, error);
        updateStepStatus(i, "failed");
        setErrorMessage(error.message);
        allCompleted = false; // Mark that not all steps were successful
        failureError = error.message; // Store the error message
        break; // Stop the process on failure
      }
    }

    setIsLoading(false);

    // After processing, send a notification email based on the outcome
    try {
      await fetch("http://127.0.0.1:8000/notify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: userEmail,
          success: allCompleted,
          error: allCompleted ? null : failureError,
        }),
      });
    } catch (notifyError) {
      console.error("Failed to send notification email:", notifyError);
      // Optionally, set another error message or log it
    }

    if (allCompleted) {
      navigate("/select"); // Navigate to /select upon success
    }
  };

  // Retry function to re-attempt processing
  const handleRetry = async (index) => {
    await handleProcess(email);
  };

  // Function to get the appropriate status icon
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

  // Function to get the status text
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
    steps.length > 0 ? (completedSteps / steps.length) * 100 : 0;

  // Calculate total time as the sum of step times
  useEffect(() => {
    const total = steps.reduce((acc, step) => {
      return acc + (step.time ? step.time : 0);
    }, 0);
    setTotalTime(total.toFixed(2));
  }, [steps]);

  // Email Modal Component
  const EmailModal = () => (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg p-6 w-11/12 max-w-md">
        <h2 className="text-2xl mb-4">Enter Your Email</h2>
        <input
          type="email"
          placeholder="your.email@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 mb-4"
        />
        <div className="flex justify-end">
          <button
            onClick={() => {
              if (email.trim() === "") {
                alert("Please enter a valid email.");
                return;
              }
              setShowEmailModal(false);
              handleProcess(email);
            }}
            className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 transition duration-200"
          >
            Start
          </button>
        </div>
      </div>
    </div>
  );

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
                <th className="px-4 py-2 text-left bg-gray-200">Step</th>
                <th className="px-4 py-2 text-left bg-gray-200">Status</th>
                <th className="px-4 py-2 text-left bg-gray-200">Time Taken (sec)</th>
                <th className="px-4 py-2 text-left bg-gray-200">Actions</th>
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
                    <span className="font-medium">{step.name}</span>
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
                    {step.time !== null ? step.time : "--"}
                  </td>
                  <td className="px-4 py-2">
                    {step.status === "failed" && (
                      <button
                        onClick={() => handleRetry(index)}
                        disabled={isLoading}
                        className="flex items-center bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600 transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <FaRedoAlt className="mr-1" />
                        Retry
                      </button>
                    )}
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
        <div className="mt-4 text-center text-gray-700">
          Total Time Taken: {totalTime} sec
        </div>

        {/* Start Button */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={() => setShowEmailModal(true)}
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

      {/* Email Modal */}
      {showEmailModal && <EmailModal />}
    </div>
  );
}

export default Processing;

