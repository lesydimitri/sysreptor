import urlJoin from 'url-join';
import { debounce } from 'lodash';

export function absoluteApiUrl(url, axios) {
  if (['http', 'data'].some(p => url.startsWith(p))) {
    return url;
  } else if (url.startsWith('/api/')) {
    return urlJoin(new URL(axios.defaults.baseURL, window.location).origin, url);
  } else {
    return urlJoin(axios.defaults.baseURL, url);
  }
}

export function relativeTo(url, baseUrl) {
  const absUrl = absoluteApiUrl(url);
  baseUrl = absoluteApiUrl(baseUrl);

  if (absUrl.startsWith(baseUrl)) {
    return absUrl.substring(baseUrl.length);
  } else {
    return url;
  }
}

export class CursorPaginationFetcher {
  constructor(baseURL, axios, toast) {
    this.axios = axios;
    this.toast = toast;
    this.baseURL = baseURL;

    this.nextPageURL = this.baseURL;
    this.isLoading = false;
    this.data = [];
  }

  get hasNextPage() {
    return this.nextPageURL !== null;
  }

  async fetchNextPage() {
    if (!this || this.isLoading || !this.hasNextPage) {
      return;
    }

    this.isLoading = true;
    try {
      const res = await this.axios.$get(this.nextPageURL);
      this.nextPageURL = res.next;
      this.data.push(...res.results);
    } catch (error) {
      console.log('CursorPaginationFetcher error', error);
      this.toast.global.requestError({ error });
    }
    this.isLoading = false;
  }
}

export class SearchableCursorPaginationFetcher {
  constructor({ baseURL, searchQuery = '', axios, toast }) {
    this.axios = axios;
    this.toast = toast;
    this.baseURL = baseURL;
    this._searchQuery = searchQuery;

    this._fetchNextPageDebounced = debounce(function() { this._fetchNextPage(); }, 500);

    this.fetcher = null;
    this._createFetcher();
  }

  _createFetcher() {
    const searchParams = new URLSearchParams(this.baseURL.split('?')[1]);
    searchParams.set('search', this.searchQuery || '');
    const searchUrl = this.baseURL.split('?')[0] + '?' + searchParams.toString();
    this.fetcher = new CursorPaginationFetcher(searchUrl, this.axios, this.toast);
  }

  search(val) {
    this._searchQuery = val;
    this._createFetcher();
    this.fetchNextPage();
  }

  get searchQuery() {
    return this._searchQuery;
  }

  set searchQuery(val) {
    this.search(val);
  }

  get hasNextPage() {
    return this.fetcher.hasNextPage;
  }

  get data() {
    return this.fetcher.data;
  }

  fetchNextPage() {
    this._fetchNextPageDebounced();
  }

  async _fetchNextPage() {
    await this.fetcher.fetchNextPage();
  }

  fetchNextPageImmediate() {
    if (!this) {
      return;
    }

    this._fetchNextPageDebounced();
    this._fetchNextPageDebounced.flush();
  }
}
