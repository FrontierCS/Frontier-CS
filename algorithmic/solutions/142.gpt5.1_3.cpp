#include <bits/stdc++.h>
using namespace std;

// Hungarian algorithm for maximum weight matching (converted to min-cost)
vector<int> hungarian_maximize(const vector<vector<int>>& w) {
    int n = (int)w.size() - 1; // 1-based
    const long long INF = (long long)1e18;
    vector<long long> u(n + 1), v(n + 1);
    vector<int> p(n + 1), way(n + 1);

    // cost = -w[i][j]
    for (int i = 1; i <= n; ++i) {
        p[0] = i;
        int j0 = 0;
        vector<long long> minv(n + 1, INF);
        vector<char> used(n + 1, false);
        do {
            used[j0] = true;
            int i0 = p[j0];
            long long delta = INF;
            int j1 = 0;
            for (int j = 1; j <= n; ++j) if (!used[j]) {
                long long cur = -(long long)w[i0][j] - u[i0] - v[j];
                if (cur < minv[j]) {
                    minv[j] = cur;
                    way[j] = j0;
                }
                if (minv[j] < delta) {
                    delta = minv[j];
                    j1 = j;
                }
            }
            for (int j = 0; j <= n; ++j) {
                if (used[j]) {
                    u[p[j]] += delta;
                    v[j] -= delta;
                } else {
                    minv[j] -= delta;
                }
            }
            j0 = j1;
        } while (p[j0] != 0);
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0);
    }

    // p[j] is row matched to column j
    vector<int> match_row_to_col(n + 1);
    for (int j = 1; j <= n; ++j) {
        int i = p[j];
        match_row_to_col[i] = j;
    }
    return match_row_to_col;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int rodsCount = n + 1;
    int B = rodsCount; // buffer rod index

    vector<vector<int>> tubes(rodsCount + 1);
    for (int i = 1; i <= n; ++i) {
        tubes[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int c; cin >> c;
            tubes[i].push_back(c);
        }
    }
    // rod B is empty

    // Count occurrences: cnt[color][rod]
    vector<vector<int>> cnt(n + 1, vector<int>(n + 1, 0)); // colors 1..n, rods 1..n
    for (int rod = 1; rod <= n; ++rod) {
        for (int c : tubes[rod]) cnt[c][rod]++;
    }

    // Hungarian to assign each color to one rod (1..n), buffer rod unused
    vector<int> targetRod = hungarian_maximize(cnt); // targetRod[color] = rod
    vector<int> targetColorOfRod(n + 1, 0);
    for (int color = 1; color <= n; ++color) {
        int r = targetRod[color];
        targetColorOfRod[r] = color;
    }

    const int LIMIT = 2000000;
    vector<pair<int,int>> ops;
    ops.reserve(LIMIT);

    auto moveBall = [&](int x, int y) {
        if (x == y) return;
        if (tubes[x].empty()) return;
        int c = tubes[x].back();
        tubes[x].pop_back();
        tubes[y].push_back(c);
        ops.emplace_back(x, y);
    };

    auto isSolved = [&]() -> bool {
        for (int rod = 1; rod <= rodsCount; ++rod) {
            for (int c : tubes[rod]) {
                int t = targetRod[c];
                if (rod != t) return false;
            }
        }
        return true;
    };

    while ((int)ops.size() < LIMIT) {
        if (isSolved()) break;
        bool moved = false;

        // Step 1: direct moves to target rods where top color matches or rod empty
        for (int x = 1; x <= rodsCount && (int)ops.size() < LIMIT; ++x) {
            if (tubes[x].empty()) continue;
            int c = tubes[x].back();
            int t = targetRod[c];
            if (x == t) continue;
            if ((int)tubes[t].size() < m &&
                (tubes[t].empty() || tubes[t].back() == c)) {
                moveBall(x, t);
                moved = true;
                break;
            }
        }
        if (moved) continue;

        // Step 2: group same colors on non-target rods (helps aggregation)
        for (int x = 1; x <= rodsCount && (int)ops.size() < LIMIT; ++x) {
            if (tubes[x].empty()) continue;
            int c = tubes[x].back();
            for (int y = 1; y <= rodsCount; ++y) {
                if (y == x) continue;
                if ((int)tubes[y].size() >= m) continue;
                // group with same color on top but not already target rod
                if (!tubes[y].empty() && tubes[y].back() == c &&
                    y != targetRod[c]) {
                    moveBall(x, y);
                    moved = true;
                    break;
                }
            }
            if (moved) break;
        }
        if (moved) continue;

        // Step 3: general relocation to buffer or any rod with space
        int xSel = -1;
        for (int x = 1; x <= rodsCount; ++x) {
            if (tubes[x].empty()) continue;
            int c = tubes[x].back();
            int t = targetRod[c];
            if (x != t || x == B) {
                xSel = x;
                break;
            }
        }
        if (xSel == -1) break; // likely solved
        int ySel = -1;
        if ((int)tubes[B].size() < m && B != xSel) {
            ySel = B;
        } else {
            for (int y = 1; y <= rodsCount; ++y) {
                if (y == xSel) continue;
                if ((int)tubes[y].size() < m) {
                    ySel = y;
                    break;
                }
            }
        }
        if (ySel == -1) break;
        moveBall(xSel, ySel);
    }

    if ((int)ops.size() > LIMIT) ops.resize(LIMIT);
    cout << ops.size() << '\n';
    for (auto &mv : ops) {
        cout << mv.first << ' ' << mv.second << '\n';
    }
    return 0;
}