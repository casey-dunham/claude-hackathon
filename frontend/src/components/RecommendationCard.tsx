import { Recommendation } from '../services/types';

interface Props {
  recommendation: Recommendation;
}

export default function RecommendationCard({ recommendation: r }: Props) {
  return (
    <div className="bg-white border border-[#f0f0f0] rounded-xl p-5 hover:border-[#d4d4d8] transition-colors cursor-pointer">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-[#18181b]">{r.item_name}</h3>
          <p className="text-xs text-[#a1a1aa] mt-0.5">{r.place_name} · {r.distance_m}m away</p>
        </div>
        <span className="text-sm font-semibold text-[#18181b]">${r.estimated_price_usd.toFixed(2)}</span>
      </div>

      <p className="text-xs text-[#71717a] leading-relaxed mb-3">{r.description}</p>

      <div className="flex items-center gap-3 mb-3">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium uppercase tracking-wide text-[#a1a1aa]">Cal</span>
          <span className="text-xs font-semibold text-[#18181b]">{r.estimated_calories}</span>
        </div>
        <div className="w-px h-3 bg-[#f0f0f0]" />
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium uppercase tracking-wide text-[#a1a1aa]">Protein</span>
          <span className="text-xs font-semibold text-[#6366f1]">{r.estimated_protein_g}g</span>
        </div>
        <div className="w-px h-3 bg-[#f0f0f0]" />
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium uppercase tracking-wide text-[#a1a1aa]">Carbs</span>
          <span className="text-xs font-semibold text-[#71717a]">{r.estimated_carbs_g}g</span>
        </div>
        <div className="w-px h-3 bg-[#f0f0f0]" />
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium uppercase tracking-wide text-[#a1a1aa]">Fat</span>
          <span className="text-xs font-semibold text-[#71717a]">{r.estimated_fat_g}g</span>
        </div>
      </div>

      {r.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {r.tags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[#f4f4f5] text-[#52525b]"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
