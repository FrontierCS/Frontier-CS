#include <bits/stdc++.h>
using namespace std;

struct Cand {
    char dir;
    int idx;
    int k;   // number of shifts (cost = 2*k)
    int r;   // number of oni removed
};

static inline char opp(char d) {
    if (d == 'L') return 'R';
    if (d == 'R') return 'L';
    if (d == 'U') return 'D';
    return 'U'; // 'D'
}

static inline bool better(const Cand& a, const Cand& b) {
    if (a.r <= 0) return false;
    if (b.r <= 0) return true;
    // maximize a.r / a.k
    long long lhs = 1LL * a.r * b.k;
    long long rhs = 1LL * b.r * a.k;
    if (lhs != rhs) return lhs > rhs;
    if (a.k != b.k) return a.k < b.k;
    return a.r > b.r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<string> g(N);
    for (int i = 0; i < N; i++) cin >> g[i];

    int oni = 0;
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) if (g[i][j] == 'x') oni++;

    vector<pair<char,int>> ops;
    ops.reserve(4 * N * N);

    while (oni > 0) {
        Cand best{'?', -1, 1, 0};

        // Rows: left-prefix
        for (int i = 0; i < N; i++) {
            bool noO = true;
            int r = 0;
            for (int j = 0; j < N; j++) {
                if (g[i][j] == 'o') noO = false;
                if (g[i][j] == 'x') r++;
                if (noO && r > 0) {
                    Cand c{'L', i, j + 1, r};
                    if (better(c, best)) best = c;
                }
                if (!noO) break;
            }
        }
        // Rows: right-suffix
        for (int i = 0; i < N; i++) {
            bool noO = true;
            int r = 0;
            for (int j = N - 1; j >= 0; j--) {
                if (g[i][j] == 'o') noO = false;
                if (g[i][j] == 'x') r++;
                if (noO && r > 0) {
                    Cand c{'R', i, N - j, r};
                    if (better(c, best)) best = c;
                }
                if (!noO) break;
            }
        }
        // Cols: up-prefix
        for (int j = 0; j < N; j++) {
            bool noO = true;
            int r = 0;
            for (int i = 0; i < N; i++) {
                if (g[i][j] == 'o') noO = false;
                if (g[i][j] == 'x') r++;
                if (noO && r > 0) {
                    Cand c{'U', j, i + 1, r};
                    if (better(c, best)) best = c;
                }
                if (!noO) break;
            }
        }
        // Cols: down-suffix
        for (int j = 0; j < N; j++) {
            bool noO = true;
            int r = 0;
            for (int i = N - 1; i >= 0; i--) {
                if (g[i][j] == 'o') noO = false;
                if (g[i][j] == 'x') r++;
                if (noO && r > 0) {
                    Cand c{'D', j, N - i, r};
                    if (better(c, best)) best = c;
                }
                if (!noO) break;
            }
        }

        if (best.r <= 0) break; // should not happen under guarantees

        int removed = 0;
        if (best.dir == 'L') {
            int i = best.idx;
            for (int c = 0; c < best.k; c++) {
                if (g[i][c] == 'x') removed++;
                g[i][c] = '.';
            }
        } else if (best.dir == 'R') {
            int i = best.idx;
            for (int c = N - best.k; c < N; c++) {
                if (g[i][c] == 'x') removed++;
                g[i][c] = '.';
            }
        } else if (best.dir == 'U') {
            int j = best.idx;
            for (int r = 0; r < best.k; r++) {
                if (g[r][j] == 'x') removed++;
                g[r][j] = '.';
            }
        } else if (best.dir == 'D') {
            int j = best.idx;
            for (int r = N - best.k; r < N; r++) {
                if (g[r][j] == 'x') removed++;
                g[r][j] = '.';
            }
        }

        oni -= removed;

        for (int t = 0; t < best.k; t++) ops.push_back({best.dir, best.idx});
        char od = opp(best.dir);
        for (int t = 0; t < best.k; t++) ops.push_back({od, best.idx});

        if ((int)ops.size() > 4 * N * N) break; // safety
    }

    if ((int)ops.size() > 4 * N * N) ops.resize(4 * N * N);

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}