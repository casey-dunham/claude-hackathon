import { useEffect, useState } from 'react';
import { getProfile, updateProfile } from '../services/api';
import type { Profile } from '../services/types';

const DIETARY_OPTIONS = [
  'Gluten-free',
  'Vegetarian',
  'Vegan',
  'Dairy-free',
  'Nut-free',
  'Halal',
  'Kosher',
  'Low-carb',
  'Keto',
  'Paleo',
];

const EMPTY_PROFILE: Profile = {
  calorie_goal: null,
  protein_goal_g: null,
  carbs_goal_g: null,
  fat_goal_g: null,
  dietary_restrictions: [],
};

export default function ProfileTab() {
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load profile'))
      .finally(() => setLoading(false));
  }, []);

  function toggleRestriction(option: string) {
    setProfile((prev) => ({
      ...prev,
      dietary_restrictions: prev.dietary_restrictions.includes(option)
        ? prev.dietary_restrictions.filter((r) => r !== option)
        : [...prev.dietary_restrictions, option],
    }));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateProfile(profile);
      setProfile(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-sm text-[#a1a1aa]">Loading profile...</p>;

  return (
    <div className="max-w-lg space-y-6">
      <div className="rounded-xl border border-[#f0f0f0] bg-white p-5">
        <h2 className="mb-4 text-sm font-medium text-[#18181b]">Daily Goals</h2>
        <div className="grid grid-cols-2 gap-4">
          {(
            [
              { label: 'Calories', key: 'calorie_goal', unit: 'kcal' },
              { label: 'Protein', key: 'protein_goal_g', unit: 'g' },
              { label: 'Carbs', key: 'carbs_goal_g', unit: 'g' },
              { label: 'Fat', key: 'fat_goal_g', unit: 'g' },
            ] as { label: string; key: keyof Profile; unit: string }[]
          ).map(({ label, key, unit }) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-[#71717a]">
                {label} ({unit})
              </label>
              <input
                type="number"
                min={0}
                value={profile[key] ?? ''}
                onChange={(e) =>
                  setProfile((prev) => ({
                    ...prev,
                    [key]: e.target.value === '' ? null : Number(e.target.value),
                  }))
                }
                className="w-full rounded-lg border border-[#f0f0f0] px-3 py-2 text-sm text-[#18181b] outline-none focus:border-[#a1a1aa]"
                placeholder="—"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-[#f0f0f0] bg-white p-5">
        <h2 className="mb-4 text-sm font-medium text-[#18181b]">Dietary Restrictions</h2>
        <div className="flex flex-wrap gap-2">
          {DIETARY_OPTIONS.map((option) => {
            const active = profile.dietary_restrictions.includes(option);
            return (
              <button
                key={option}
                onClick={() => toggleRestriction(option)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  active
                    ? 'border-[#18181b] bg-[#18181b] text-white'
                    : 'border-[#f0f0f0] bg-white text-[#71717a] hover:border-[#d4d4d8]'
                }`}
              >
                {option}
              </button>
            );
          })}
        </div>
      </div>

      {error && <p className="text-xs text-[#b91c1c]">{error}</p>}

      <button
        onClick={handleSave}
        disabled={saving}
        className="rounded-lg bg-[#18181b] px-5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-80 disabled:opacity-50"
      >
        {saving ? 'Saving...' : saved ? 'Saved!' : 'Save profile'}
      </button>
    </div>
  );
}
