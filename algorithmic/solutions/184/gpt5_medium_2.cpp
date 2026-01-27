#include <bits/stdc++.h>
using namespace std;

static inline int popcnt64(uint64_t x) { return __builtin_popcountll(x); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    int W = (N + 63) >> 6;
    uint64_t tailMask = (N % 64) ? ((1ULL << (N % 64)) - 1ULL) : ~0ULL;

    vector<vector<uint64_t>> adj(N, vector<uint64_t>(W, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u][v >> 6] |= (1ULL << (v & 63));
        adj[v][u >> 6] |= (1ULL << (u & 63));
    }

    auto count_and = [&](const vector<uint64_t>& a, const vector<uint64_t>& b) -> int {
        int res = 0;
        for (int i = 0; i < W; ++i) res += popcnt64(a[i] & b[i]);
        return res;
    };

    auto any_set = [&](const vector<uint64_t>& bs) -> bool {
        for (int i = 0; i < W; ++i) if (bs[i]) return true;
        return false;
    };

    auto build_by_order = [&](const vector<int>& order, vector<uint64_t>& outS) -> int {
        vector<uint64_t> forbidden(W, 0);
        if (W) forbidden[W - 1] &= tailMask; // tail masked, though zero anyway
        outS.assign(W, 0);
        int cnt = 0;
        for (int v : order) {
            uint64_t mask = 1ULL << (v & 63);
            if ((forbidden[v >> 6] & mask) == 0) {
                // add v
                for (int i = 0; i < W; ++i) forbidden[i] |= adj[v][i];
                forbidden[v >> 6] |= mask;
                outS[v >> 6] |= mask;
                ++cnt;
            }
        }
        return cnt;
    };

    auto greedy_min_degree = [&](mt19937_64& rng, vector<uint64_t>& outS) -> int {
        vector<uint64_t> R(W, ~0ULL);
        if (W) R[W - 1] &= tailMask;
        outS.assign(W, 0);
        int cnt = 0;

        while (any_set(R)) {
            int minDeg = INT_MAX;
            vector<int> cand;
            cand.reserve(64);

            for (int wi = 0; wi < W; ++wi) {
                uint64_t word = R[wi];
                while (word) {
                    int t = __builtin_ctzll(word);
                    int v = (wi << 6) + t;
                    // v < N guaranteed by tailMask
                    int deg = 0;
                    for (int i = 0; i < W; ++i) deg += popcnt64(adj[v][i] & R[i]);
                    if (deg < minDeg) {
                        minDeg = deg;
                        cand.clear();
                        cand.push_back(v);
                    } else if (deg == minDeg) {
                        cand.push_back(v);
                    }
                    word &= (word - 1);
                }
            }

            int v = cand[rng() % cand.size()];
            outS[v >> 6] |= (1ULL << (v & 63));
            ++cnt;

            // Remove neighbors
            for (int i = 0; i < W; ++i) R[i] &= ~adj[v][i];
            // Remove v itself
            R[v >> 6] &= ~(1ULL << (v & 63));
        }
        return cnt;
    };

    // Precompute degrees for heuristic orders
    vector<int> deg(N, 0);
    for (int u = 0; u < N; ++u) {
        int d = 0;
        for (int i = 0; i < W; ++i) d += popcnt64(adj[u][i]);
        deg[u] = d;
    }

    // Random engine
    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    // Best solution holder
    vector<uint64_t> bestS(W, 0), curS(W, 0);
    int bestK = 0, curK = 0;

    auto consider = [&](const vector<uint64_t>& S, int K) {
        if (K > bestK) {
            bestK = K;
            bestS = S;
        }
    };

    // 1) Deterministic greedy: dynamic min-degree
    curK = greedy_min_degree(rng, curS);
    consider(curS, curK);

    // 2) Static order: ascending degree
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });
    curK = build_by_order(order, curS);
    consider(curS, curK);

    // 3) Multiple randomized runs within time limit
    auto start = chrono::high_resolution_clock::now();
    const int timeLimitMs = 1800; // be safe under 2s
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start).count() > timeLimitMs) break;

        // Randomized tie-breaking min-degree greedy
        curK = greedy_min_degree(rng, curS);
        consider(curS, curK);

        // Random order greedy
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        curK = build_by_order(order, curS);
        consider(curS, curK);

        // Slightly biased by degree + noise
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng); // break ties randomly
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            // degree with noise: random bits masked to small range
            int na = deg[a] + int(rng() & 3ULL);
            int nb = deg[b] + int(rng() & 3ULL);
            if (na != nb) return na < nb;
            return a < b;
        });
        curK = build_by_order(order, curS);
        consider(curS, curK);
    }

    // Output result
    for (int i = 0; i < N; ++i) {
        int bit = (bestS[i >> 6] >> (i & 63)) & 1ULL;
        cout << bit << '\n';
    }
    return 0;
}