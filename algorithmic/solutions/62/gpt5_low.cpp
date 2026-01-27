#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int totalPillars = n + 1;
    vector<vector<int>> st(totalPillars + 1); // 1..n+1
    for (int i = 1; i <= n; ++i) {
        st[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int x; cin >> x;
            st[i].push_back(x); // bottom to top; back is top
        }
    }
    int E = n + 1; // empty pillar
    // Ensure E is empty
    st[E].clear();
    
    vector<pair<int,int>> moves;
    moves.reserve((size_t)n * m * 4); // heuristic reserve
    
    auto moveBall = [&](int x, int y) {
        // assume valid
        int v = st[x].back();
        st[x].pop_back();
        st[y].push_back(v);
        moves.emplace_back(x, y);
    };
    
    // For each color d = 1..n, gather all balls of color d onto pillar d
    for (int d = 1; d <= n; ++d) {
        for (int s = 1; s <= n + 1; ++s) {
            if (s == d || s == E) continue;
            if (st[s].empty()) continue;
            // count how many balls of color d in stack s
            int cntd = 0;
            for (int v : st[s]) if (v == d) ++cntd;
            if (cntd == 0) continue;
            // Extract all d from s to d, using E as buffer for non-d, then restore E->s
            while (cntd > 0) {
                while (!st[s].empty() && st[s].back() != d) {
                    moveBall(s, E);
                }
                // now top is d
                moveBall(s, d);
                --cntd;
            }
            // restore non-d from E back to s
            while (!st[E].empty()) {
                moveBall(E, s);
            }
        }
        // Also need to process the empty pillar E itself if it contains color d (shouldn't, as we always restore)
        // But for safety, handle E as source too (it should be empty here).
        int s = E;
        if (s != d && !st[s].empty()) {
            int cntd = 0;
            for (int v : st[s]) if (v == d) ++cntd;
            while (cntd > 0) {
                while (!st[s].empty() && st[s].back() != d) {
                    // We need a temporary place, but s==E already; choose any stack != d with space.
                    // However by construction E should be empty here, so this block should not trigger.
                    // To maintain safety, find a stack with space (there must be at least one).
                    int t = -1;
                    for (int k = 1; k <= n; ++k) {
                        if (k == d) continue;
                        if ((int)st[k].size() < m) { t = k; break; }
                    }
                    if (t == -1) { // fallback shouldn't happen; break to avoid infinite loop
                        break;
                    }
                    moveBall(s, t);
                }
                moveBall(s, d);
                --cntd;
            }
            // No restoration here in safety path.
        }
    }
    
    // Output
    cout << moves.size() << "\n";
    for (auto &p : moves) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}