var VERSION = "dev";

self.addEventListener("install", evt => {
	async function init() {
		var keys = await caches.keys();
		for(var key, i = 0, l = keys.length; i < l; i++) {
			key = keys[i];
			if(key == VERSION || key == "permanent") continue;
			console.log(`Deleting cache ${key}`);
			caches.delete(key);
		}
		// Create a cache for this version...
		console.log(`Opening ${VERSION} cache`);
		await caches.open(VERSION);
		// ...and a permanent cache (that stores hashed files)
		console.log(`Opening permanent cache`);
		await caches.open("permanent");
	}
	evt.waitUntil(init());
});

/**
 * Returns true if the URL of the given response contains a hash, false otherwise.
 */
function hasHash(response) {
	return response.url.match(/\.[0-9a-f]{8,}\.[^.]$/);
}

self.addEventListener("fetch", async evt => {
	async function fetchFromCache(request) {
		ret = await caches.match(request);
		console.log(`Fetching ${request.url} from cache${ret ? "" : ", does not exist"}`);
		return ret;
	}
	async function getResponse(evt) {
		var request = evt.request;
		// In production, try to get the response from the cache
		// (in development, files change and mustn't be cached)
		if(VERSION != "dev") {
			var cachedResponse = await fetchFromCache(request);
			if(cachedResponse) return cachedResponse;
		}
		try {
			var response = await fetch(request);

			// Store the response in the version cache
			// (or permanent cache if it's a hashed file)

			var clonedResponse = response.clone();

			evt.waitUntil(
				caches.open(hasHash(response) ? "permanent" : VERSION)
				.then(cache => {
					console.log(`Storing ${response.url}`);
					return cache.put(request, clonedResponse);
				})
				.catch(console.error)
			);

			return response;
		} catch(err) {
			// In development, serve requests from the cache if they couldn't be done
			if(VERSION == "dev") {
				var cachedResponse = await fetchFromCache(request);
				if(cachedResponse)
					return cachedResponse;
				else
					throw err;
			}
		}
	}
	evt.respondWith(getResponse(evt));
});
