#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    long long M;
    if (!(cin >> N >> M)) return 0;
    
    int W = (N + 63) >> 6;
    uint64_t lastMask = (N % 64 == 0) ? ~0ULL : ((1ULL << (N % 64)) - 1ULL);
    
    vector<vector<uint64_t>> adjBits(N, vector<uint64_t>(W, 0));
    
    for (long long e = 0; e < M; ++e) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        adjBits[u][v >> 6] |= (1ULL << (v & 63));
        adjBits[v][u >> 6] |= (1ULL << (u & 63));
    }
    
    vector<vector<int>> neighbors(N);
    vector<int> deg(N, 0);
    
    auto buildNeighbors = [&]() {
        for (int i = 0; i < N; ++i) {
            neighbors[i].clear();
            for (int w = 0; w < W; ++w) {
                uint64_t word = adjBits[i][w];
                if (w == W - 1) word &= lastMask;
                while (word) {
                    int b = __builtin_ctzll(word);
                    int j = (w << 6) + b;
                    neighbors[i].push_back(j);
                    word &= word - 1;
                }
            }
            deg[i] = (int)neighbors[i].size();
        }
    };
    buildNeighbors();
    
    auto greedyMIS = [&](const vector<uint32_t>& rkey) -> vector<char> {
        vector<char> active(N, 1), chosen(N, 0);
        vector<int> degActive = deg;
        
        struct Node { int deg; uint32_t r; int idx; };
        struct Cmp {
            bool operator()(const Node& a, const Node& b) const {
                if (a.deg != b.deg) return a.deg > b.deg;
                return a.r > b.r;
            }
        };
        priority_queue<Node, vector<Node>, Cmp> pq;
        for (int i = 0; i < N; ++i) pq.push(Node{degActive[i], rkey[i], i});
        int rem = N;
        while (rem > 0) {
            Node nd;
            do {
                if (pq.empty()) break;
                nd = pq.top(); pq.pop();
            } while (!active[nd.idx] || nd.deg != degActive[nd.idx]);
            if (!active[nd.idx]) break;
            int v = nd.idx;
            chosen[v] = 1;
            active[v] = 0;
            rem--;
            for (int j : neighbors[v]) {
                if (active[j]) {
                    active[j] = 0;
                    rem--;
                    for (int k : neighbors[j]) {
                        if (active[k]) {
                            degActive[k]--;
                            pq.push(Node{degActive[k], rkey[k], k});
                        }
                    }
                }
            }
        }
        return chosen;
    };
    
    auto two_improve = [&](vector<char>& chosen) {
        vector<int> c(N, 0);
        for (int u = 0; u < N; ++u) if (chosen[u]) {
            for (int v : neighbors[u]) c[v]++;
        }
        while (true) {
            bool applied = false;
            for (int u = 0; u < N && !applied; ++u) if (chosen[u]) {
                vector<uint64_t> Abits(W, 0);
                vector<int> A;
                for (int a : neighbors[u]) if (!chosen[a] && c[a] == 1) {
                    Abits[a >> 6] |= (1ULL << (a & 63));
                    A.push_back(a);
                }
                if ((int)A.size() >= 2) {
                    for (int a : A) {
                        int block = a >> 6, offset = a & 63;
                        for (int w = 0; w < W; ++w) {
                            uint64_t x = Abits[w] & ~adjBits[a][w];
                            if (w == W - 1) x &= lastMask;
                            if (w == block) x &= ~(1ULL << offset);
                            if (x) {
                                int b = (w << 6) + __builtin_ctzll(x);
                                chosen[u] = 0;
                                chosen[a] = chosen[b] = 1;
                                for (int v : neighbors[u]) c[v]--;
                                for (int v : neighbors[a]) c[v]++;
                                for (int v : neighbors[b]) c[v]++;
                                applied = true;
                                break;
                            }
                        }
                        if (applied) break;
                    }
                }
            }
            if (!applied) break;
        }
    };
    
    auto countChosen = [&](const vector<char>& s) {
        int cnt = 0;
        for (char x : s) cnt += (x != 0);
        return cnt;
    };
    
    // Time-bounded multi-start greedy + 2-improvement
    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_MS = 1900.0;
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    vector<char> best(N, 0);
    int bestK = -1;
    
    vector<uint32_t> rkey(N);
    int iter = 0;
    while (true) {
        double elapsed = chrono::duration<double, milli>(chrono::steady_clock::now() - start).count();
        if (elapsed > TIME_LIMIT_MS) break;
        for (int i = 0; i < N; ++i) rkey[i] = uint32_t(rng());
        vector<char> cur = greedyMIS(rkey);
        two_improve(cur);
        int K = countChosen(cur);
        if (K > bestK) {
            bestK = K;
            best = cur;
        }
        iter++;
        // Optional: early exit if we reached N (perfect independent set in edgeless graph)
        if (bestK == N) break;
    }
    
    // Output result
    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}