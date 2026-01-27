#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int Sidx; // spare pillar index
    Sidx = n + 1;
    vector<vector<int>> st(n + 2); // 1..n+1, bottom->top
    vector<vector<int>> cnt(n + 2, vector<int>(n + 1, 0)); // cnt[pillar][color]
    vector<int> sz(n + 2, 0);
    
    for (int i = 1; i <= n; ++i) {
        st[i].resize(m);
        for (int j = 0; j < m; ++j) {
            int c; cin >> c;
            st[i][j] = c;
            cnt[i][c]++;
        }
        sz[i] = m;
    }
    st[Sidx] = {};
    sz[Sidx] = 0;
    
    vector<pair<int,int>> ops;
    ops.reserve(1000000); // reserve some, will grow if needed

    auto apply_move = [&](int from, int to) {
        // assume valid
        int ball = st[from].back();
        st[from].pop_back();
        st[to].push_back(ball);
        sz[from]--; sz[to]++;
        // update counts
        cnt[from][ball]--;
        cnt[to][ball]++;
        ops.emplace_back(from, to);
    };

    auto move_color_from_to = [&](int color, int X, int Y) {
        // Move one ball of 'color' from pillar X to pillar Y using only spare S
        // Precondition: cnt[X][color] > 0 and X != Y
        bool y_was_full = (sz[Y] == m);
        if (y_was_full) {
            // push top of Y to spare
            apply_move(Y, Sidx);
        }
        // find topmost index of 'color' in X
        int idx = -1;
        for (int i = sz[X] - 1; i >= 0; --i) {
            if (st[X][i] == color) { idx = i; break; }
        }
        int J = (idx == -1 ? 0 : (sz[X] - 1 - idx));
        // move J obstacles from X to S
        for (int t = 0; t < J; ++t) apply_move(X, Sidx);
        // move the color ball from X to Y
        apply_move(X, Y);
        // move back obstacles from S to X
        for (int t = 0; t < J; ++t) apply_move(Sidx, X);
        // if Y was full, move the stored ball from S to X
        if (y_was_full) {
            apply_move(Sidx, X);
        }
    };

    // For each color c, gather all its balls to pillar c
    for (int c = 1; c <= n; ++c) {
        while (cnt[c][c] < m) {
            int X = -1;
            for (int p = 1; p <= n; ++p) {
                if (p == c) continue;
                if (cnt[p][c] > 0) { X = p; break; }
            }
            if (X == -1) break; // nothing to move
            move_color_from_to(c, X, c);
        }
    }

    cout << ops.size() << "\n";
    for (auto &mv : ops) {
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}