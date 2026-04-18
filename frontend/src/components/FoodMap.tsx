import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { NearbyPlace } from '../services/types';
import { useEffect } from 'react';

// Fix default marker icons in bundled builds
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const TYPE_COLORS: Record<string, string> = {
  restaurant: '#18181b',
  cafe: '#92400e',
  grocery: '#166534',
  deli: '#7c3aed',
  food_truck: '#c2410c',
  juice_bar: '#0d9488',
};

function createIcon(type: string) {
  const color = TYPE_COLORS[type] || '#18181b';
  return L.divIcon({
    className: '',
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.3);"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function userIcon() {
  return L.divIcon({
    className: '',
    html: `<div style="width:16px;height:16px;border-radius:50%;background:#3b82f6;border:3px solid #fff;box-shadow:0 0 8px rgba(59,130,246,0.5);"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function RecenterMap({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], 15);
  }, [lat, lng, map]);
  return null;
}

interface FoodMapProps {
  places: NearbyPlace[];
  userLat: number;
  userLng: number;
  onPlaceClick?: (place: NearbyPlace) => void;
}

export default function FoodMap({ places, userLat, userLng, onPlaceClick }: FoodMapProps) {
  return (
    <div className="w-full rounded-xl overflow-hidden border border-[#f0f0f0]" style={{ height: '340px' }}>
      <MapContainer
        center={[userLat, userLng]}
        zoom={15}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <RecenterMap lat={userLat} lng={userLng} />
        <Marker position={[userLat, userLng]} icon={userIcon()}>
          <Popup>
            <span className="text-xs font-medium">You are here</span>
          </Popup>
        </Marker>
        {places.map((place) => (
          <Marker
            key={place.id}
            position={[place.lat, place.lng]}
            icon={createIcon(place.type)}
            eventHandlers={{
              click: () => onPlaceClick?.(place),
            }}
          >
            <Popup>
              <div className="text-xs">
                <p className="font-semibold text-[#18181b] mb-0.5">{place.name}</p>
                <p className="text-[#71717a]">{place.type.replace('_', ' ')} · {place.distance_m}m away</p>
                <p className="text-[#71717a]">{'$'.repeat(place.price_level)} · {place.rating} rating</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
