interface HeaderProps {
  userName: string;
  date: string;
}

export default function Header({ userName, date }: HeaderProps) {
  return (
    <div className="flex items-center justify-between border-b border-[#f0f0f0] bg-white px-8 py-5">
      <div>
        <h1 className="text-lg font-semibold text-[#18181b]">
          Good afternoon, {userName}
        </h1>
        <p className="mt-0.5 text-sm text-[#a1a1aa]">{date}</p>
      </div>

      <button className="flex items-center gap-2 rounded-lg bg-[#18181b] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#27272a]">
        + Log Meal
      </button>
    </div>
  );
}
