#include <bits/stdc++.h>
using namespace std;

static inline bool intersectsBits(const vector<uint64_t>& a, const vector<uint64_t>& b) {
    for (size_t i = 0; i < a.size(); ++i) if (a[i] & b[i]) return true;
    return false;
}

static inline void setBit(vector<uint64_t>& bits, int v) {
    bits[(unsigned)v >> 6] |= 1ULL << (v & 63);
}
static inline void clearBit(vector<uint64_t>& bits, int v) {
    bits[(unsigned)v >> 6] &= ~(1ULL << (v & 63));
}

static vector<int> makeOrder(int N, const vector<int>& deg, mt19937_64& rng) {
    int type = (int)(rng() % 3);
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    if (type == 0) {
        vector<pair<uint64_t,int>> keys;
        keys.reserve(N);
        for (int v = 0; v < N; ++v) {
            uint64_t noise = (uint64_t)(rng() & 0xffffffffULL);
            uint64_t key = (uint64_t)deg[v] * (1ULL << 32) + noise;
            keys.push_back({key, v});
        }
        sort(keys.begin(), keys.end(), [](auto &a, auto &b){ return a.first < b.first; });
        for (int i = 0; i < N; ++i) order[i] = keys[i].second;
    } else if (type == 1) {
        shuffle(order.begin(), order.end(), rng);
    } else {
        // Slightly different bias: prioritize very low degree more aggressively
        vector<pair<uint64_t,int>> keys;
        keys.reserve(N);
        for (int v = 0; v < N; ++v) {
            uint64_t d = (uint64_t)deg[v];
            uint64_t keyBase = d * d; // emphasize low degrees
            uint64_t noise = (uint64_t)(rng() & 0xffffULL);
            uint64_t key = (keyBase << 16) + noise;
            keys.push_back({key, v});
        }
        sort(keys.begin(), keys.end(), [](auto &a, auto &b){ return a.first < b.first; });
        for (int i = 0; i < N; ++i) order[i] = keys[i].second;
    }
    return order;
}

static inline void augmentMaximal(
    vector<unsigned char>& inS,
    vector<int>& cnt,
    int& sz,
    const vector<vector<int>>& adj,
    mt19937_64& rng
) {
    int N = (int)inS.size();
    vector<int> perm(N);
    iota(perm.begin(), perm.end(), 0);
    shuffle(perm.begin(), perm.end(), rng);

    for (int v : perm) {
        if (!inS[v] && cnt[v] == 0) {
            inS[v] = 1;
            ++sz;
            for (int w : adj[v]) ++cnt[w];
        }
    }
}

static inline int findOneSelectedNeighbor(int v, const vector<unsigned char>& inS, const vector<vector<int>>& adj) {
    for (int w : adj[v]) if (inS[w]) return w;
    return -1;
}

static inline pair<int,int> findTwoSelectedNeighbors(int v, const vector<unsigned char>& inS, const vector<vector<int>>& adj) {
    int a = -1, b = -1;
    for (int w : adj[v]) {
        if (inS[w]) {
            if (a == -1) a = w;
            else { b = w; break; }
        }
    }
    return {a, b};
}

static inline void removeVertex(int u, vector<unsigned char>& inS, vector<int>& cnt, int& sz, const vector<vector<int>>& adj) {
    inS[u] = 0;
    --sz;
    for (int w : adj[u]) --cnt[w];
}

static inline void addVertex(int v, vector<unsigned char>& inS, vector<int>& cnt, int& sz, const vector<vector<int>>& adj) {
    inS[v] = 1;
    ++sz;
    for (int w : adj[v]) ++cnt[w];
}

static void localImprove(
    vector<unsigned char>& inS,
    vector<int>& cnt,
    int& sz,
    const vector<vector<int>>& adj,
    mt19937_64& rng
) {
    int N = (int)inS.size();
    vector<unsigned char> inS_snap(N);
    vector<int> cnt_snap(N);

    const int maxSteps = 200;
    const int maxCand1 = 250;
    const int maxCand2 = 120;

    for (int step = 0; step < maxSteps; ++step) {
        int oldSz = sz;
        bool improved = false;

        vector<int> c1;
        c1.reserve(N);
        for (int v = 0; v < N; ++v) if (!inS[v] && cnt[v] == 1) c1.push_back(v);
        shuffle(c1.begin(), c1.end(), rng);

        int limit1 = min((int)c1.size(), maxCand1);
        for (int i = 0; i < limit1; ++i) {
            int v = c1[i];
            int u = findOneSelectedNeighbor(v, inS, adj);
            if (u < 0) continue;

            copy(inS.begin(), inS.end(), inS_snap.begin());
            copy(cnt.begin(), cnt.end(), cnt_snap.begin());
            int sz_snap = sz;

            removeVertex(u, inS, cnt, sz, adj);
            // after removing u, v should have cnt[v]==0
            if (cnt[v] != 0) {
                copy(inS_snap.begin(), inS_snap.end(), inS.begin());
                copy(cnt_snap.begin(), cnt_snap.end(), cnt.begin());
                sz = sz_snap;
                continue;
            }
            addVertex(v, inS, cnt, sz, adj);
            augmentMaximal(inS, cnt, sz, adj, rng);

            if (sz > oldSz) { improved = true; break; }

            copy(inS_snap.begin(), inS_snap.end(), inS.begin());
            copy(cnt_snap.begin(), cnt_snap.end(), cnt.begin());
            sz = sz_snap;
        }

        if (!improved) {
            vector<int> c2;
            c2.reserve(N);
            for (int v = 0; v < N; ++v) if (!inS[v] && cnt[v] == 2) c2.push_back(v);
            shuffle(c2.begin(), c2.end(), rng);

            int limit2 = min((int)c2.size(), maxCand2);
            for (int i = 0; i < limit2; ++i) {
                int v = c2[i];
                auto [u1, u2] = findTwoSelectedNeighbors(v, inS, adj);
                if (u1 < 0 || u2 < 0) continue;

                copy(inS.begin(), inS.end(), inS_snap.begin());
                copy(cnt.begin(), cnt.end(), cnt_snap.begin());
                int sz_snap = sz;

                removeVertex(u1, inS, cnt, sz, adj);
                if (inS[u2]) removeVertex(u2, inS, cnt, sz, adj);
                if (cnt[v] != 0) {
                    copy(inS_snap.begin(), inS_snap.end(), inS.begin());
                    copy(cnt_snap.begin(), cnt_snap.end(), cnt.begin());
                    sz = sz_snap;
                    continue;
                }
                addVertex(v, inS, cnt, sz, adj);
                augmentMaximal(inS, cnt, sz, adj, rng);

                if (sz > oldSz) { improved = true; break; }

                copy(inS_snap.begin(), inS_snap.end(), inS.begin());
                copy(cnt_snap.begin(), cnt_snap.end(), cnt.begin());
                sz = sz_snap;
            }
        }

        if (!improved) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int M;
    cin >> N >> M;
    int W = (N + 63) / 64;

    vector<vector<uint64_t>> adjBits(N, vector<uint64_t>(W, 0ULL));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adjBits[u][(unsigned)v >> 6] |= 1ULL << (v & 63);
        adjBits[v][(unsigned)u >> 6] |= 1ULL << (u & 63);
    }

    vector<vector<int>> adj(N);
    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) {
        adj[i].reserve(N);
        for (int k = 0; k < W; ++k) {
            uint64_t x = adjBits[i][k];
            while (x) {
                int b = __builtin_ctzll(x);
                int j = (k << 6) + b;
                if (j < N) adj[i].push_back(j);
                x &= x - 1;
            }
        }
        deg[i] = (int)adj[i].size();
    }

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&rng);

    vector<unsigned char> bestInS(N, 0);
    int bestSz = -1;

    auto start = chrono::steady_clock::now();
    const double timeLimit = 1.90;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed >= timeLimit) break;

        vector<int> order = makeOrder(N, deg, rng);

        vector<unsigned char> inS(N, 0);
        vector<uint64_t> setBits(W, 0ULL);
        int sz = 0;

        for (int v : order) {
            if (!intersectsBits(adjBits[v], setBits)) {
                inS[v] = 1;
                ++sz;
                setBit(setBits, v);
            }
        }

        vector<int> cnt(N, 0);
        for (int u = 0; u < N; ++u) if (inS[u]) for (int w : adj[u]) ++cnt[w];

        augmentMaximal(inS, cnt, sz, adj, rng);
        localImprove(inS, cnt, sz, adj, rng);

        if (sz > bestSz) {
            bestSz = sz;
            bestInS = inS;
        }
    }

    if (bestSz < 0) {
        bestSz = 0;
        fill(bestInS.begin(), bestInS.end(), 0);
    }

    // Safety repair (should be unnecessary, but ensures validity)
    vector<uint64_t> finalBits(W, 0ULL);
    for (int i = 0; i < N; ++i) if (bestInS[i]) setBit(finalBits, i);
    for (int i = 0; i < N; ++i) {
        if (!bestInS[i]) continue;
        if (intersectsBits(adjBits[i], finalBits)) {
            bestInS[i] = 0;
            clearBit(finalBits, i);
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestInS[i] ? 1 : 0) << '\n';
    }
    return 0;
}