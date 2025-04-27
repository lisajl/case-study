export const getAIMessage = async (userQuery) => {
  try {
    console.log("User query:", userQuery);  // Log the user query for debugging
    const response = await fetch("http://127.0.0.1:5000/api/get_answer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query: userQuery }),  // Send query as JSON
    });

    console.log("Response status:", response.status); // Log status for debugging

    // Ensure the response is OK before parsing
    if (!response.ok) {
      return {
        role: "assistant",
        content: `Server returned an error: ${response.status}`,
      };
    }

    const data = await response.json();  // Parse the response JSON
    console.log("Backend response:", data);  // Log the response data

    if (data.error) {
      return {
        role: "assistant",
        content: `Error: ${data.error}`,
      };
    }

    return {
      role: "assistant",
      content: data.answer,  // Return the answer from the backend
    };
  } catch (error) {
    console.error("Error:", error);  // Log any error from the fetch
    return {
      role: "assistant",
      content: "An error occurred while communicating with the server.",
    };
  }
};
