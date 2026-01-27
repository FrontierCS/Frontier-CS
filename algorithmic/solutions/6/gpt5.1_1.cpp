#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 45;

mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    if (N == 1) {
        return vector<vector<int>>(1, vector<int>(1, 1));
    }

    static bool want[MAXN][MAXN];
    static int cntAdj[MAXN][MAXN];
    static int cellCount[MAXN];

    // Build adjacency wanted matrix
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            want[i][j] = false;
            cntAdj[i][j] = 0;
        }
        want[i][i] = true; // same color always allowed
    }
    for (int k = 0; k < M; ++k) {
        int u = A[k], v = B[k];
        want[u][v] = want[v][u] = true;
    }

    auto verify_map = [&](const vector<vector<int>> &grid) -> bool {
        int K = (int)grid.size();
        // Check each country appears
        vector<int> cntC(N + 1, 0);
        for (int r = 0; r < K; ++r)
            for (int c = 0; c < K; ++c)
                cntC[grid[r][c]]++;
        for (int i = 1; i <= N; ++i)
            if (cntC[i] == 0) return false;

        // Check adjacencies
        static bool seen[MAXN][MAXN];
        for (int i = 1; i <= N; ++i)
            for (int j = 1; j <= N; ++j)
                seen[i][j] = false;

        int dr[4] = {-1, 1, 0, 0};
        int dc[4] = {0, 0, -1, 1};
        for (int r = 0; r < K; ++r) {
            for (int c = 0; c < K; ++c) {
                int x = grid[r][c];
                for (int d = 0; d < 4; ++d) {
                    int nr = r + dr[d], nc = c + dc[d];
                    if (nr < 0 || nr >= K || nc < 0 || nc >= K) continue;
                    int y = grid[nr][nc];
                    if (x == y) continue;
                    if (!want[x][y]) return false;
                    seen[x][y] = seen[y][x] = true;
                }
            }
        }
        for (int k = 0; k < M; ++k) {
            int u = A[k], v = B[k];
            if (!seen[u][v]) return false;
        }
        return true;
    };

    int K = 240;

    const long long wME = 1;    // weight for missing edges
    const long long wEE = 100;  // weight for extra (forbidden) edges
    const long long wMC = 10;   // weight for missing country

    int maxAttempts = 5;

    for (int attempt = 0; attempt < maxAttempts; ++attempt) {
        vector<vector<int>> grid(K, vector<int>(K));

        // Initial random grid, ensure first row uses all colors once.
        for (int r = 0; r < K; ++r) {
            for (int c = 0; c < K; ++c) {
                grid[r][c] = (int)(rng() % N) + 1;
            }
        }
        for (int c = 0; c < N && c < K; ++c) {
            grid[0][c] = c + 1;
        }

        // Initialize counts
        for (int i = 1; i <= N; ++i) {
            cellCount[i] = 0;
            for (int j = 1; j <= N; ++j) {
                cntAdj[i][j] = 0;
            }
        }

        for (int r = 0; r < K; ++r)
            for (int c = 0; c < K; ++c)
                cellCount[grid[r][c]]++;

        int missingCountry = 0;
        for (int i = 1; i <= N; ++i)
            if (cellCount[i] == 0) missingCountry++;

        long long missingEdges = M;
        long long extraEdges = 0;

        auto addAdj = [&](int a, int b) {
            if (a == b) return;
            if (a > b) swap(a, b);
            int old = cntAdj[a][b];
            bool edgeWanted = want[a][b];
            if (edgeWanted) {
                if (old == 0) missingEdges--;
            } else {
                if (old == 0) extraEdges++;
            }
            cntAdj[a][b] = old + 1;
        };

        auto removeAdj = [&](int a, int b) {
            if (a == b) return;
            if (a > b) swap(a, b);
            int old = cntAdj[a][b];
            bool edgeWanted = want[a][b];
            int neu = old - 1;
            if (edgeWanted) {
                if (old == 1) missingEdges++;
            } else {
                if (old == 1) extraEdges--;
            }
            cntAdj[a][b] = neu;
        };

        // Build adjacency counts from grid
        for (int r = 0; r < K; ++r) {
            for (int c = 0; c < K; ++c) {
                int x = grid[r][c];
                if (r + 1 < K) {
                    int y = grid[r + 1][c];
                    if (x != y) addAdj(x, y);
                }
                if (c + 1 < K) {
                    int y = grid[r][c + 1];
                    if (x != y) addAdj(x, y);
                }
            }
        }

        long long cost = missingEdges * wME + extraEdges * wEE + missingCountry * wMC;

        long long steps = 2LL * K * K;
        double T0 = 200.0, T1 = 1.0;

        int dr[4] = {-1, 1, 0, 0};
        int dc[4] = {0, 0, -1, 1};

        struct ModPair {
            int x, y, oldCount;
        };

        for (long long iter = 0; iter < steps && cost > 0; ++iter) {
            double tfrac = (double)iter / (double)steps;
            double T = T0 + (T1 - T0) * tfrac;
            if (T < 1e-3) T = 1e-3;

            int idx = (int)(rng() % (K * 1LL * K));
            int r = idx / K;
            int c = idx % K;
            int oldColor = grid[r][c];

            if (N <= 1) continue;

            int newColor = (int)(rng() % (N - 1)) + 1;
            if (newColor >= oldColor) newColor++;

            if (newColor == oldColor) continue;

            long long oldCost = cost;
            long long oldMissingEdges = missingEdges;
            long long oldExtraEdges = extraEdges;
            int oldMissingCountry = missingCountry;
            int oldCountOld = cellCount[oldColor];
            int oldCountNew = cellCount[newColor];

            ModPair mods[16];
            int modCnt = 0;

            auto mark_mod = [&](int a, int b) {
                if (a == b) return;
                if (a > b) swap(a, b);
                for (int i = 0; i < modCnt; ++i) {
                    if (mods[i].x == a && mods[i].y == b) return;
                }
                mods[modCnt].x = a;
                mods[modCnt].y = b;
                mods[modCnt].oldCount = cntAdj[a][b];
                modCnt++;
            };

            // Apply adjacency changes
            for (int d = 0; d < 4; ++d) {
                int nr = r + dr[d], nc = c + dc[d];
                if (nr < 0 || nr >= K || nc < 0 || nc >= K) continue;
                int nb = grid[nr][nc];
                if (nb != oldColor) {
                    mark_mod(oldColor, nb);
                    removeAdj(oldColor, nb);
                }
                if (nb != newColor) {
                    mark_mod(newColor, nb);
                    addAdj(newColor, nb);
                }
            }

            // Update country counts
            if (oldCountOld == 1) missingCountry++;
            if (oldCountNew == 0) missingCountry--;
            cellCount[oldColor]--;
            cellCount[newColor]++;

            long long newCost = missingEdges * wME + extraEdges * wEE + missingCountry * wMC;
            long long delta = newCost - oldCost;

            bool accept = false;
            if (delta <= 0) {
                accept = true;
            } else {
                double prob = exp(-double(delta) / T);
                double u = (double)(rng() & 0xFFFFFFFFULL) / 4294967296.0;
                if (u < prob) accept = true;
            }

            if (accept) {
                grid[r][c] = newColor;
                cost = newCost;
            } else {
                // revert
                for (int i = 0; i < modCnt; ++i) {
                    int x = mods[i].x;
                    int y = mods[i].y;
                    cntAdj[x][y] = mods[i].oldCount;
                }
                missingEdges = oldMissingEdges;
                extraEdges = oldExtraEdges;
                missingCountry = oldMissingCountry;
                cellCount[oldColor] = oldCountOld;
                cellCount[newColor] = oldCountNew;
                cost = oldCost;
            }
        }

        if (cost == 0 && verify_map(grid)) {
            return grid;
        }
    }

    // Fallback (should rarely be used): simple map that likely satisfies many cases
    // but not guaranteed for all pathological ones.
    // We make a simple pattern based on rows of repeated colors.
    int Kf = max(2, N);
    vector<vector<int>> grid(Kf, vector<int>(Kf, 1));
    for (int r = 0; r < Kf; ++r) {
        for (int c = 0; c < Kf; ++c) {
            grid[r][c] = (r + c) % N + 1;
        }
    }
    return grid;
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
        cout << P << '\n';
        for (int i = 0; i < P; ++i) {
            cout << (int)C[i].size();
            if (i + 1 < P) cout << ' ';
        }
        cout << "\n";
        cout << "\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                if (j) cout << ' ';
                cout << C[i][j];
            }
            cout << '\n';
        }
    }
    return 0;
}