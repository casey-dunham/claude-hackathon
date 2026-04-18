interface SidebarProps {
  activePage: string;
  onNavigate: (page: string) => void;
}

const navItems = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="2" y="2" width="7" height="7" rx="1.5" />
        <rect x="11" y="2" width="7" height="7" rx="1.5" />
        <rect x="2" y="11" width="7" height="7" rx="1.5" />
        <rect x="11" y="11" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    id: "meals",
    label: "Meals",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <line x1="4" y1="5" x2="16" y2="5" />
        <line x1="4" y1="10" x2="16" y2="10" />
        <line x1="4" y1="15" x2="16" y2="15" />
      </svg>
    ),
  },
  {
    id: "goals",
    label: "Goals",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="10" cy="10" r="8" />
        <circle cx="10" cy="10" r="5" />
        <circle cx="10" cy="10" r="2" />
      </svg>
    ),
  },
  {
    id: "settings",
    label: "Settings",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="10" cy="10" r="3" />
        <path d="M10 1.5v2M10 16.5v2M1.5 10h2M16.5 10h2M3.4 3.4l1.4 1.4M15.2 15.2l1.4 1.4M3.4 16.6l1.4-1.4M15.2 4.8l1.4-1.4" />
      </svg>
    ),
  },
];

export default function Sidebar({ activePage, onNavigate }: SidebarProps) {
  return (
    <div className="flex h-screen w-16 flex-col items-center justify-between border-r border-[#f0f0f0] bg-white py-5">
      <div className="flex flex-col items-center gap-6">
        <button
          onClick={() => onNavigate("dashboard")}
          className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#18181b] text-sm font-bold text-white"
        >
          N
        </button>

        <nav className="flex flex-col items-center gap-1">
          {navItems.map((item) => {
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                title={item.label}
                className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
                  isActive
                    ? "bg-[#f0f0f0] text-[#18181b]"
                    : "text-[#a1a1aa] hover:bg-[#fafafa] hover:text-[#71717a]"
                }`}
              >
                {item.icon}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f0f0f0] text-xs font-semibold text-[#18181b]">
        A
      </div>
    </div>
  );
}
