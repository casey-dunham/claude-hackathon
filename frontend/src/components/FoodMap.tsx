import { useEffect } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { NearbyPlace } from "../services/types";

const defaultProto = L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown };
delete defaultProto._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

function createPlaceIcon() {
  return L.divIcon({
    className: "",
    html: '<div style="width:12px;height:12px;border-radius:50%;background:#16a34a;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.3);"></div>',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function createUserIcon() {
  return L.divIcon({
    className: "",
    html: '<div style="width:16px;height:16px;border-radius:50%;background:#2563eb;border:3px solid #fff;box-shadow:0 0 8px rgba(37,99,235,0.45);"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function RecenterMap({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], 14);
  }, [lat, lng, map]);
  return null;
}

interface FoodMapProps {
  userLat: number;
  userLng: number;
  places: NearbyPlace[];
}

export default function FoodMap({ userLat, userLng, places }: FoodMapProps) {
  return (
    <div className="h-[340px] w-full overflow-hidden rounded-xl border border-[#f0f0f0]">
      <MapContainer center={[userLat, userLng]} zoom={14} style={{ height: "100%", width: "100%" }} zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <RecenterMap lat={userLat} lng={userLng} />
        <Marker position={[userLat, userLng]} icon={createUserIcon()}>
          <Popup>
            <span className="text-xs font-medium">You are here</span>
          </Popup>
        </Marker>
        {places.map((place) => (
          <Marker key={place.id} position={[place.lat, place.lng]} icon={createPlaceIcon()}>
            <Popup>
              <div className="text-xs">
                <p className="mb-0.5 font-semibold text-[#18181b]">{place.name}</p>
                <p className="text-[#71717a]">{place.address}</p>
                <p className="mt-0.5 text-[#71717a]">{place.distance_m}m away</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
