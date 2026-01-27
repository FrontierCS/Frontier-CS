#include <bits/stdc++.h>
using namespace std;

static mt19937 rng(712367821);

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    if (N == 1) {
        return vector<vector<int>>(1, vector<int>(1, 1));
    }

    // adjacency matrix of graph
    vector<vector<char>> isEdge(N + 1, vector<char>(N + 1, 0));
    for (int i = 0; i < M; ++i) {
        int u = A[i];
        int v = B[i];
        isEdge[u][v] = isEdge[v][u] = 1;
    }

    // parameters
    const int S_BAD = 1000;
    const int S_MISS = 10;
    const int S_COLOR = 1;

    int K = max(5, N); // use a single K per test, square grid

    vector<vector<int>> bestGrid;
    bool solved = false;

    int MAX_RESTARTS = 6;
    int BASE_ITERS = max(200000, K * K * 400);

    for (int rest = 0; rest < MAX_RESTARTS && !solved; ++rest) {
        vector<vector<int>> grid(K, vector<int>(K));
        vector<int> cntColor(N + 1, 0);
        vector<vector<int>> adjCount(N + 1, vector<int>(N + 1, 0));

        // Initial coloring: round-robin by color
        int cur = 1;
        for (int i = 0; i < K; ++i) {
            for (int j = 0; j < K; ++j) {
                grid[i][j] = cur;
                cntColor[cur]++;
                cur++;
                if (cur > N) cur = 1;
            }
        }

        int missingColors = 0;
        for (int c = 1; c <= N; ++c) if (cntColor[c] == 0) missingColors++;

        // Build adjacency counts
        auto addAdj = [&](int c1, int c2) {
            if (c1 == c2) return;
            int x = min(c1, c2), y = max(c1, c2);
            adjCount[x][y]++;
        };

        for (int i = 0; i < K; ++i) {
            for (int j = 0; j < K; ++j) {
                int c = grid[i][j];
                if (i + 1 < K) addAdj(c, grid[i + 1][j]);
                if (j + 1 < K) addAdj(c, grid[i][j + 1]);
            }
        }

        long long badNonEdges = 0;
        int missingEdges = 0;
        for (int x = 1; x <= N; ++x) {
            for (int y = x + 1; y <= N; ++y) {
                if (isEdge[x][y]) {
                    if (adjCount[x][y] == 0) missingEdges++;
                } else {
                    badNonEdges += adjCount[x][y];
                }
            }
        }

        long long curCost = S_BAD * badNonEdges + S_MISS * missingEdges + S_COLOR * missingColors;

        if (curCost == 0) {
            solved = true;
            bestGrid = grid;
            break;
        }

        double T = 1.0;
        const double COOL = 0.9995;

        int MAX_ITERS = BASE_ITERS;

        for (int iter = 0; iter < MAX_ITERS; ++iter) {
            T *= COOL;

            int i = (int)(rng() % K);
            int j = (int)(rng() % K);
            int oldC = grid[i][j];
            int newC = (int)(rng() % N) + 1;
            if (newC == oldC) continue;

            int deltaMissingColors = 0;
            if (cntColor[oldC] == 1) deltaMissingColors += 1;
            if (cntColor[newC] == 0) deltaMissingColors -= 1;

            struct Mod { int x, y, delta; };
            Mod mods[8];
            int modSz = 0;

            auto addMod = [&](int c1, int c2, int d) {
                if (c1 == c2) return;
                int x = min(c1, c2), y = max(c1, c2);
                for (int k = 0; k < modSz; ++k) {
                    if (mods[k].x == x && mods[k].y == y) {
                        mods[k].delta += d;
                        return;
                    }
                }
                mods[modSz++] = {x, y, d};
            };

            // gather neighbor-induced changes
            if (i > 0) {
                int s = grid[i - 1][j];
                if (s != oldC) addMod(oldC, s, -1);
                if (s != newC) addMod(newC, s, +1);
            }
            if (i + 1 < K) {
                int s = grid[i + 1][j];
                if (s != oldC) addMod(oldC, s, -1);
                if (s != newC) addMod(newC, s, +1);
            }
            if (j > 0) {
                int s = grid[i][j - 1];
                if (s != oldC) addMod(oldC, s, -1);
                if (s != newC) addMod(newC, s, +1);
            }
            if (j + 1 < K) {
                int s = grid[i][j + 1];
                if (s != oldC) addMod(oldC, s, -1);
                if (s != newC) addMod(newC, s, +1);
            }

            int deltaMissingEdges = 0;
            long long deltaBadNonEdges = 0;

            for (int idx = 0; idx < modSz; ++idx) {
                int x = mods[idx].x, y = mods[idx].y, d = mods[idx].delta;
                int before = adjCount[x][y];
                int after = before + d;
                if (after < 0) { after = 0; } // safety, should not happen
                if (isEdge[x][y]) {
                    int missB = (before == 0);
                    int missA = (after == 0);
                    deltaMissingEdges += (missA - missB);
                } else {
                    deltaBadNonEdges += (after - before);
                }
            }

            long long deltaCost =
                (long long)S_COLOR * deltaMissingColors +
                (long long)S_MISS * deltaMissingEdges +
                (long long)S_BAD * deltaBadNonEdges;

            if (deltaCost <= 0 || (double)rng() / (double)rng.max() < exp(-(double)deltaCost / T)) {
                // accept move
                grid[i][j] = newC;
                if (--cntColor[oldC] == 0) missingColors++;
                if (++cntColor[newC] == 1) missingColors--;

                for (int idx = 0; idx < modSz; ++idx) {
                    int x = mods[idx].x, y = mods[idx].y, d = mods[idx].delta;
                    int before = adjCount[x][y];
                    int after = before + d;
                    if (after < 0) after = 0;
                    adjCount[x][y] = after;
                    if (isEdge[x][y]) {
                        int missB = (before == 0);
                        int missA = (after == 0);
                        if (missB && !missA) missingEdges--;
                        else if (!missB && missA) missingEdges++;
                    } else {
                        badNonEdges += (after - before);
                    }
                }

                curCost += deltaCost;

                if (curCost == 0) {
                    solved = true;
                    bestGrid = grid;
                    break;
                }
            }
        }
    }

    if (!solved) {
        // fallback: return some map (may be invalid, but try)
        vector<vector<int>> C(K, vector<int>(K, 1));
        return C;
    }

    return bestGrid;
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
        for (int i = 0; i < M; ++i) {
            cin >> A[i] >> B[i];
        }
        vector<vector<int>> C = create_map(N, M, A, B);
        int P = (int)C.size();
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << (int)C[i].size();
            if (i + 1 < P) cout << " ";
        }
        cout << "\n\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                if (j) cout << " ";
                cout << C[i][j];
            }
            cout << "\n";
        }
    }
    return 0;
}