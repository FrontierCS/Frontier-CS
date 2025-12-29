#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int n = 20, m = 20;
    vector<string> g(n, string(m, '0'));

    // Build a long 1-cell-wide induced path using a 10x10 "node grid" scaled by 2.
    // Nodes at (2*r,2*c); edges open the midpoint cell.
    const int R = 10, C = 10;
    vector<pair<int,int>> nodes;
    nodes.reserve(R * C);

    for (int r = 0; r < R; r++) {
        if (r % 2 == 0) {
            for (int c = 0; c < C; c++) nodes.push_back({r, c});
        } else {
            for (int c = C - 1; c >= 0; c--) nodes.push_back({r, c});
        }
    }

    auto openCell = [&](int rr, int cc) {
        if (0 <= rr && rr < n && 0 <= cc && cc < m) g[rr][cc] = '1';
    };

    for (int i = 0; i < (int)nodes.size(); i++) {
        auto [r, c] = nodes[i];
        int gr = 2 * r, gc = 2 * c;
        openCell(gr, gc);

        if (i > 0) {
            auto [pr, pc] = nodes[i - 1];
            int pgr = 2 * pr, pgc = 2 * pc;
            int ngr = gr, ngc = gc;
            int mr = (pgr + ngr) / 2;
            int mc = (pgc + ngc) / 2;
            openCell(mr, mc);
        }
    }

    cout << n << ' ' << m << "\n";
    for (int i = 0; i < n; i++) cout << g[i] << "\n";
    return 0;
}