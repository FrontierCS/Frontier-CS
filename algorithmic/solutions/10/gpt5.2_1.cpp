#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct SplitMix64Hash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM =
            chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64(x + FIXED_RANDOM);
    }
};

struct Edge {
    int u, v;
    ll w;
};

static constexpr ll KEY_BASE = 131072LL; // 2^17 > 1e5

struct Solver {
    int n = 0;
    unordered_map<uint64_t, ll, SplitMix64Hash> cache;
    vector<Edge> edges;

    ll ask(int u, int v) {
        if (u > v) swap(u, v);
        uint64_t key = (uint64_t)u * (uint64_t)KEY_BASE + (uint64_t)v;
        auto it = cache.find(key);
        if (it != cache.end()) return it->second;

        cout << "? " << u << " " << v << "\n";
        cout.flush();

        ll ans;
        if (!(cin >> ans)) exit(0);
        if (ans < 0) exit(0);

        if (cache.size() < 2000000) cache.emplace(key, ans);
        return ans;
    }

    vector<ll> queryAll(int src, const vector<int>& nodes) {
        vector<ll> d(nodes.size());
        for (size_t i = 0; i < nodes.size(); i++) {
            int v = nodes[i];
            d[i] = (v == src ? 0LL : ask(src, v));
        }
        return d;
    }

    struct Comp {
        vector<int> nodes;
        bool knownRootDist = false;
        int root = -1;
        vector<ll> distRoot; // aligned with nodes
    };

    void processComp(Comp&& comp, vector<Comp>& st) {
        auto& nodes = comp.nodes;
        int sz = (int)nodes.size();
        if (sz <= 1) return;

        int A = -1;
        if (comp.knownRootDist) {
            int bestIdx = 0;
            ll bestD = comp.distRoot[0];
            for (int i = 1; i < sz; i++) {
                if (comp.distRoot[i] > bestD) {
                    bestD = comp.distRoot[i];
                    bestIdx = i;
                }
            }
            A = nodes[bestIdx];
        } else {
            int s = nodes[0];
            vector<ll> distS = queryAll(s, nodes);
            int bestIdx = 0;
            ll bestD = distS[0];
            for (int i = 1; i < sz; i++) {
                if (distS[i] > bestD) {
                    bestD = distS[i];
                    bestIdx = i;
                }
            }
            A = nodes[bestIdx];
        }

        vector<ll> distA = queryAll(A, nodes);
        int bIdx = 0;
        ll D = distA[0];
        for (int i = 1; i < sz; i++) {
            if (distA[i] > D) {
                D = distA[i];
                bIdx = i;
            }
        }
        int B = nodes[bIdx];

        vector<ll> distB = queryAll(B, nodes);
        D = distA[bIdx];

        vector<char> isPath(sz, 0);
        vector<pair<ll, int>> path; // (coord from A, node)
        path.reserve(sz);

        for (int i = 0; i < sz; i++) {
            if (distA[i] + distB[i] == D) {
                isPath[i] = 1;
                path.push_back({distA[i], nodes[i]});
            }
        }

        sort(path.begin(), path.end());
        int m = (int)path.size();

        for (int i = 0; i + 1 < m; i++) {
            int u = path[i].second;
            int v = path[i + 1].second;
            ll w = path[i + 1].first - path[i].first;
            edges.push_back({u, v, w});
        }

        if (m == 0) return; // should never happen

        unordered_map<ll, int, SplitMix64Hash> coord2idx;
        coord2idx.reserve((size_t)m * 2);
        for (int i = 0; i < m; i++) coord2idx.emplace(path[i].first, i);

        vector<vector<int>> buckets(m);
        vector<vector<ll>> bucketDist(m);

        for (int i = 0; i < sz; i++) {
            if (isPath[i]) continue;
            ll numT = distA[i] + D - distB[i];
            ll numH = distA[i] + distB[i] - D;
            ll t = numT / 2;
            ll h = numH / 2;
            auto it = coord2idx.find(t);
            if (it == coord2idx.end()) continue; // should never happen
            int j = it->second;
            buckets[j].push_back(nodes[i]);
            bucketDist[j].push_back(h);
        }

        for (int j = 0; j < m; j++) {
            if (buckets[j].empty()) continue;
            int p = path[j].second;

            Comp child;
            child.knownRootDist = true;
            child.root = p;

            child.nodes.reserve(1 + buckets[j].size());
            child.distRoot.reserve(1 + buckets[j].size());

            child.nodes.push_back(p);
            child.distRoot.push_back(0);

            for (size_t k = 0; k < buckets[j].size(); k++) {
                child.nodes.push_back(buckets[j][k]);
                child.distRoot.push_back(bucketDist[j][k]);
            }
            st.push_back(std::move(child));
        }
    }

    void solveCase() {
        edges.clear();
        edges.reserve(max(0, n - 1));

        cache.clear();
        size_t reserveHint = (size_t)min(2000000LL, max(0LL, 20LL * (ll)n));
        cache.reserve(reserveHint);

        if (n <= 1) {
            cout << "!\n";
            cout.flush();
            return;
        }

        vector<Comp> st;
        st.reserve(n);

        Comp root;
        root.knownRootDist = false;
        root.nodes.resize(n);
        iota(root.nodes.begin(), root.nodes.end(), 1);
        st.push_back(std::move(root));

        while (!st.empty()) {
            Comp cur = std::move(st.back());
            st.pop_back();
            processComp(std::move(cur), st);
        }

        // Should have exactly n-1 edges for a valid tree; still output what we have.
        cout << "!";
        for (const auto& e : edges) {
            cout << " " << e.u << " " << e.v << " " << e.w;
        }
        cout << "\n";
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    Solver solver;

    while (T--) {
        cin >> solver.n;
        solver.solveCase();
    }
    return 0;
}