import React, { useState } from "react";
import "./App.css";
import ChatWindow from "./components/ChatWindow";
import Logo from "./assets/Logo.png";

function App() {

  return (
    <div className="App">
      <div className="heading">
        <img src={Logo} alt="PartSelect Logo" className="logo" />
        PartSelect
      </div>
        <ChatWindow/>
    </div>
  );
}

export default App;
