#include <bits/stdc++.h>
using namespace std;

static const int N_FIXED = 20;

struct Solver {
    int N, M;
    vector<string> s;
    mt19937_64 rng;
    chrono::steady_clock::time_point start;
    double TIME_LIMIT;

    Solver(): N(20), M(0), TIME_LIMIT(1.95) {
        rng.seed(chrono::steady_clock::now().time_since_epoch().count());
    }

    inline int try_place(const vector<string>& grid, const string& t, int i, int j, bool horizontal) {
        int k = (int)t.size();
        int newcells = 0;
        if (horizontal) {
            int col = j;
            for (int p = 0; p < k; ++p) {
                char g = grid[i][col];
                if (g != '.' && g != t[p]) return -1;
                if (g == '.') newcells++;
                col++; if (col == N) col = 0;
            }
        } else {
            int row = i;
            for (int p = 0; p < k; ++p) {
                char g = grid[row][j];
                if (g != '.' && g != t[p]) return -1;
                if (g == '.') newcells++;
                row++; if (row == N) row = 0;
            }
        }
        return newcells;
    }

    inline void apply_place(vector<string>& grid, const string& t, int i, int j, bool horizontal) {
        int k = (int)t.size();
        if (horizontal) {
            int col = j;
            for (int p = 0; p < k; ++p) {
                if (grid[i][col] == '.') grid[i][col] = t[p];
                col++; if (col == N) col = 0;
            }
        } else {
            int row = i;
            for (int p = 0; p < k; ++p) {
                if (grid[row][j] == '.') grid[row][j] = t[p];
                row++; if (row == N) row = 0;
            }
        }
    }

    inline bool contains_string(const vector<string>& grid, const string& t) {
        int k = (int)t.size();
        // Check horizontal
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                int p = 0;
                int col = j;
                for (; p < k; ++p) {
                    char g = grid[i][col];
                    if (g != t[p]) break;
                    col++; if (col == N) col = 0;
                }
                if (p == k) return true;
            }
        }
        // Check vertical
        for (int j = 0; j < N; ++j) {
            for (int i = 0; i < N; ++i) {
                int p = 0;
                int row = i;
                for (; p < k; ++p) {
                    char g = grid[row][j];
                    if (g != t[p]) break;
                    row++; if (row == N) row = 0;
                }
                if (p == k) return true;
            }
        }
        return false;
    }

    int evaluate_c(const vector<string>& grid) {
        int cnt = 0;
        for (int idx = 0; idx < M; ++idx) {
            if (contains_string(grid, s[idx])) cnt++;
        }
        return cnt;
    }

    void solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);
        cin >> N >> M;
        s.resize(M);
        for (int i = 0; i < M; ++i) cin >> s[i];

        start = chrono::steady_clock::now();

        vector<string> bestGrid(N, string(N, '.'));
        int bestC = -1;

        vector<int> order(M);
        iota(order.begin(), order.end(), 0);

        int attempt = 0;
        while (true) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
            if (elapsed > TIME_LIMIT) break;
            attempt++;

            vector<string> grid(N, string(N, '.'));

            // Randomly decide ordering strategy
            if (attempt % 3 == 0) {
                // Sort by length descending
                stable_sort(order.begin(), order.end(), [&](int a, int b){
                    if (s[a].size() != s[b].size()) return s[a].size() > s[b].size();
                    return a < b;
                });
            } else if (attempt % 3 == 1) {
                // Shuffle
                shuffle(order.begin(), order.end(), rng);
            } else {
                // Sort by length ascending
                stable_sort(order.begin(), order.end(), [&](int a, int b){
                    if (s[a].size() != s[b].size()) return s[a].size() < s[b].size();
                    return a < b;
                });
            }

            int placed = 0;
            for (int idx : order) {
                const string& t = s[idx];
                int bestNew = INT_MAX;
                int bi = -1, bj = -1;
                bool bh = false;

                // Try to find a zero-cost placement quickly
                bool foundZero = false;

                // Try both orientations, maybe randomize starting orientation
                int oriStart = (rng() & 1);
                for (int oo = 0; oo < 2; ++oo) {
                    bool horizontal = ((oriStart + oo) & 1) == 0;
                    for (int i = 0; i < N; ++i) {
                        for (int j = 0; j < N; ++j) {
                            int nc = try_place(grid, t, i, j, horizontal);
                            if (nc >= 0) {
                                if (nc < bestNew) {
                                    bestNew = nc;
                                    bi = i; bj = j; bh = horizontal;
                                    if (bestNew == 0) { foundZero = true; break; }
                                } else if (nc == bestNew) {
                                    // random tie-break
                                    if ((rng() & 1) == 0) {
                                        bi = i; bj = j; bh = horizontal;
                                    }
                                }
                            }
                        }
                        if (foundZero) break;
                    }
                    if (foundZero) break;
                }

                if (bi != -1) {
                    apply_place(grid, t, bi, bj, bh);
                    placed++;
                }
            }

            int c = evaluate_c(grid);
            if (c > bestC) {
                bestC = c;
                bestGrid = grid;
            }
        }

        for (int i = 0; i < N; ++i) {
            cout << bestGrid[i] << "\n";
        }
    }
};

int main() {
    Solver solver;
    solver.solve();
    return 0;
}