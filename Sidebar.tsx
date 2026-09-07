"use client";

type SidebarProps = {
  onNewChat: () => void;
};

export default function Sidebar({ onNewChat }: SidebarProps) {
  return (
    <aside className="flex h-full w-[270px] flex-col border-r border-white/[0.07] bg-[#08080b]/95 backdrop-blur-2xl">

      {/* Logo */}
      <div className="flex h-20 items-center gap-3 border-b border-white/[0.07] px-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-violet-400/20 bg-violet-500/[0.08] shadow-[0_0_25px_rgba(139,92,246,0.2)]">
          <span className="text-lg font-bold text-violet-300">I</span>
        </div>

        <div>
          <h1 className="text-lg font-semibold tracking-[0.2em]">
            IGNYX
          </h1>

          <p className="text-[8px] uppercase tracking-[0.3em] text-white/30">
            Intelligence Evolved
          </p>
        </div>
      </div>

      {/* New Chat */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="group flex w-full items-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-3 text-sm text-white/70 transition-all duration-300 hover:border-violet-400/30 hover:bg-violet-500/[0.08] hover:text-white"
        >
          <span className="text-xl font-light transition-transform duration-300 group-hover:rotate-90">
            +
          </span>

          <span>New Chat</span>
        </button>
      </div>

      {/* Chats */}
      <div className="flex-1 overflow-y-auto px-3">

        <p className="px-3 pb-3 pt-2 text-[10px] font-medium uppercase tracking-[0.25em] text-white/25">
          Recent Chats
        </p>

        <div className="space-y-1">

          <button className="w-full rounded-xl px-3 py-3 text-left text-sm text-white/45 transition hover:bg-white/[0.04] hover:text-white/80">
            Welcome to IGNYX
          </button>

          <button className="w-full rounded-xl px-3 py-3 text-left text-sm text-white/45 transition hover:bg-white/[0.04] hover:text-white/80">
            Python project
          </button>

          <button className="w-full rounded-xl px-3 py-3 text-left text-sm text-white/45 transition hover:bg-white/[0.04] hover:text-white/80">
            Machine learning
          </button>

        </div>
      </div>

      {/* Bottom */}
      <div className="border-t border-white/[0.07] p-4">

        <button className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm text-white/40 transition hover:bg-white/[0.04] hover:text-white/80">
          <span>⚙</span>
          Settings
        </button>

        <div className="mt-2 flex items-center gap-3 rounded-xl bg-white/[0.03] p-3">

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-violet-500/15 text-sm font-semibold text-violet-200">
            M
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm text-white/70">
              My Account
            </p>

            <p className="text-[10px] text-white/25">
              IGNYX User
            </p>
          </div>

        </div>
      </div>

    </aside>
  );
}