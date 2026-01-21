#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int N, M;
    vector<int> A, B;
    bool need[41][41];
    mt19937_64 rng;

    Solver(int n, int m, const vector<int>& a, const vector<int>& b)
        : N(n), M(m), A(a), B(b) {
        memset(need, 0, sizeof(need));
        for (int i = 0; i < M; ++i) {
            int u = A[i];
            int v = B[i];
            if (u > v) swap(u, v);
            need[u][v] = true;
        }
        rng.seed((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    pair<int, vector<vector<int>>> attempt(int K) {
        const int PEN_MISS = 10;
        const int PEN_FORBID = 100;
        const int PEN_UNUSED = 50;

        vector<vector<int>> grid(K, vector<int>(K));
        vector<int> colorCount(N + 1, 0);
        int curAdj[41][41];
        memset(curAdj, 0, sizeof(curAdj));

        uniform_int_distribution<int> colorDist(1, N);

        // Initial random grid
        for (int r = 0; r < K; ++r) {
            for (int c = 0; c < K; ++c) {
                int col = colorDist(rng);
                grid[r][c] = col;
            }
        }
        // Ensure each color appears at least once in first N cells
        for (int i = 0; i < N; ++i) {
            int r = i / K;
            int c = i % K;
            grid[r][c] = i + 1;
        }

        // Recompute colorCount and adjacency
        auto recompute_all = [&]() -> int {
            fill(colorCount.begin(), colorCount.end(), 0);
            memset(curAdj, 0, sizeof(curAdj));
            for (int r = 0; r < K; ++r) {
                for (int c = 0; c < K; ++c) {
                    int col = grid[r][c];
                    colorCount[col]++;
                }
            }
            for (int r = 0; r < K; ++r) {
                for (int c = 0; c < K; ++c) {
                    int col = grid[r][c];
                    if (c + 1 < K) {
                        int col2 = grid[r][c + 1];
                        if (col != col2) {
                            int i = min(col, col2);
                            int j = max(col, col2);
                            curAdj[i][j]++;
                        }
                    }
                    if (r + 1 < K) {
                        int col2 = grid[r + 1][c];
                        if (col != col2) {
                            int i = min(col, col2);
                            int j = max(col, col2);
                            curAdj[i][j]++;
                        }
                    }
                }
            }
            int pen = 0;
            for (int col = 1; col <= N; ++col) {
                if (colorCount[col] == 0) pen += PEN_UNUSED;
            }
            for (int i = 1; i <= N; ++i) {
                for (int j = i + 1; j <= N; ++j) {
                    int cnt = curAdj[i][j];
                    if (need[i][j]) {
                        if (cnt == 0) pen += PEN_MISS;
                    } else {
                        if (cnt > 0) pen += PEN_FORBID;
                    }
                }
            }
            return pen;
        };

        int totalPenalty = recompute_all();
        vector<vector<int>> bestGrid = grid;
        int bestPenalty = totalPenalty;

        if (bestPenalty == 0) return {0, bestGrid};

        long long TOT_ITERS = 400LL * K * K;
        if (TOT_ITERS < 20000) TOT_ITERS = 20000;
        const double Tstart = 2.0;
        const double Tend = 0.01;
        double alpha = pow(Tend / Tstart, 1.0 / (double)TOT_ITERS);
        double T = Tstart;

        uniform_real_distribution<double> realDist(0.0, 1.0);

        struct PairDelta {
            int u, v;
            int delta;
        };

        for (long long it = 0; it < TOT_ITERS && bestPenalty > 0; ++it) {
            int r = (int)(rng() % K);
            int c = (int)(rng() % K);
            int oldColor = grid[r][c];
            if (N == 1) break; // should not happen here because N>1 in this attempt
            int newColor = (int)(rng() % (N - 1)) + 1;
            if (newColor >= oldColor) ++newColor;
            if (newColor == oldColor) continue;

            int deltaColor = 0;
            int oldCountA = colorCount[oldColor];
            int oldCountB = colorCount[newColor];
            if (oldCountA == 1) deltaColor += PEN_UNUSED;
            if (oldCountB == 0) deltaColor -= PEN_UNUSED;

            PairDelta pd[8];
            int pdSize = 0;
            auto addDelta = [&](int u, int v, int d) {
                if (u == v) return;
                if (u > v) swap(u, v);
                for (int k = 0; k < pdSize; ++k) {
                    if (pd[k].u == u && pd[k].v == v) {
                        pd[k].delta += d;
                        return;
                    }
                }
                pd[pdSize].u = u;
                pd[pdSize].v = v;
                pd[pdSize].delta = d;
                ++pdSize;
            };

            auto process_neighbor = [&](int nr, int nc) {
                int x = grid[nr][nc];
                if (x == oldColor) {
                    if (newColor != x) {
                        addDelta(min(newColor, x), max(newColor, x), +1);
                    }
                } else if (x == newColor) {
                    addDelta(min(oldColor, x), max(oldColor, x), -1);
                } else {
                    addDelta(min(oldColor, x), max(oldColor, x), -1);
                    addDelta(min(newColor, x), max(newColor, x), +1);
                }
            };

            if (r > 0) process_neighbor(r - 1, c);
            if (r + 1 < K) process_neighbor(r + 1, c);
            if (c > 0) process_neighbor(r, c - 1);
            if (c + 1 < K) process_neighbor(r, c + 1);

            int deltaEdges = 0;
            for (int k = 0; k < pdSize; ++k) {
                int u = pd[k].u;
                int v = pd[k].v;
                int d = pd[k].delta;
                if (d == 0) continue;
                int oldCnt = curAdj[u][v];
                int newCnt = oldCnt + d;
                int oldP, newP;
                if (need[u][v]) {
                    oldP = (oldCnt == 0 ? PEN_MISS : 0);
                    newP = (newCnt == 0 ? PEN_MISS : 0);
                } else {
                    oldP = (oldCnt > 0 ? PEN_FORBID : 0);
                    newP = (newCnt > 0 ? PEN_FORBID : 0);
                }
                deltaEdges += newP - oldP;
            }

            int delta = deltaColor + deltaEdges;
            int newPenalty = totalPenalty + delta;

            bool accept = false;
            if (delta <= 0) {
                accept = true;
            } else {
                double prob = exp(- (double)delta / T);
                if (realDist(rng) < prob) accept = true;
            }

            if (accept) {
                grid[r][c] = newColor;
                colorCount[oldColor]--;
                colorCount[newColor]++;
                for (int k = 0; k < pdSize; ++k) {
                    int u = pd[k].u;
                    int v = pd[k].v;
                    int d = pd[k].delta;
                    if (d != 0) curAdj[u][v] += d;
                }
                totalPenalty = newPenalty;
                if (totalPenalty < bestPenalty) {
                    bestPenalty = totalPenalty;
                    bestGrid = grid;
                    if (bestPenalty == 0) break;
                }
            }

            T *= alpha;
            if (T < Tend) T = Tend;
        }

        return {bestPenalty, bestGrid};
    }

    vector<vector<int>> solve() {
        if (N == 1) {
            return vector<vector<int>>(1, vector<int>(1, 1));
        }

        int K = min(240, max(3 * N, 5));
        int bestPenalty = INT_MAX;
        vector<vector<int>> bestGrid;

        int TRIES = 3;
        for (int t = 0; t < TRIES; ++t) {
            auto res = attempt(K);
            if (res.first < bestPenalty) {
                bestPenalty = res.first;
                bestGrid = res.second;
            }
            if (bestPenalty == 0) break;
        }

        // As a fallback, if somehow not perfect, just return bestGrid (may be invalid in worst case).
        return bestGrid;
    }
};

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    Solver solver(N, M, A, B);
    return solver.solve();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; ++i) cin >> A[i] >> B[i];
        vector<vector<int>> C = create_map(N, M, A, B);
        int P = (int)C.size();
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << (int)C[i].size() << (i + 1 == P ? '\n' : ' ');
        }
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                if (j) cout << ' ';
                cout << C[i][j];
            }
            cout << "\n";
        }
    }
    return 0;
}