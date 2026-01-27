#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Node {
    ll sum;
    int parent;
    unsigned char take;
};

struct Cand {
    ll sum;
    int parent;
    unsigned char take;
    ll diff;
};

static inline ll absl(ll x) { return x >= 0 ? x : -x; }

vector<int> beam_search_ordered(const vector<ll>& values, ll T, int K) {
    int n = (int)values.size();
    vector<vector<Node>> layers(n + 1);
    layers[0].push_back({0, -1, 0});

    vector<Cand> cand;
    cand.reserve(max(4, 2 * K));

    bool foundExact = false;
    int exactLayer = -1, exactIdx = -1;

    for (int i = 0; i < n; ++i) {
        cand.clear();
        const auto& prev = layers[i];
        cand.reserve(prev.size() * 2);
        ll ai = values[i];
        for (int j = 0; j < (int)prev.size(); ++j) {
            ll s = prev[j].sum;
            Cand c0{ s, j, 0, absl(s - T) };
            cand.push_back(c0);
            ll s2 = s + ai;
            Cand c1{ s2, j, 1, absl(s2 - T) };
            cand.push_back(c1);
        }
        int keep = K;
        if (keep >= (int)cand.size()) {
            // keep all
        } else {
            nth_element(cand.begin(), cand.begin() + keep, cand.end(),
                        [](const Cand& x, const Cand& y) { return x.diff < y.diff; });
        }
        int takeCount = min(keep, (int)cand.size());
        layers[i + 1].reserve(takeCount);
        for (int k = 0; k < takeCount; ++k) {
            auto& c = cand[k];
            layers[i + 1].push_back(Node{c.sum, c.parent, c.take});
            if (c.diff == 0) {
                foundExact = true;
                exactLayer = i + 1;
                exactIdx = k;
                break;
            }
        }
        if (foundExact) {
            // Early reconstruction
            vector<int> sel(n, 0);
            int idx = exactIdx;
            for (int layer = exactLayer; layer >= 1; --layer) {
                const Node& cur = layers[layer][idx];
                sel[layer - 1] = cur.take;
                idx = cur.parent;
                if (idx < 0) idx = 0;
            }
            // Remaining items are 0 (already initialized)
            return sel;
        }
    }

    // choose best at the last layer
    const auto& last = layers[n];
    int bestIdx = 0;
    ll bestDiff = LLONG_MAX;
    for (int i = 0; i < (int)last.size(); ++i) {
        ll diff = absl(last[i].sum - T);
        if (diff < bestDiff) {
            bestDiff = diff;
            bestIdx = i;
        }
    }
    vector<int> sel(n, 0);
    int idx = bestIdx;
    for (int i = n; i >= 1; --i) {
        const Node& cur = layers[i][idx];
        sel[i - 1] = (int)cur.take;
        idx = cur.parent;
        if (idx < 0) idx = 0;
    }
    return sel;
}

void one_flip_local(vector<int>& sel, const vector<ll>& a, ll& S, ll T, mt19937_64& rng) {
    int n = (int)sel.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    bool improved = true;
    int passes = 0;
    while (improved && passes < 6) {
        improved = false;
        passes++;
        shuffle(order.begin(), order.end(), rng);
        for (int idx : order) {
            ll newS = S + (sel[idx] ? -a[idx] : a[idx]);
            if (absl(newS - T) < absl(S - T)) {
                sel[idx] ^= 1;
                S = newS;
                improved = true;
            }
        }
    }
}

void two_flip_local(vector<int>& sel, const vector<ll>& a, ll& S, ll T, mt19937_64& rng, int maxTries) {
    int n = (int)sel.size();
    ll bestDiff = absl(S - T);
    for (int tries = 0; tries < maxTries; ++tries) {
        int i = (int)(rng() % n);
        int j = (int)(rng() % n);
        if (i == j) continue;
        ll delta = (sel[i] ? -a[i] : a[i]) + (sel[j] ? -a[j] : a[j]);
        ll newS = S + delta;
        ll newDiff = absl(newS - T);
        if (newDiff < bestDiff) {
            sel[i] ^= 1;
            sel[j] ^= 1;
            S = newS;
            bestDiff = newDiff;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    ll T;
    if (!(cin >> n >> T)) {
        return 0;
    }
    vector<ll> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    ll total = 0;
    for (ll v : a) total += v;

    string out(n, '0');
    if (T <= 0) {
        cout << out << '\n';
        return 0;
    }
    if (T >= total) {
        for (int i = 0; i < n; ++i) out[i] = '1';
        cout << out << '\n';
        return 0;
    }

    // Sort items by descending value
    vector<pair<ll,int>> items(n);
    for (int i = 0; i < n; ++i) items[i] = {a[i], i};
    sort(items.begin(), items.end(), [](const auto& x, const auto& y) {
        if (x.first != y.first) return x.first > y.first;
        return x.second < y.second;
    });
    vector<ll> values_sorted(n);
    vector<int> idx_sorted(n);
    for (int i = 0; i < n; ++i) {
        values_sorted[i] = items[i].first;
        idx_sorted[i] = items[i].second;
    }

    int beamWidth = 20000;
    beamWidth = max(2000, beamWidth);
    beamWidth = min(beamWidth, 60000);

    vector<int> sel_sorted = beam_search_ordered(values_sorted, T, beamWidth);

    vector<int> sel(n, 0);
    for (int i = 0; i < n; ++i) sel[idx_sorted[i]] = sel_sorted[i];

    ll S = 0;
    for (int i = 0; i < n; ++i) if (sel[i]) S += a[i];

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    one_flip_local(sel, a, S, T, rng);
    two_flip_local(sel, a, S, T, rng, 50000);
    one_flip_local(sel, a, S, T, rng);

    for (int i = 0; i < n; ++i) out[i] = sel[i] ? '1' : '0';
    cout << out << '\n';
    return 0;
}