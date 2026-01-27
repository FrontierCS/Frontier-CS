#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int total_cols = n + 1;
    vector<vector<int>> stk(total_cols + 1); // 1..n+1
    for (int i = 1; i <= n; ++i) {
        stk[i].reserve(m);
        vector<int> tmp(m);
        for (int j = 0; j < m; ++j) cin >> tmp[j];
        // input bottom->top; store as vector with back as top
        for (int j = 0; j < m; ++j) stk[i].push_back(tmp[j]);
    }
    // n+1 is empty
    stk[n+1].reserve(m);

    vector<pair<int,int>> moves;
    moves.reserve(10000000);

    auto move_ball = [&](int x, int y) {
        // assumes valid
        int v = stk[x].back();
        stk[x].pop_back();
        stk[y].push_back(v);
        moves.emplace_back(x, y);
    };

    auto has_color = [&](int col, int color) -> bool {
        for (int v : stk[col]) if (v == color) return true;
        return false;
    };

    // Empty a column s, not touching avoided columns as sources or as free.
    auto empty_column = [&](int s, const vector<char>& avoid) {
        // find initial free f != s with space and not avoided
        int f = -1;
        for (int k = 1; k <= total_cols; ++k) {
            if (k == s) continue;
            if (avoid[k]) continue;
            if ((int)stk[k].size() < m) { f = k; break; }
        }
        if (f == -1) {
            // No free other than possibly s having space; ensure s has space, otherwise impossible
            if ((int)stk[s].size() == m) {
                // create free by moving from some r -> s to make r free
                int r = -1;
                for (int k = 1; k <= total_cols; ++k) {
                    if (k == s) continue;
                    if (avoid[k]) continue;
                    if (!stk[k].empty()) { r = k; break; }
                }
                if (r == -1) return; // degenerate
                move_ball(r, s);
                f = r;
            } else {
                // s has space, still need a free distinct from s; move from some r to s to free r
                int r = -1;
                for (int k = 1; k <= total_cols; ++k) {
                    if (k == s) continue;
                    if (avoid[k]) continue;
                    if (!stk[k].empty()) { r = k; break; }
                }
                if (r == -1) return;
                move_ball(r, s);
                f = r;
            }
        }
        while (!stk[s].empty()) {
            if (f == s || (int)stk[f].size() == m) {
                // switch free by moving from some r -> s
                int r = -1;
                for (int k = 1; k <= total_cols; ++k) {
                    if (k == s) continue;
                    if (avoid[k]) continue;
                    if (!stk[k].empty()) { r = k; break; }
                }
                if (r == -1) break; // should not happen
                move_ball(r, s);
                f = r;
            }
            move_ball(s, f);
            if ((int)moves.size() > 10000000) break;
        }
    };

    // Find an auxiliary column g != p and != j, from indices >= start_i+1..n+1
    auto choose_aux = [&](int start_i, int p, int j) -> int {
        for (int k = start_i + 1; k <= total_cols; ++k) {
            if (k == p || k == j) continue;
            return k;
        }
        // fallback search entire range
        for (int k = 1; k <= total_cols; ++k) {
            if (k == p || k == j) continue;
            return k;
        }
        return -1;
    };

    // Phase 1: process colors 1..n-2
    for (int color = 1; color <= n - 2; ++color) {
        int p = color; // target pillar
        // empty p avoiding fixed [1..color-1] and avoiding p as well (though it's the target)
        vector<char> avoid(total_cols + 1, 0);
        for (int k = 1; k <= color - 1; ++k) avoid[k] = 1;
        avoid[p] = 1; // do not use p as free or source in emptying others
        // But when emptying p itself, avoid should not include p as source; create a special avoid for emptying p
        vector<char> avoid_empty_p = avoid;
        avoid_empty_p[p] = 0; // allow p as source (we are emptying it)
        empty_column(p, avoid_empty_p);

        // For each other column j, move all 'color' to p using an auxiliary g
        for (int j = color + 1; j <= n; ++j) {
            if (!has_color(j, color)) continue;
            int g = choose_aux(color, p, j);
            if (g == -1) continue;
            // ensure g is empty; avoid fixed prefix and avoid p (to keep p pure)
            vector<char> avoid_g(total_cols + 1, 0);
            for (int k = 1; k <= color - 1; ++k) avoid_g[k] = 1;
            avoid_g[p] = 1;
            // allow j as source if needed
            empty_column(g, avoid_g);

            // Move all color from j to p, pushing blockers to g (without restoring each time)
            while (has_color(j, color)) {
                while (!stk[j].empty() && stk[j].back() != color) {
                    move_ball(j, g);
                }
                if (!stk[j].empty() && stk[j].back() == color) {
                    move_ball(j, p);
                } else {
                    break;
                }
                if ((int)moves.size() > 10000000) break;
            }
            // restore g back onto j
            while (!stk[g].empty()) {
                move_ball(g, j);
                if ((int)moves.size() > 10000000) break;
            }
            if ((int)moves.size() > 10000000) break;
        }
        if ((int)moves.size() > 10000000) break;
    }

    // Phase 2: last two colors on pillars a=n-1 and b=n
    if (n >= 2) {
        int a = n - 1;
        int b = n;
        // choose auxiliary e
        int e = -1;
        for (int k = 1; k <= total_cols; ++k) {
            if (k == a || k == b) continue;
            e = k; break;
        }
        if (e == -1) e = total_cols; // should not happen
        // empty e avoiding only fixed 1..n-2 (allow a and b)
        vector<char> avoid_e(total_cols + 1, 0);
        for (int k = 1; k <= n - 2; ++k) avoid_e[k] = 1;
        empty_column(e, avoid_e);

        // Move all color a from b to a using e as temp
        while (has_color(b, a)) {
            while (!stk[b].empty() && stk[b].back() != a) {
                move_ball(b, e);
            }
            if (!stk[b].empty() && stk[b].back() == a) {
                move_ball(b, a);
            } else break;
            while (!stk[e].empty()) move_ball(e, b);
            if ((int)moves.size() > 10000000) break;
        }
        // Move all color b from a to b using e as temp
        while (has_color(a, b)) {
            while (!stk[a].empty() && stk[a].back() != b) {
                move_ball(a, e);
            }
            if (!stk[a].empty() && stk[a].back() == b) {
                move_ball(a, b);
            } else break;
            while (!stk[e].empty()) move_ball(e, a);
            if ((int)moves.size() > 10000000) break;
        }
    }

    // Output moves (truncate if exceeded, though should not)
    int k = (int)moves.size();
    if (k > 10000000) k = 10000000;
    cout << k << "\n";
    for (int i = 0; i < k; ++i) {
        cout << moves[i].first << " " << moves[i].second << "\n";
    }
    return 0;
}