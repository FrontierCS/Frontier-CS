#include <bits/stdc++.h>
using namespace std;

struct SplitMix64Hash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64(x + FIXED_RANDOM);
    }
};

struct Interactor {
    unordered_map<uint64_t, long long, SplitMix64Hash> cache;

    static uint64_t key(int u, int v) {
        if (u > v) swap(u, v);
        return (uint64_t)(uint32_t)u << 32 | (uint32_t)v;
    }

    long long dist(int u, int v) {
        if (u == v) return 0;
        uint64_t k = key(u, v);
        auto it = cache.find(k);
        if (it != cache.end()) return it->second;

        cout << "? " << u << " " << v << "\n";
        cout.flush();

        long long ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);

        cache.emplace(k, ans);
        return ans;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        cin >> n;

        Interactor it;
        it.cache.clear();
        it.cache.max_load_factor(0.7f);
        it.cache.reserve((size_t)max(1, n) * 20);

        vector<tuple<int,int,long long>> edges;
        edges.reserve(max(0, n - 1));

        if (n <= 1) {
            cout << "!\n";
            cout.flush();
            continue;
        }

        vector<vector<int>> st;
        st.reserve(n);
        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        st.push_back(move(all));

        auto addEdge = [&](int u, int v, long long w) {
            edges.emplace_back(u, v, w);
        };

        while (!st.empty()) {
            vector<int> nodes = move(st.back());
            st.pop_back();

            int m = (int)nodes.size();
            if (m <= 1) continue;

            if (m == 2) {
                int u = nodes[0], v = nodes[1];
                long long w = it.dist(u, v);
                addEdge(u, v, w);
                continue;
            }

            int s = nodes[0];
            vector<long long> dS(m, 0);
            int idxA = 0;
            for (int i = 1; i < m; i++) {
                dS[i] = it.dist(s, nodes[i]);
                if (dS[i] > dS[idxA]) idxA = i;
            }
            int a = nodes[idxA];

            vector<long long> dA(m, 0);
            int idxB = idxA;
            for (int i = 0; i < m; i++) {
                if (i == idxA) continue;
                dA[i] = it.dist(a, nodes[i]);
                if (dA[i] > dA[idxB]) idxB = i;
            }
            int b = nodes[idxB];

            vector<long long> dB(m, 0);
            for (int i = 0; i < m; i++) {
                if (i == idxB) continue;
                dB[i] = it.dist(b, nodes[i]);
            }

            long long D = dA[idxB];

            vector<char> onDia(m, 0);
            vector<pair<long long,int>> dia; // (coord from a, vertex)
            dia.reserve(m);

            for (int i = 0; i < m; i++) {
                if (dA[i] + dB[i] == D) {
                    onDia[i] = 1;
                    dia.push_back({dA[i], nodes[i]});
                }
            }

            sort(dia.begin(), dia.end());
            int L = (int)dia.size();
            if (L <= 1) {
                // Should not happen for a tree with m>=2, but safe fallback:
                // Connect nodes by chaining with queries.
                for (int i = 1; i < m; i++) {
                    addEdge(nodes[i-1], nodes[i], it.dist(nodes[i-1], nodes[i]));
                }
                continue;
            }

            for (int i = 0; i + 1 < L; i++) {
                int u = dia[i].second;
                int v = dia[i + 1].second;
                long long w = dia[i + 1].first - dia[i].first;
                addEdge(u, v, w);
            }

            unordered_map<long long, int, SplitMix64Hash> coord2idx;
            coord2idx.max_load_factor(0.7f);
            coord2idx.reserve((size_t)L * 2);

            for (int i = 0; i < L; i++) coord2idx.emplace(dia[i].first, i);

            vector<vector<int>> groups(L);
            for (int i = 0; i < L; i++) groups[i].push_back(dia[i].second);

            for (int i = 0; i < m; i++) {
                if (onDia[i]) continue;
                long long num = dA[i] + D - dB[i];
                // num should be even in valid tree metrics
                long long coord = num / 2;
                auto itc = coord2idx.find(coord);
                if (itc == coord2idx.end()) {
                    // Fallback: find by binary search (shouldn't happen)
                    int pos = (int)(lower_bound(dia.begin(), dia.end(), make_pair(coord, -1)) - dia.begin());
                    if (pos < 0) pos = 0;
                    if (pos >= L) pos = L - 1;
                    groups[pos].push_back(nodes[i]);
                } else {
                    groups[itc->second].push_back(nodes[i]);
                }
            }

            for (int i = 0; i < L; i++) {
                if ((int)groups[i].size() > 1) st.push_back(move(groups[i]));
            }
        }

        cout << "!";
        for (auto &[u, v, w] : edges) {
            cout << " " << u << " " << v << " " << w;
        }
        cout << "\n";
        cout.flush();
    }

    return 0;
}