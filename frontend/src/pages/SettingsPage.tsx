const profileFields = [
  { label: "Name", value: "Adam" },
  { label: "Plan", value: "Pro Plan" },
  { label: "Email", value: "adam@example.com" },
];

const preferences = [
  { label: "Dietary preference", value: "No restrictions" },
  { label: "Meal frequency", value: "3 meals + 1 snack" },
  { label: "Hydration goal", value: "8 glasses / day" },
  { label: "Notifications", value: "Enabled" },
];

export default function SettingsPage() {
  return (
    <div>
      <h2 className="mb-6 text-lg font-semibold text-[#18181b]">Settings</h2>

      <div className="flex flex-col gap-6">
        <div className="rounded-xl border border-[#f0f0f0] bg-white">
          <div className="border-b border-[#f0f0f0] px-5 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[#a1a1aa]">
              Profile
            </p>
          </div>
          <div className="divide-y divide-[#f0f0f0]">
            {profileFields.map((field) => (
              <div
                key={field.label}
                className="flex items-center justify-between px-5 py-4"
              >
                <p className="text-sm text-[#71717a]">{field.label}</p>
                <p className="text-sm font-medium text-[#18181b]">{field.value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-[#f0f0f0] bg-white">
          <div className="border-b border-[#f0f0f0] px-5 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[#a1a1aa]">
              Preferences
            </p>
          </div>
          <div className="divide-y divide-[#f0f0f0]">
            {preferences.map((pref) => (
              <div
                key={pref.label}
                className="flex items-center justify-between px-5 py-4"
              >
                <p className="text-sm text-[#71717a]">{pref.label}</p>
                <p className="text-sm font-medium text-[#18181b]">{pref.value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
