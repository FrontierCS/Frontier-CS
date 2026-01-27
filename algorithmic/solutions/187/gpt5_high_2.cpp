#include <bits/stdc++.h>
using namespace std;

struct DSaturSolver {
    int N;
    vector<vector<int>> H;
    vector<int> degH;
    mt19937 rng;

    DSaturSolver(int n, const vector<vector<int>>& H_adj, const vector<int>& deg)
        : N(n), H(H_adj), degH(deg), rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()) {}

    pair<vector<int>, int> run_once() {
        vector<int> color(N, 0);
        vector<int> sat(N, 0);
        int K = 0;

        int Bcols = (N + 63) >> 6;
        vector<vector<unsigned long long>> used(N, vector<unsigned long long>(Bcols, 0ULL));

        auto set_used = [&](int v, int c) {
            int idx = (c - 1) >> 6;
            int off = (c - 1) & 63;
            unsigned long long mask = 1ULL << off;
            if ((used[v][idx] & mask) == 0ULL) {
                used[v][idx] |= mask;
                sat[v]++;
            }
        };
        auto is_used = [&](int v, int c) -> bool {
            int idx = (c - 1) >> 6;
            int off = (c - 1) & 63;
            return (used[v][idx] >> off) & 1ULL;
        };

        // Choose the first vertex: maximum degree in H, break ties randomly
        int first = -1;
        int bestDeg = -1;
        int countTie = 0;
        for (int v = 0; v < N; ++v) {
            if (degH[v] > bestDeg) {
                bestDeg = degH[v];
                first = v;
                countTie = 1;
            } else if (degH[v] == bestDeg) {
                ++countTie;
                if ((uint32_t)rng() % countTie == 0) first = v;
            }
        }

        for (int step = 0; step < N; ++step) {
            int u;
            if (step == 0) {
                u = first;
            } else {
                int bestSat = -1;
                int bestDegNow = -1;
                int chosen = -1;
                int ties = 0;
                for (int v = 0; v < N; ++v) {
                    if (color[v] != 0) continue;
                    int s = sat[v];
                    if (s > bestSat) {
                        bestSat = s;
                        bestDegNow = degH[v];
                        chosen = v;
                        ties = 1;
                    } else if (s == bestSat) {
                        if (degH[v] > bestDegNow) {
                            bestDegNow = degH[v];
                            chosen = v;
                            ties = 1;
                        } else if (degH[v] == bestDegNow) {
                            ++ties;
                            if ((uint32_t)rng() % ties == 0) chosen = v;
                        }
                    }
                }
                u = chosen;
            }

            // assign minimal available color
            int c = 1;
            for (; c <= K; ++c) if (!is_used(u, c)) break;
            if (c == K + 1) K++;
            color[u] = c;

            // update saturation of neighbors
            for (int v : H[u]) {
                if (color[v] == 0) set_used(v, c);
            }
        }

        return {color, K};
    }

    int try_reduce(vector<int>& color, int K) {
        vector<vector<int>> classes(K + 1);
        for (int v = 0; v < N; ++v) classes[color[v]].push_back(v);

        bool improved = true;
        while (improved) {
            improved = false;
            while (true) {
                if (K <= 1) break;
                bool movedAny = false;
                vector<int> remain;
                remain.reserve(classes[K].size());
                for (int u : classes[K]) {
                    vector<char> forbid(K + 1, 0);
                    for (int w : H[u]) {
                        int cw = color[w];
                        if (cw >= 1 && cw <= K) forbid[cw] = 1;
                    }
                    int target = 0;
                    for (int c = 1; c < K; ++c) {
                        if (!forbid[c]) { target = c; break; }
                    }
                    if (target) {
                        color[u] = target;
                        classes[target].push_back(u);
                        movedAny = true;
                        improved = true;
                    } else {
                        remain.push_back(u);
                    }
                }
                classes[K].swap(remain);
                if (classes[K].empty()) {
                    classes.pop_back();
                    --K;
                } else if (!movedAny) {
                    break;
                }
            }
        }
        return K;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;

    int B = (N + 63) >> 6;
    vector<vector<unsigned long long>> G(N, vector<unsigned long long>(B, 0ULL));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        G[u][v >> 6] |= 1ULL << (v & 63);
        G[v][u >> 6] |= 1ULL << (u & 63);
    }

    auto hasEdge = [&](int u, int v) -> bool {
        return (G[u][v >> 6] >> (v & 63)) & 1ULL;
    };

    vector<vector<int>> H(N);
    vector<int> degH(N, 0);
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (!hasEdge(i, j)) {
                H[i].push_back(j);
                H[j].push_back(i);
                degH[i]++;
                degH[j]++;
            }
        }
    }

    DSaturSolver solver(N, H, degH);

    vector<int> bestColor(N, 1);
    int bestK = N;

    auto start = chrono::steady_clock::now();
    const double timeLimitSec = 1.85; // keep margin under 2.0s

    int runs = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > timeLimitSec && runs > 0) break;

        auto res = solver.run_once();
        vector<int> col = move(res.first);
        int K = res.second;

        K = solver.try_reduce(col, K);

        if (K < bestK) {
            bestK = K;
            bestColor = col;
            if (bestK == 1) break;
        }
        runs++;
        // Small safeguard against too many runs even if extremely fast
        if (runs > 200) break;
    }

    for (int i = 0; i < N; ++i) {
        cout << bestColor[i] << '\n';
    }
    return 0;
}