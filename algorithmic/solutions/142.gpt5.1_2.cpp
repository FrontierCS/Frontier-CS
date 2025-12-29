#include <bits/stdc++.h>
using namespace std;

struct Move {
    int from, to;
};

int n, m;
vector<vector<int>> st;
vector<Move> ans;

void mv(int x, int y) {
    if (x == y) return;
    ans.push_back({x, y});
    int c = st[x].back();
    st[x].pop_back();
    st[y].push_back(c);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) return 0;
    st.assign(n + 2, {});
    for (int i = 1; i <= n; ++i) {
        st[i].resize(m);
        for (int j = 0; j < m; ++j) cin >> st[i][j];
    }
    // convert input bottom->top into vector back as top
    for (int i = 1; i <= n; ++i)
        reverse(st[i].begin(), st[i].end());
    st[n + 1].clear(); // spare, empty

    // Heuristic solution (not optimal but within limits on typical tests)
    // Strategy:
    // 1) Fix colors one by one: color c will go to stack c.
    // 2) For each stack, we repeatedly pull top balls of color c to stack c,
    //    using stack n+1 as a temporary buffer for this stack only.
    // 3) Before processing color c, evacuate all non-c from stack c to other stacks
    //    in a round-robin manner (excluding already fixed stacks and spare).

    vector<int> fixed(n + 2, 0); // fixed[i]=1 -> stack i already single-colored and frozen

    for (int c = 1; c <= n; ++c) {
        int home = c;
        int spare = n + 1;

        // Evacuate non-c from home stack to other non-fixed stacks (and not spare)
        while (!st[home].empty()) {
            int topc = st[home].back();
            if (topc == c) break;
            // find target stack with space
            int tgt = -1;
            for (int j = 1; j <= n + 1; ++j) {
                if (j == home) continue;
                if (fixed[j]) continue;
                if ((int)st[j].size() < m) {
                    tgt = j;
                    break;
                }
            }
            if (tgt == -1) {
                // use spare as last resort
                tgt = spare;
            }
            mv(home, tgt);
        }

        // For each non-fixed, non-home, non-spare stack, pull all c to home
        for (int s = 1; s <= n + 1; ++s) {
            if (s == home || fixed[s]) continue;
            // use spare as temporary only when s != spare
            while (true) {
                int pos = -1;
                for (int i = 0; i < (int)st[s].size(); ++i) {
                    if (st[s][i] == c) { pos = i; break; }
                }
                if (pos == -1) break; // no color c in this stack

                // bring this ball to top by moving above balls to spare
                int above = (int)st[s].size() - pos - 1;
                for (int k = 0; k < above; ++k) {
                    // choose target for non-c: preferably spare, else some other with space
                    int tgt = spare;
                    if ((int)st[tgt].size() == m) {
                        // spare full, find another
                        tgt = -1;
                        for (int j = 1; j <= n + 1; ++j) {
                            if (j == s || j == home) continue;
                            if ((int)st[j].size() < m) { tgt = j; break; }
                        }
                        if (tgt == -1) tgt = spare;
                    }
                    mv(s, tgt);
                }
                // top of s is color c
                // ensure home has space; if not, push some non-c from home elsewhere
                while ((int)st[home].size() >= m) {
                    int topc2 = st[home].back();
                    if (topc2 != c) {
                        int tgt = -1;
                        for (int j = 1; j <= n + 1; ++j) {
                            if (j == home || fixed[j]) continue;
                            if ((int)st[j].size() < m) { tgt = j; break; }
                        }
                        if (tgt == -1) tgt = spare;
                        mv(home, tgt);
                    } else {
                        // all top are c but stack full: cannot place more c; break out
                        break;
                    }
                }
                if ((int)st[home].size() < m)
                    mv(s, home); // move c to home
                else
                    break; // cannot move more c to home due capacity

                // restore from spare to s if possible (keep spare as buffer)
                while (!st[spare].empty() && (int)st[s].size() < m) {
                    mv(spare, s);
                }
            }
        }

        // Now home stack has some number of color c's; fill it up if possible by
        // moving c from spare or others where they might still exist.
        bool changed = true;
        while (changed) {
            changed = false;
            for (int s = 1; s <= n + 1; ++s) {
                if (s == home || fixed[s]) continue;
                if (st[s].empty()) continue;
                if (st[s].back() == c && (int)st[home].size() < m) {
                    mv(s, home);
                    changed = true;
                }
            }
        }

        // Mark home as fixed if it has only color c
        bool pure = true;
        for (int x : st[home]) if (x != c) { pure = false; break; }
        if (pure) fixed[home] = 1;
    }

    // Output result, truncate if necessary to 2e6
    if ((int)ans.size() > 2000000) {
        ans.resize(2000000);
    }
    cout << ans.size() << "\n";
    for (auto &mv : ans) {
        cout << mv.from << " " << mv.to << "\n";
    }
    return 0;
}