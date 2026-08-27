/**
 * ==============================================================================
 * MineGuard & Smart Complaint System - Google Maps & Exact Location Module
 * ==============================================================================
 * Features:
 * 1. Google Places Autocomplete for instant address search suggestions.
 * 2. Interactive Google Map with a Draggable Marker.
 * 3. Reverse Geocoding on marker drag & map click to auto-fill address and coordinates.
 * 4. "Use My Current Location" button with Geolocation API & permission error handling.
 * 5. Property Details Interactive Map Viewer with "Get Directions" navigation.
 * 6. Graceful fallbacks for unauthenticated or offline states.
 * 
 * REQUIRED GOOGLE APIS IN GOOGLE CLOUD CONSOLE:
 * - Maps JavaScript API
 * - Places API
 * - Geocoding API
 * ==============================================================================
 */

// Registry for pending map initializers if Google Maps loads asynchronously
window.__gmapsInitializers = window.__gmapsInitializers || [];

/**
 * Global Callback invoked by Google Maps script once loaded.
 */
window.initGoogleMapsServices = function () {
    console.log("🗺️ [GoogleMaps] Google Maps API loaded successfully.");
    window.__gmapsLoaded = true;
    while (window.__gmapsInitializers.length > 0) {
        const initFn = window.__gmapsInitializers.shift();
        try {
            initFn();
        } catch (err) {
            console.error("⚠️ [GoogleMaps] Error executing pending map initializer:", err);
        }
    }
};

/**
 * Google Maps Authentication Failure Handler.
 */
window.gm_authFailure = function () {
    console.warn("⚠️ [GoogleMaps] Authentication Failed: Please check your GOOGLE_MAPS_API_KEY in .env and ensure Maps JavaScript API, Places API, and Geocoding API are enabled.");
    // Hide all loading overlays
    document.querySelectorAll('#location-map-loading').forEach(el => { el.style.display = 'none'; });
    // Show auth failure notices
    document.querySelectorAll('.gmaps-auth-notice').forEach(el => {
        el.classList.remove('d-none');
    });
};

/**
 * Helper to queue or run map initialization logic.
 */
function onGoogleMapsReady(callback) {
    if (window.__gmapsLoaded && typeof google !== 'undefined' && google.maps) {
        callback();
    } else {
        window.__gmapsInitializers.push(callback);
    }
}

/**
 * ==============================================================================
 * GoogleMapsLocationPicker Class
 * Handles Address Search, Places Autocomplete, Draggable Pin, & Current Location
 * ==============================================================================
 */
class GoogleMapsLocationPicker {
    constructor(config) {
        this.config = Object.assign({
            inputId: 'location',
            mapId: 'location-map',
            latInputId: 'input-latitude',
            lonInputId: 'input-longitude',
            placeIdInputId: 'input-place-id',
            statusId: 'location-status-text',
            badgeId: 'live-location-badge',
            locateBtnId: 'btn-current-location',
            clearBtnId: 'btn-clear-location',
            errorContainerId: 'location-error-alert',
            defaultLat: 21.2514, // Default (Raipur / India)
            defaultLng: 81.6296,
            defaultZoom: 14
        }, config);

        this.inputEl = document.getElementById(this.config.inputId);
        this.mapEl = document.getElementById(this.config.mapId);
        this.latInput = document.getElementById(this.config.latInputId);
        this.lonInput = document.getElementById(this.config.lonInputId);
        this.placeIdInput = document.getElementById(this.config.placeIdInputId);
        this.statusEl = document.getElementById(this.config.statusId);
        this.badgeEl = document.getElementById(this.config.badgeId);
        this.locateBtn = document.getElementById(this.config.locateBtnId);
        this.clearBtn = document.getElementById(this.config.clearBtnId);
        this.errorEl = document.getElementById(this.config.errorContainerId);

        this.map = null;
        this.marker = null;
        this.geocoder = null;
        this.autocomplete = null;

        this.init();
    }

    init() {
        if (!this.inputEl || !this.mapEl) {
            console.warn("⚠️ [GoogleMapsPicker] Missing input or map container elements.");
            return;
        }

        // Set up Current Location button immediately (works with browser API)
        if (this.locateBtn) {
            this.locateBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleCurrentLocation();
            });
        }

        // Set up Clear button
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearLocation();
            });
        }

        // Initialize Google Maps once script is ready
        onGoogleMapsReady(() => this.setupGoogleMaps());

        // Fallback timeout: If Google Maps doesn't load within 8 seconds, setup fallback
        setTimeout(() => {
            if (!this.map && typeof google === 'undefined') {
                console.warn('⚠️ [GoogleMapsPicker] Google Maps API did not load in time. Switching to fallback mode.');
                this.setupFallbackMode();
            }
        }, 8000);
    }

    setupGoogleMaps() {
        if (window.__gMapsFallbackOnly || typeof google === 'undefined' || !google.maps) {
            this.setupFallbackMode();
            return;
        }

        try {
            this.geocoder = new google.maps.Geocoder();

            // Determine initial coordinates
            let initialLat = parseFloat(this.latInput?.value) || this.config.defaultLat;
            let initialLng = parseFloat(this.lonInput?.value) || this.config.defaultLng;
            const initialPos = { lat: initialLat, lng: initialLng };

            // Initialize Map
            this.map = new google.maps.Map(this.mapEl, {
                center: initialPos,
                zoom: this.config.defaultZoom,
                mapTypeControl: true,
                mapTypeControlOptions: {
                    style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
                    position: google.maps.ControlPosition.TOP_RIGHT
                },
                streetViewControl: false,
                fullscreenControl: true,
                zoomControl: true,
                gestureHandling: 'greedy'
            });

            // Initialize Draggable Marker
            this.marker = new google.maps.Marker({
                position: initialPos,
                map: this.map,
                draggable: true,
                animation: google.maps.Animation.DROP,
                title: "Drag marker to adjust exact property location"
            });

            // Marker Drag End Listener -> Reverse Geocode
            this.marker.addListener('dragend', () => {
                const pos = this.marker.getPosition();
                this.updateCoordinates(pos.lat(), pos.lng());
                this.reverseGeocode(pos.lat(), pos.lng());
            });

            // Map Click Listener -> Move Marker & Reverse Geocode
            this.map.addListener('click', (event) => {
                const clickedLat = event.latLng.lat();
                const clickedLng = event.latLng.lng();
                this.marker.setPosition(event.latLng);
                this.updateCoordinates(clickedLat, clickedLng);
                this.reverseGeocode(clickedLat, clickedLng);
            });

            // Initialize Places Autocomplete
            if (google.maps.places && google.maps.places.Autocomplete) {
                this.autocomplete = new google.maps.places.Autocomplete(this.inputEl, {
                    fields: ['formatted_address', 'geometry', 'name', 'place_id']
                });

                // Bind autocomplete to map viewport if desired
                this.autocomplete.bindTo('bounds', this.map);

                // Prevent form submission on hitting Enter in Autocomplete dropdown
                this.inputEl.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                    }
                });

                // Place Selection Listener
                this.autocomplete.addListener('place_changed', () => {
                    const place = this.autocomplete.getPlace();
                    if (!place.geometry || !place.geometry.location) {
                        this.showError("No location details found for this address. Please choose from suggestions or drag the map marker.");
                        return;
                    }

                    this.clearError();
                    const loc = place.geometry.location;
                    const lat = loc.lat();
                    const lng = loc.lng();
                    const formattedAddr = place.formatted_address || place.name || this.inputEl.value;

                    // Update UI and Inputs
                    this.inputEl.value = formattedAddr;
                    this.updateCoordinates(lat, lng);
                    if (this.placeIdInput && place.place_id) {
                        this.placeIdInput.value = place.place_id;
                    }

                    // Move map & marker
                    this.map.panTo(loc);
                    this.map.setZoom(16);
                    this.marker.setPosition(loc);
                    this.marker.setAnimation(google.maps.Animation.BOUNCE);
                    setTimeout(() => this.marker && this.marker.setAnimation(null), 1400);

                    this.setStatus(`✓ Exact Location: ${lat.toFixed(5)}, ${lng.toFixed(5)}`, 'success');
                });
            }

            // ✅ Hide loading overlay — map is ready
            this.hideLoadingOverlay();
            console.log("📍 [GoogleMapsPicker] Google Maps Location Picker initialized.");
        } catch (e) {
            console.error("⚠️ [GoogleMapsPicker] Initialization error:", e);
            this.setupFallbackMode();
        }
    }

    /**
     * Reverse Geocode coordinates to an address using Google Geocoder.
     */
    reverseGeocode(lat, lng) {
        if (!this.geocoder) return;

        this.setStatus(`Geocoding coordinates (${lat.toFixed(4)}, ${lng.toFixed(4)})...`, 'info');

        this.geocoder.geocode({ location: { lat: lat, lng: lng } }, (results, status) => {
            if (status === 'OK' && results && results[0]) {
                const address = results[0].formatted_address;
                this.inputEl.value = address;
                if (this.placeIdInput && results[0].place_id) {
                    this.placeIdInput.value = results[0].place_id;
                }
                this.setStatus(`✓ Location Set: (${lat.toFixed(5)}, ${lng.toFixed(5)})`, 'success');
                this.clearError();
            } else {
                this.setStatus(`✓ Coordinates Set: (${lat.toFixed(5)}, ${lng.toFixed(5)})`, 'success');
                console.warn("⚠️ [GoogleMapsPicker] Reverse geocoding failed status:", status);
            }
        });
    }

    /**
     * "Use My Current Location" - Uses Browser Geolocation API.
     */
    handleCurrentLocation() {
        if (!("geolocation" in navigator)) {
            this.showError("Geolocation is not supported by your current browser.");
            return;
        }

        this.clearError();
        this.setLocateButtonLoading(true);
        this.setStatus("Acquiring high-accuracy GPS coordinates...", 'info');

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                const accuracy = position.coords.accuracy ? Math.round(position.coords.accuracy) : 0;

                this.setLocateButtonLoading(false);
                this.updateCoordinates(lat, lng);

                if (this.map && this.marker) {
                    const pos = new google.maps.LatLng(lat, lng);
                    this.map.panTo(pos);
                    this.map.setZoom(17);
                    this.marker.setPosition(pos);
                    this.marker.setAnimation(google.maps.Animation.DROP);
                    this.reverseGeocode(lat, lng);
                } else {
                    // Fallback reverse geocoding via OpenStreetMap if Google Maps is not loaded
                    this.fallbackReverseGeocode(lat, lng);
                }

                this.setStatus(`✓ Current GPS Location Detected (${lat.toFixed(5)}, ${lng.toFixed(5)}) ±${accuracy}m`, 'success');
            },
            (error) => {
                this.setLocateButtonLoading(false);
                let message = "Unable to retrieve your current location.";
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        message = "Location permission denied. Please allow location access in your browser settings or type your address above.";
                        break;
                    case error.POSITION_UNAVAILABLE:
                        message = "GPS position is unavailable. Please check device location settings or enter address manually.";
                        break;
                    case error.TIMEOUT:
                        message = "Location request timed out. Please try again or search your address.";
                        break;
                }
                this.showError(message);
                this.setStatus(`Error: ${error.message}`, 'danger');
            },
            {
                enableHighAccuracy: true,
                timeout: 12000,
                maximumAge: 0
            }
        );
    }

    /**
     * Fallback reverse geocode if Google Maps API is keyless or blocked.
     */
    fallbackReverseGeocode(lat, lng) {
        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`)
            .then(res => res.json())
            .then(data => {
                if (data && data.display_name) {
                    this.inputEl.value = data.display_name;
                }
            })
            .catch(e => console.warn("Fallback geocode error:", e));
    }

    /**
     * Fallback setup when Google Maps API is not loaded or key is missing.
     */
    setupFallbackMode() {
        console.log("ℹ️ [GoogleMapsPicker] Running in fallback mode.");
        // ✅ Hide loading overlay in fallback too
        this.hideLoadingOverlay();
        if (this.mapEl) {
            this.mapEl.innerHTML = `
                <div class="d-flex flex-column align-items-center justify-content-center h-100 bg-light p-4 text-center border rounded-3">
                    <i class="bi bi-geo-alt-fill text-primary" style="font-size: 2.5rem;"></i>
                    <h6 class="fw-bold mt-2 mb-1">Location Entry Mode</h6>
                    <p class="small text-muted mb-3">Google Maps requires an API key. Use <b>"Use My Current Location"</b> or type your address above to save coordinates.</p>
                    <div class="small text-secondary bg-white p-2 rounded border">
                        <i class="bi bi-info-circle me-1"></i> Add <code>GOOGLE_MAPS_API_KEY</code> in <code>.env</code> to enable the interactive map.
                    </div>
                </div>
            `;
        }
    }

    hideLoadingOverlay() {
        // Hide the loading overlay if it exists (sibling to map div)
        const loadingEl = document.getElementById('location-map-loading');
        if (loadingEl) loadingEl.style.display = 'none';
    }

    updateCoordinates(lat, lng) {
        if (this.latInput) this.latInput.value = lat;
        if (this.lonInput) this.lonInput.value = lng;
        
        // Also update legacy fields if present for full backward compatibility
        const browserLat = document.getElementById('browser_lat');
        const browserLon = document.getElementById('browser_lon');
        if (browserLat) browserLat.value = lat;
        if (browserLon) browserLon.value = lng;
    }

    setStatus(text, type = 'info') {
        if (this.statusEl) {
            let colorClass = 'text-muted';
            if (type === 'success') colorClass = 'text-success fw-bold';
            if (type === 'danger') colorClass = 'text-danger fw-bold';
            if (type === 'info') colorClass = 'text-primary';
            this.statusEl.innerHTML = `<span class="${colorClass}">${text}</span>`;
        }
        if (this.badgeEl) {
            if (type === 'success') {
                this.badgeEl.innerHTML = `<i class="bi bi-check-circle-fill text-success"></i>`;
            } else if (type === 'danger') {
                this.badgeEl.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-danger"></i>`;
            } else {
                this.badgeEl.innerHTML = `<span class="spinner-border spinner-border-sm text-primary" role="status"></span>`;
            }
        }
    }

    showError(message) {
        if (this.errorEl) {
            this.errorEl.innerHTML = `
                <div class="alert alert-warning alert-dismissible fade show p-3 mt-2 shadow-sm" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2 text-warning"></i>
                    <span>${message}</span>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            this.errorEl.classList.remove('d-none');
        } else {
            alert(message);
        }
    }

    clearError() {
        if (this.errorEl) {
            this.errorEl.innerHTML = '';
            this.errorEl.classList.add('d-none');
        }
    }

    setLocateButtonLoading(isLoading) {
        if (!this.locateBtn) return;
        if (isLoading) {
            this.locateBtn.disabled = true;
            this.locateBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> Detecting...`;
        } else {
            this.locateBtn.disabled = false;
            this.locateBtn.innerHTML = `<i class="bi bi-crosshair me-1"></i> Use My Current Location`;
        }
    }

    clearLocation() {
        this.inputEl.value = '';
        if (this.latInput) this.latInput.value = '';
        if (this.lonInput) this.lonInput.value = '';
        if (this.placeIdInput) this.placeIdInput.value = '';
        this.setStatus('Location cleared. Enter address or use GPS.', 'info');
        this.clearError();
    }
}


/**
 * ==============================================================================
 * GoogleMapsLocationViewer Class
 * Renders Interactive Map for Property Details / Track / Modals with Get Directions
 * ==============================================================================
 */
class GoogleMapsLocationViewer {
    constructor(config) {
        this.config = Object.assign({
            mapId: 'detail-map',
            lat: 21.2514,
            lng: 81.6296,
            title: 'Property Location',
            address: '',
            placeId: '',
            zoom: 15,
            modalId: null,
            directionsBtnId: null
        }, config);

        this.mapEl = document.getElementById(this.config.mapId);
        this.map = null;
        this.marker = null;

        this.init();
    }

    init() {
        if (!this.mapEl) return;

        const lat = parseFloat(this.config.lat);
        const lng = parseFloat(this.config.lng);

        if (isNaN(lat) || isNaN(lng) || (lat === 0 && lng === 0)) {
            this.renderNoLocation();
            return;
        }

        // Setup Directions button link
        this.setupDirectionsButton(lat, lng);

        // Initialize Google Map once script is ready
        onGoogleMapsReady(() => this.renderMap(lat, lng));

        // If inside Bootstrap modal, handle map resize on modal show
        if (this.config.modalId) {
            const modalEl = document.getElementById(this.config.modalId);
            if (modalEl) {
                modalEl.addEventListener('shown.bs.modal', () => {
                    if (this.map) {
                        google.maps.event.trigger(this.map, 'resize');
                        this.map.setCenter({ lat: lat, lng: lng });
                    }
                });
            }
        }
    }

    renderMap(lat, lng) {
        if (typeof google === 'undefined' || !google.maps) {
            this.renderStaticFallback(lat, lng);
            return;
        }

        try {
            const pos = { lat: lat, lng: lng };

            this.map = new google.maps.Map(this.mapEl, {
                center: pos,
                zoom: this.config.zoom,
                mapTypeControl: true,
                streetViewControl: true,
                fullscreenControl: true,
                zoomControl: true
            });

            this.marker = new google.maps.Marker({
                position: pos,
                map: this.map,
                title: this.config.title,
                animation: google.maps.Animation.DROP
            });

            // InfoWindow with Address & Directions
            const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}${this.config.placeId ? '&destination_place_id=' + encodeURIComponent(this.config.placeId) : ''}`;
            const infoContent = `
                <div style="padding: 6px; font-family: sans-serif; max-width: 240px;">
                    <h6 style="margin: 0 0 4px 0; font-size: 14px; font-weight: bold; color: #003366;">${this.escapeHtml(this.config.title)}</h6>
                    <p style="margin: 0 0 8px 0; font-size: 12px; color: #555;">${this.escapeHtml(this.config.address || 'Exact Coordinates: ' + lat.toFixed(5) + ', ' + lng.toFixed(5))}</p>
                    <a href="${directionsUrl}" target="_blank" style="display: inline-block; padding: 4px 10px; font-size: 12px; background-color: #003366; color: white; border-radius: 4px; text-decoration: none; font-weight: 500;">
                        <i class="bi bi-cursor-fill"></i> Get Directions
                    </a>
                </div>
            `;

            const infoWindow = new google.maps.InfoWindow({
                content: infoContent
            });

            this.marker.addListener('click', () => {
                infoWindow.open(this.map, this.marker);
            });

            // Automatically open InfoWindow
            infoWindow.open(this.map, this.marker);

        } catch (e) {
            console.error("⚠️ [GoogleMapsViewer] Error rendering map:", e);
            this.renderStaticFallback(lat, lng);
        }
    }

    setupDirectionsButton(lat, lng) {
        if (!this.config.directionsBtnId) return;
        const btn = document.getElementById(this.config.directionsBtnId);
        if (btn) {
            const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}${this.config.placeId ? '&destination_place_id=' + encodeURIComponent(this.config.placeId) : ''}`;
            btn.href = directionsUrl;
            btn.target = "_blank";
            btn.rel = "noopener noreferrer";
        }
    }

    renderStaticFallback(lat, lng) {
        const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        this.mapEl.innerHTML = `
            <div class="p-3 bg-light border rounded text-center">
                <p class="mb-2 text-muted small"><i class="bi bi-geo-alt-fill text-danger me-1"></i> <strong>Coordinates:</strong> ${lat.toFixed(5)}, ${lng.toFixed(5)}</p>
                <a href="${directionsUrl}" target="_blank" class="btn btn-sm btn-primary rounded-pill shadow-sm">
                    <i class="bi bi-box-arrow-up-right me-1"></i> Open in Google Maps
                </a>
            </div>
        `;
    }

    renderNoLocation() {
        this.mapEl.innerHTML = `
            <div class="p-4 bg-light border rounded text-center text-muted">
                <i class="bi bi-geo-alt text-secondary" style="font-size: 2rem;"></i>
                <p class="mb-0 mt-2 small">No exact map coordinates recorded for this entry.</p>
            </div>
        `;
    }

    escapeHtml(text) {
        if (!text) return '';
        return text.replace(/[&<>"']/g, function(m) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
        });
    }
}

// Export to window for global template usage
window.GoogleMapsLocationPicker = GoogleMapsLocationPicker;
window.GoogleMapsLocationViewer = GoogleMapsLocationViewer;
