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

static inline uint64_t pairKey(int u, int v) {
    if (u > v) std::swap(u, v);
    return (uint64_t(uint32_t(u)) << 32) | uint32_t(v);
}

struct Solver {
    int n = 0;
    long long queryCount = 0;

    unordered_map<uint64_t, long long, SplitMix64Hash> distCache;
    unordered_map<uint64_t, long long, SplitMix64Hash> edgeW;
    vector<tuple<int,int,long long>> edges;

    long long ask(int u, int v) {
        if (u == v) return 0;
        uint64_t k = pairKey(u, v);
        auto it = distCache.find(k);
        if (it != distCache.end()) return it->second;

        cout << "? " << u << " " << v << "\n" << std::flush;
        long long d;
        if (!(cin >> d)) exit(0);
        if (d < 0) exit(0);
        distCache.emplace(k, d);
        ++queryCount;
        return d;
    }

    void addEdge(int u, int v, long long w) {
        if (u == v) return;
        uint64_t k = pairKey(u, v);
        auto it = edgeW.find(k);
        if (it == edgeW.end()) {
            edgeW.emplace(k, w);
            edges.emplace_back(u, v, w);
        } else {
            // ignore if already exists; should match
        }
    }

    void processComponent(vector<int>&& comp, vector<vector<int>>& st) {
        int m = (int)comp.size();
        if (m <= 1) return;

        int x = comp[0];
        vector<long long> distX(m, 0);

        long long best = -1;
        int a = x;
        for (int i = 0; i < m; i++) {
            int v = comp[i];
            long long d = (v == x) ? 0LL : ask(x, v);
            distX[i] = d;
            if (d > best) {
                best = d;
                a = v;
            }
        }

        vector<long long> distA(m, 0);
        best = -1;
        int b = a;
        for (int i = 0; i < m; i++) {
            int v = comp[i];
            long long d = (v == a) ? 0LL : ask(a, v);
            distA[i] = d;
            if (d > best) {
                best = d;
                b = v;
            }
        }
        long long D = best;

        vector<long long> distB(m, 0);
        for (int i = 0; i < m; i++) {
            int v = comp[i];
            distB[i] = (v == b) ? 0LL : ask(b, v);
        }

        vector<char> onPath(m, 0);
        vector<pair<long long,int>> path;
        path.reserve(m);
        for (int i = 0; i < m; i++) {
            if (distA[i] + distB[i] == D) {
                onPath[i] = 1;
                path.push_back({distA[i], comp[i]});
            }
        }
        sort(path.begin(), path.end());

        for (int i = 0; i + 1 < (int)path.size(); i++) {
            int u = path[i].second;
            int v = path[i + 1].second;
            long long w = path[i + 1].first - path[i].first;
            addEdge(u, v, w);
        }

        unordered_map<long long, int, SplitMix64Hash> posToIdx;
        posToIdx.reserve(path.size() * 2 + 1);
        for (int i = 0; i < (int)path.size(); i++) {
            posToIdx.emplace(path[i].first, i);
        }

        vector<vector<int>> groups(path.size());
        for (int i = 0; i < m; i++) {
            if (onPath[i]) continue;
            long long xpos = (distA[i] + D - distB[i]) / 2;
            auto it = posToIdx.find(xpos);
            if (it == posToIdx.end()) continue; // should not happen
            groups[it->second].push_back(comp[i]);
        }

        for (int i = 0; i < (int)groups.size(); i++) {
            if (groups[i].empty()) continue;
            vector<int> nxt = std::move(groups[i]);
            nxt.push_back(path[i].second);
            st.push_back(std::move(nxt));
        }
    }

    void solveOne() {
        cin >> n;
        edges.clear();
        edgeW.clear();
        distCache.clear();
        queryCount = 0;

        edgeW.reserve((size_t)max(1, n * 2));
        distCache.reserve((size_t)max(1, n * 40));

        if (n <= 1) {
            cout << "!\n" << std::flush;
            return;
        }

        vector<int> init(n);
        iota(init.begin(), init.end(), 1);

        vector<vector<int>> st;
        st.reserve(n);
        st.push_back(std::move(init));

        while (!st.empty()) {
            vector<int> comp = std::move(st.back());
            st.pop_back();
            processComponent(std::move(comp), st);
        }

        cout << "!";
        // In rare cases due to duplicates we might have < n-1; still output what we have.
        for (auto &e : edges) {
            int u, v;
            long long w;
            tie(u, v, w) = e;
            cout << " " << u << " " << v << " " << w;
        }
        cout << "\n" << std::flush;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    Solver solver;
    while (T--) solver.solveOne();
    return 0;
}