#include <bits/stdc++.h>
using namespace std;

class FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

public:
    bool readInt(int &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
            if (!c) break;
        }
        out = x;
        return true;
    }
};

struct EdgeRef {
    int to;
    int id;
};

static inline uint64_t xorshift64(uint64_t &x) {
    x ^= x << 7;
    x ^= x >> 9;
    return x;
}

int main() {
    FastScanner fs;
    int N, M_in;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M_in);

    vector<uint64_t> keys;
    keys.reserve(M_in);
    for (int i = 0; i < M_in; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        --u; --v;
        if (u > v) swap(u, v);
        uint64_t key = (uint64_t)(uint32_t)u << 32 | (uint64_t)(uint32_t)v;
        keys.push_back(key);
    }

    sort(keys.begin(), keys.end());
    keys.erase(unique(keys.begin(), keys.end()), keys.end());
    int M = (int)keys.size();

    vector<int> eu(M), ev(M);
    vector<int> deg(N, 0);
    for (int id = 0; id < M; id++) {
        int u = (int)(keys[id] >> 32);
        int v = (int)(keys[id] & 0xffffffffu);
        eu[id] = u;
        ev[id] = v;
        deg[u]++; deg[v]++;
    }

    vector<vector<EdgeRef>> g(N);
    for (int i = 0; i < N; i++) g[i].reserve(deg[i]);
    for (int id = 0; id < M; id++) {
        int u = eu[id], v = ev[id];
        g[u].push_back({v, id});
        g[v].push_back({u, id});
    }

    auto minimalize = [&](vector<char> &inCover) {
        vector<int> outCnt(N, 0);
        vector<int> removable;
        removable.reserve(N);

        for (int v = 0; v < N; v++) {
            if (!inCover[v]) continue;
            int cnt = 0;
            for (const auto &er : g[v]) {
                if (!inCover[er.to]) { cnt = 1; break; }
            }
            outCnt[v] = cnt;
            if (cnt == 0) removable.push_back(v);
        }

        sort(removable.begin(), removable.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] < deg[b];
            return a < b;
        });

        for (int v : removable) {
            if (!inCover[v] || outCnt[v] != 0) continue;
            inCover[v] = 0;
            for (const auto &er : g[v]) {
                int u = er.to;
                if (inCover[u]) outCnt[u]++; // now u has an outside neighbor
            }
        }
    };

    auto isValid = [&](const vector<char> &inCover) -> bool {
        for (int id = 0; id < M; id++) {
            if (!inCover[eu[id]] && !inCover[ev[id]]) return false;
        }
        return true;
    };

    auto coverSize = [&](const vector<char> &inCover) -> int {
        int s = 0;
        for (char c : inCover) s += (c != 0);
        return s;
    };

    auto coverMatching = [&]() -> vector<char> {
        vector<int> mate(N, -1);
        vector<char> inCover(N, 0);
        for (int id = 0; id < M; id++) {
            int u = eu[id], v = ev[id];
            if (mate[u] == -1 && mate[v] == -1) {
                mate[u] = v;
                mate[v] = u;
                inCover[u] = 1;
                inCover[v] = 1;
            }
        }
        minimalize(inCover);
        return inCover;
    };

    auto coverGreedy = [&]() -> vector<char> {
        vector<int> uncoveredDeg = deg;
        vector<char> inCover(N, 0);
        vector<char> edgeCov(M, 0);

        priority_queue<pair<int,int>> pq;
        for (int v = 0; v < N; v++) pq.push({uncoveredDeg[v], v});

        long long remEdges = M;
        while (remEdges > 0) {
            int v = -1;
            while (!pq.empty()) {
                auto [d, x] = pq.top();
                pq.pop();
                if (inCover[x]) continue;
                if (d != uncoveredDeg[x]) continue;
                v = x;
                break;
            }
            if (v == -1) {
                // Fallback scan (should rarely happen)
                int best = -1, bestd = -1;
                for (int i = 0; i < N; i++) {
                    if (!inCover[i] && uncoveredDeg[i] > bestd) {
                        bestd = uncoveredDeg[i];
                        best = i;
                    }
                }
                if (best == -1) break;
                v = best;
            }

            if (uncoveredDeg[v] <= 0) break;

            inCover[v] = 1;
            for (const auto &er : g[v]) {
                int id = er.id;
                if (edgeCov[id]) continue;
                edgeCov[id] = 1;
                remEdges--;
                int u = er.to;
                if (!inCover[u]) {
                    uncoveredDeg[u]--;
                    pq.push({uncoveredDeg[u], u});
                }
            }
            uncoveredDeg[v] = 0;
        }

        minimalize(inCover);
        return inCover;
    };

    auto coverLeafMatching = [&]() -> vector<char> {
        vector<char> inCover(N, 0);
        vector<char> inGraph(N, 1);
        vector<int> degRem = deg;
        vector<char> activeEdge(M, 1);
        vector<int> ptr(N, 0);

        deque<int> q;
        for (int v = 0; v < N; v++) if (degRem[v] == 1) q.push_back(v);

        auto findNeighbor = [&](int v) -> int {
            int &i = ptr[v];
            while (i < (int)g[v].size()) {
                const auto &er = g[v][i];
                if (activeEdge[er.id] && inGraph[er.to]) return er.to;
                i++;
            }
            return -1;
        };

        while (!q.empty()) {
            int u = q.front(); q.pop_front();
            if (!inGraph[u]) continue;
            if (degRem[u] != 1) continue;

            int v = findNeighbor(u);
            if (v == -1) {
                inGraph[u] = 0;
                degRem[u] = 0;
                continue;
            }
            if (!inGraph[v]) continue;

            inCover[v] = 1;

            // Remove v: select into cover, deactivate all incident edges.
            inGraph[v] = 0;
            for (const auto &er : g[v]) {
                int id = er.id;
                if (!activeEdge[id]) continue;
                activeEdge[id] = 0;
                int w = er.to;
                if (inGraph[w]) {
                    degRem[w]--;
                    if (degRem[w] == 1) q.push_back(w);
                }
            }

            // Leaf u becomes isolated
            if (inGraph[u]) {
                inGraph[u] = 0;
                degRem[u] = 0;
            }
        }

        vector<int> mate(N, -1);
        for (int id = 0; id < M; id++) {
            if (!activeEdge[id]) continue;
            int u = eu[id], v = ev[id];
            if (!inGraph[u] || !inGraph[v]) continue;
            if (mate[u] == -1 && mate[v] == -1) {
                mate[u] = v;
                mate[v] = u;
                inCover[u] = 1;
                inCover[v] = 1;
            }
        }

        minimalize(inCover);
        return inCover;
    };

    auto coverFromMIS = [&](const vector<int> &ord) -> vector<char> {
        vector<char> state(N, 0); // 0 free, 1 in IS, 2 blocked
        for (int v : ord) {
            if (state[v] != 0) continue;
            state[v] = 1;
            for (const auto &er : g[v]) {
                int u = er.to;
                if (state[u] == 0) state[u] = 2;
            }
        }
        vector<char> inCover(N, 1);
        for (int v = 0; v < N; v++) if (state[v] == 1) inCover[v] = 0;
        minimalize(inCover);
        return inCover;
    };

    vector<char> bestCover(N, 1);
    int bestSize = N;

    auto consider = [&](vector<char> cand) {
        if (!isValid(cand)) return;
        int sz = coverSize(cand);
        if (sz < bestSize) {
            bestSize = sz;
            bestCover.swap(cand);
        }
    };

    consider(coverLeafMatching());
    consider(coverMatching());
    consider(coverGreedy());

    vector<int> ordDeg(N);
    iota(ordDeg.begin(), ordDeg.end(), 0);
    sort(ordDeg.begin(), ordDeg.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });
    consider(coverFromMIS(ordDeg));

    vector<int> ordRand(N);
    iota(ordRand.begin(), ordRand.end(), 0);
    uint64_t seed = 0x9e3779b97f4a7c15ULL;
    for (int t = 0; t < 3; t++) {
        // Fisher-Yates shuffle
        for (int i = N - 1; i >= 1; i--) {
            uint64_t r = xorshift64(seed);
            int j = (int)(r % (uint64_t)(i + 1));
            swap(ordRand[i], ordRand[j]);
        }
        consider(coverFromMIS(ordRand));
    }

    if (!isValid(bestCover)) {
        // Ultimate fallback
        fill(bestCover.begin(), bestCover.end(), 1);
    }

    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int i = 0; i < N; i++) {
        cout << (bestCover[i] ? 1 : 0) << '\n';
    }
    return 0;
}