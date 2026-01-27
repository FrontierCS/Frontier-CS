#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int P = n + 1;
    vector<vector<int>> pile(P + 1);
    for (int i = 1; i <= n; ++i) {
        pile[i].reserve(m);
        vector<int> tmp(m);
        for (int j = 0; j < m; ++j) cin >> tmp[j];
        // input is bottom to top; we store bottom->top in vector; back is top
        for (int j = 0; j < m; ++j) pile[i].push_back(tmp[j]);
    }
    pile[P] = {}; // spare initially empty

    // Count occurrences count[color][pillar]
    vector<vector<int>> cnt(n + 2, vector<int>(P + 2, 0));
    for (int j = 1; j <= P; ++j) {
        for (int x : pile[j]) {
            if (x >= 1 && x <= n) cnt[x][j]++;
        }
    }

    // Hungarian algorithm to assign n colors to n+1 pillars leaving one spare.
    int N = P; // rows = P (n colors + 1 dummy), cols = P pillars
    vector<vector<int>> cost(N + 1, vector<int>(N + 1, 0));
    // rows 1..n represent colors, row N is dummy (all zeros)
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= P; ++j) {
            cost[i][j] = -cnt[i][j]; // minimize negative -> maximize count
        }
    }
    for (int j = 1; j <= P; ++j) cost[N][j] = 0;

    // Hungarian (minimization)
    vector<int> u(N + 1), v(N + 1), p(N + 1), way(N + 1);
    for (int i = 1; i <= N; ++i) {
        p[0] = i;
        int j0 = 0;
        vector<int> minv(N + 1, INT_MAX);
        vector<char> used(N + 1, false);
        do {
            used[j0] = true;
            int i0 = p[j0], delta = INT_MAX, j1 = 0;
            for (int j = 1; j <= N; ++j) if (!used[j]) {
                int cur = cost[i0][j] - u[i0] - v[j];
                if (cur < minv[j]) { minv[j] = cur; way[j] = j0; }
                if (minv[j] < delta) { delta = minv[j]; j1 = j; }
            }
            for (int j = 0; j <= N; ++j) {
                if (used[j]) { u[p[j]] += delta; v[j] -= delta; }
                else minv[j] -= delta;
            }
            j0 = j1;
        } while (p[j0] != 0);
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0);
    }
    // p[j] = assigned row for column j
    vector<int> dest(n + 1, -1);
    int spare = -1;
    for (int j = 1; j <= N; ++j) {
        int row = p[j];
        if (row == N) {
            spare = j;
        } else {
            dest[row] = j;
        }
    }
    if (spare == -1) {
        // Fallback: choose any pillar not used by dest
        vector<int> used(P + 1, 0);
        for (int c = 1; c <= n; ++c) if (dest[c] >= 1) used[dest[c]] = 1;
        for (int j = 1; j <= P; ++j) if (!used[j]) { spare = j; break; }
        if (spare == -1) spare = P;
    }

    // Moves list
    vector<pair<int,int>> moves;
    auto moveBall = [&](int x, int y) {
        if (x == y) return;
        if (pile[x].empty()) return;
        if ((int)pile[y].size() >= m) return;
        int c = pile[x].back();
        pile[x].pop_back();
        pile[y].push_back(c);
        moves.emplace_back(x, y);
    };

    auto canMoveToDest = [&](int x)->bool {
        if (pile[x].empty()) return false;
        int c = pile[x].back();
        if (c < 1 || c > n) return false;
        int d = dest[c];
        if (d <= 0) return false;
        if (d == x) return false;
        if ((int)pile[d].size() >= m) return false;
        return true;
    };

    auto solved = [&]()->bool {
        // spare must be empty
        if (!pile[spare].empty()) return false;
        // all other pillars must be of their assigned color and full m
        for (int pidx = 1; pidx <= P; ++pidx) if (pidx != spare) {
            if ((int)pile[pidx].size() != m) return false;
            int expectColor = -1;
            // find which color assigned to this pillar
            for (int c = 1; c <= n; ++c) if (dest[c] == pidx) { expectColor = c; break; }
            if (expectColor == -1) return false;
            for (int x : pile[pidx]) if (x != expectColor) return false;
        }
        return true;
    };

    const int MAX_MOVES = 10000000;
    // Main loop
    for (int iter = 0; iter < 50000000; ++iter) {
        if ((int)moves.size() > MAX_MOVES) break;
        if (solved()) break;

        bool progress = false;

        // Always try to move from spare to dest if possible
        while (!pile[spare].empty()) {
            int c = pile[spare].back();
            int d = (c >= 1 && c <= n) ? dest[c] : -1;
            if (d >= 1 && (int)pile[d].size() < m) {
                moveBall(spare, d);
                progress = true;
                if ((int)moves.size() > MAX_MOVES) break;
            } else break;
        }
        if ((int)moves.size() > MAX_MOVES) break;

        // Move any possible top to its destination
        bool did;
        do {
            did = false;
            for (int x = 1; x <= P; ++x) {
                while (canMoveToDest(x)) {
                    moveBall(x, dest[pile[x].back()]); // Note: after pop, back changed; handle carefully
                    // Fix: store color before popping
                    // To correct, we need to re-implement the call safely:
                    // But since we just popped and pushed, we need to ensure correct target.
                    // We'll instead implement properly:
                    // However we cannot modify lambda inside loop, so we adjust here:
                    // We'll revert: recompute as:
                    int y = 0; // dummy to avoid warnings
                    did = true;
                    progress = true;
                    if ((int)moves.size() > MAX_MOVES) break;
                }
                if ((int)moves.size() > MAX_MOVES) break;
            }
        } while (did && (int)moves.size() <= MAX_MOVES);
        if ((int)moves.size() > MAX_MOVES) break;

        // The above had a bug; fix by explicit loop:
        for (int x = 1; x <= P; ++x) {
            while (!pile[x].empty()) {
                int c = pile[x].back();
                if (c < 1 || c > n) break;
                int d = dest[c];
                if (d == x) break;
                if ((int)pile[d].size() >= m) break;
                moveBall(x, d);
                progress = true;
                if ((int)moves.size() > MAX_MOVES) break;
            }
            if ((int)moves.size() > MAX_MOVES) break;
        }
        if ((int)moves.size() > MAX_MOVES) break;

        if (progress) continue;

        // If stuck, push something to spare to unlock
        if ((int)pile[spare].size() < m) {
            int chosen = -1;
            // Prefer a ball not on its destination
            for (int x = 1; x <= P; ++x) if (x != spare && !pile[x].empty()) {
                int c = pile[x].back();
                if (c >= 1 && c <= n && dest[c] != x) { chosen = x; break; }
            }
            if (chosen == -1) {
                for (int x = 1; x <= P; ++x) if (x != spare && !pile[x].empty()) {
                    chosen = x; break;
                }
            }
            if (chosen != -1) {
                moveBall(chosen, spare);
                progress = true;
            }
        }

        if (!progress) {
            // As a last resort, try moving between non-spare pillars to match tops
            bool found = false;
            for (int x = 1; x <= P && !found; ++x) if (!pile[x].empty()) {
                int c = pile[x].back();
                if (c < 1 || c > n) continue;
                int d = dest[c];
                if (d != x && (int)pile[d].size() < m) {
                    moveBall(x, d);
                    found = true;
                    progress = true;
                    break;
                }
            }
            if (!found) {
                // Try any legal move to not-full pillar
                for (int x = 1; x <= P && !found; ++x) if (!pile[x].empty()) {
                    for (int y = 1; y <= P; ++y) if (x != y && (int)pile[y].size() < m) {
                        moveBall(x, y);
                        found = true;
                        progress = true;
                        break;
                    }
                }
            }
        }

        if (!progress) break;
    }

    // Output
    int k = (int)moves.size();
    if (k > 10000000) k = 10000000;
    cout << k << "\n";
    for (int i = 0; i < k; ++i) {
        cout << moves[i].first << " " << moves[i].second << "\n";
    }
    return 0;
}