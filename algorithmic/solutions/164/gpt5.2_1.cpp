#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m, H0;
    vector<vector<int>> st;            // bottom -> top
    vector<int> locStack, locIndex;    // -1 if removed
    vector<pair<int,int>> ops;         // (v, i) ; i=0 for take out, else 1..m

    void init_locations() {
        locStack.assign(n + 1, -1);
        locIndex.assign(n + 1, -1);
        for (int s = 0; s < m; s++) {
            for (int j = 0; j < (int)st[s].size(); j++) {
                int v = st[s][j];
                locStack[v] = s;
                locIndex[v] = j;
            }
        }
    }

    int min_label_in_stack(int s) const {
        if (st[s].empty()) return 1000000000;
        int mn = 1000000000;
        for (int x : st[s]) mn = min(mn, x);
        return mn;
    }

    int choose_dest(int src) const {
        int best = -1;
        int bestMn = -1;
        int bestSz = INT_MAX;
        for (int t = 0; t < m; t++) {
            if (t == src) continue;
            int mn = min_label_in_stack(t);
            int sz = (int)st[t].size();
            if (mn > bestMn || (mn == bestMn && sz < bestSz)) {
                bestMn = mn;
                bestSz = sz;
                best = t;
            }
        }
        if (best == -1) best = (src + 1) % m;
        return best;
    }

    void do_move_suffix(int src, int startIdx, int dst) {
        // move st[src][startIdx..end) to top of dst
        auto &A = st[src];
        auto &B = st[dst];
        vector<int> moved(A.begin() + startIdx, A.end());
        A.erase(A.begin() + startIdx, A.end());
        int base = (int)B.size();
        B.insert(B.end(), moved.begin(), moved.end());

        for (int i = 0; i < (int)moved.size(); i++) {
            int v = moved[i];
            locStack[v] = dst;
            locIndex[v] = base + i;
        }
        // indices in A unchanged because erased tail
    }

    void do_pop_top(int s) {
        int v = st[s].back();
        st[s].pop_back();
        locStack[v] = -1;
        locIndex[v] = -1;
    }

    void solve() {
        for (int v = 1; v <= n; v++) {
            int s = locStack[v];
            if (s < 0) continue; // should not happen
            int idx = locIndex[v];

            // Safety: if locIndex got stale, re-find
            if (idx < 0 || idx >= (int)st[s].size() || st[s][idx] != v) {
                bool found = false;
                for (int ss = 0; ss < m && !found; ss++) {
                    for (int j = 0; j < (int)st[ss].size(); j++) {
                        if (st[ss][j] == v) {
                            s = ss;
                            idx = j;
                            locStack[v] = ss;
                            locIndex[v] = j;
                            found = true;
                            break;
                        }
                    }
                }
            }

            if (idx != (int)st[s].size() - 1) {
                int w = st[s][idx + 1]; // box just above v
                int t = choose_dest(s);
                ops.push_back({w, t + 1});
                do_move_suffix(s, idx + 1, t);
            }

            // now v should be on top of stack s
            if (!st[s].empty() && st[s].back() == v) {
                ops.push_back({v, 0});
                do_pop_top(s);
            } else {
                // Fallback (shouldn't happen): search and make it happen
                int ss = -1, j = -1;
                for (int s2 = 0; s2 < m; s2++) {
                    for (int k = 0; k < (int)st[s2].size(); k++) {
                        if (st[s2][k] == v) { ss = s2; j = k; break; }
                    }
                    if (ss != -1) break;
                }
                if (ss != -1) {
                    if (j != (int)st[ss].size() - 1) {
                        int w = st[ss][j + 1];
                        int t = choose_dest(ss);
                        ops.push_back({w, t + 1});
                        do_move_suffix(ss, j + 1, t);
                    }
                    ops.push_back({v, 0});
                    do_pop_top(ss);
                }
            }
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver solver;
    cin >> solver.n >> solver.m;
    solver.H0 = solver.n / solver.m;
    solver.st.assign(solver.m, {});
    for (int i = 0; i < solver.m; i++) {
        solver.st[i].resize(solver.H0);
        for (int j = 0; j < solver.H0; j++) cin >> solver.st[i][j];
    }
    solver.init_locations();
    solver.solve();

    // Ensure within limit
    if ((int)solver.ops.size() > 5000) solver.ops.resize(5000);

    for (auto [v, i] : solver.ops) {
        cout << v << ' ' << i << '\n';
    }
    return 0;
}