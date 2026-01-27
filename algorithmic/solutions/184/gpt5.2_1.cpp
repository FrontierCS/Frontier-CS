#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t next_u32() { return (uint32_t)next(); }
    int next_int(int lo, int hi) { // inclusive
        return lo + (int)(next() % (uint64_t)(hi - lo + 1));
    }
};

static inline int popcnt64(uint64_t x) { return __builtin_popcountll(x); }
static inline int ctz64(uint64_t x) { return __builtin_ctzll(x); }

struct Solution {
    vector<uint64_t> bits;
    vector<uint8_t> in;
    int sz = 0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int M;
    cin >> N >> M;
    int W = (N + 63) >> 6;

    vector<uint64_t> adj((size_t)N * W, 0);
    vector<int> deg(N, 0);

    auto setEdge = [&](int u, int v) {
        int w = v >> 6;
        uint64_t mask = 1ULL << (v & 63);
        uint64_t &cell = adj[(size_t)u * W + w];
        if (!(cell & mask)) {
            cell |= mask;
            deg[u]++;
        }
    };

    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        setEdge(u, v);
        setEdge(v, u);
    }

    auto hasEdge = [&](int u, int v) -> bool {
        return (adj[(size_t)u * W + (v >> 6)] >> (v & 63)) & 1ULL;
    };

    auto conflict = [&](int v, const vector<uint64_t>& selBits) -> bool {
        const uint64_t* row = &adj[(size_t)v * W];
        for (int w = 0; w < W; w++) {
            if (row[w] & selBits[w]) return true;
        }
        return false;
    };

    auto addVertex = [&](Solution& sol, int v) {
        if (sol.in[v]) return;
        sol.in[v] = 1;
        sol.bits[v >> 6] |= 1ULL << (v & 63);
        sol.sz++;
    };

    auto removeVertex = [&](Solution& sol, int v) {
        if (!sol.in[v]) return;
        sol.in[v] = 0;
        sol.bits[v >> 6] &= ~(1ULL << (v & 63));
        sol.sz--;
    };

    auto augmentToMaximal = [&](Solution& sol) {
        for (int v = 0; v < N; v++) {
            if (sol.in[v]) continue;
            if (!conflict(v, sol.bits)) addVertex(sol, v);
        }
    };

    auto greedyBuild = [&](const vector<int>& order) -> Solution {
        Solution sol;
        sol.bits.assign(W, 0);
        sol.in.assign(N, 0);
        sol.sz = 0;
        for (int v : order) {
            if (!conflict(v, sol.bits)) addVertex(sol, v);
        }
        return sol;
    };

    auto improve_1to2 = [&](Solution& sol, chrono::steady_clock::time_point deadline) {
        vector<vector<int>> buckets(N);
        vector<int> selected;
        selected.reserve(N);

        while (true) {
            if (chrono::steady_clock::now() >= deadline) break;

            augmentToMaximal(sol);

            for (int s = 0; s < N; s++) buckets[s].clear();

            // Build buckets of vertices outside with exactly one conflict in the set.
            for (int u = 0; u < N; u++) {
                if (sol.in[u]) continue;
                const uint64_t* row = &adj[(size_t)u * W];
                int cnt = 0;
                int first = -1;
                for (int w = 0; w < W; w++) {
                    uint64_t x = row[w] & sol.bits[w];
                    if (!x) continue;
                    cnt += popcnt64(x);
                    if (first == -1) first = (w << 6) + ctz64(x);
                    if (cnt > 1) break;
                }
                if (cnt == 1 && first >= 0 && first < N) buckets[first].push_back(u);
            }

            bool changed = false;
            int rs = -1, ru = -1, rv = -1;

            // Find a selected vertex s that can be replaced by two non-adjacent candidates.
            for (int s = 0; s < N && !changed; s++) {
                if (!sol.in[s]) continue;
                auto &L = buckets[s];
                int Lsz = (int)L.size();
                if (Lsz < 2) continue;

                for (int i = 0; i < Lsz && !changed; i++) {
                    int u = L[i];
                    for (int j = i + 1; j < Lsz; j++) {
                        int v = L[j];
                        if (!hasEdge(u, v)) {
                            rs = s; ru = u; rv = v;
                            changed = true;
                            break;
                        }
                    }
                }
            }

            if (!changed) break;

            removeVertex(sol, rs);
            addVertex(sol, ru);
            addVertex(sol, rv);
            // Now make maximal again in next iteration.
        }
    };

    auto validateAndFix = [&](Solution& sol) {
        Solution fixed;
        fixed.bits.assign(W, 0);
        fixed.in.assign(N, 0);
        fixed.sz = 0;
        for (int v = 0; v < N; v++) {
            if (!sol.in[v]) continue;
            if (!conflict(v, fixed.bits)) addVertex(fixed, v);
        }
        augmentToMaximal(fixed);
        sol = std::move(fixed);
    };

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    SplitMix64 rng(seed);

    auto start = chrono::steady_clock::now();
    auto global_deadline = start + chrono::milliseconds(1900);

    Solution best;
    best.bits.assign(W, 0);
    best.in.assign(N, 0);
    best.sz = 0;

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);

    int iter = 0;
    while (chrono::steady_clock::now() < global_deadline) {
        // Build an order with degree bias + randomness (and sometimes pure shuffle).
        if (iter % 6 == 0) {
            // Pure random order
            for (int i = N - 1; i > 0; i--) {
                int j = (int)(rng.next() % (uint64_t)(i + 1));
                swap(order[i], order[j]);
            }
        } else {
            vector<uint32_t> key(N);
            for (int v = 0; v < N; v++) {
                uint32_t noise = (uint32_t)(rng.next() & 2047ULL);
                key[v] = (uint32_t)(deg[v] * 2048u + noise);
            }
            sort(order.begin(), order.end(), [&](int a, int b) {
                return key[a] < key[b];
            });

            // Light local shuffling to diversify
            int window = 24;
            for (int i = 0; i + window < N; i += window) {
                int swaps = 6;
                for (int s = 0; s < swaps; s++) {
                    int a = i + (int)(rng.next() % (uint64_t)window);
                    int b = i + (int)(rng.next() % (uint64_t)window);
                    swap(order[a], order[b]);
                }
            }
        }

        Solution sol = greedyBuild(order);

        auto local_deadline = min(global_deadline, chrono::steady_clock::now() + chrono::milliseconds(250));
        improve_1to2(sol, local_deadline);

        if (sol.sz > best.sz) best = sol;

        iter++;
    }

    validateAndFix(best);

    for (int i = 0; i < N; i++) {
        cout << (best.in[i] ? 1 : 0) << "\n";
    }
    return 0;
}