import Sidebar from "./Sidebar";
import ChatWindow from "../chat/ChatWindow";
import RightPanel from "./RightPanel";

export default function AppShell() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0f1117]">
      {/* Left Sidebar */}
      <aside className="w-80 border-r border-gray-800 flex flex-col">
        <Sidebar />
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col">
        <ChatWindow />
      </main>

      {/* Right Panel */}
      <aside className="w-80 border-l border-gray-800 flex flex-col">
        <RightPanel />
      </aside>
    </div>
  );
}