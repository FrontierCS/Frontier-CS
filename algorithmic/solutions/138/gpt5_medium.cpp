#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> cur(n), target(n);
    for (int i = 0; i < n; ++i) cin >> cur[i];
    for (int i = 0; i < n; ++i) cin >> target[i];
    
    // Read and ignore presets
    vector<pair<int,int>> presz(k);
    for (int p = 0; p < k; ++p) {
        int np, mp;
        cin >> np >> mp;
        presz[p] = {np, mp};
        string tmp;
        for (int i = 0; i < np; ++i) cin >> tmp;
    }
    
    // Check multiset equality
    vector<int> cnt(128, 0);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            cnt[(unsigned char)cur[i][j]]++;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            cnt[(unsigned char)target[i][j]]--;
    for (int v : cnt) {
        if (v != 0) {
            cout << -1 << "\n";
            return 0;
        }
    }
    
    struct Op { int op, x, y; };
    vector<Op> ops;
    ops.reserve(200000);
    
    auto do_swap_up = [&](int x, int y) {
        // swap (x,y) with (x-1,y); internal 0-based; output op -3 x+1 y+1
        swap(cur[x][y], cur[x-1][y]);
        ops.push_back({-3, x+1, y+1});
    };
    auto do_swap_left = [&](int x, int y) {
        // swap (x,y) with (x,y-1); internal 0-based; output op -2 x+1 y+1
        swap(cur[x][y], cur[x][y-1]);
        ops.push_back({-2, x+1, y+1});
    };
    
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (cur[i][j] == target[i][j]) continue;
            // find target char in rectangle [i..n-1] x [j..m-1]
            char need = target[i][j];
            int sx = -1, sy = -1;
            for (int x = i; x < n && sx == -1; ++x) {
                for (int y = j; y < m; ++y) {
                    if (cur[x][y] == need) { sx = x; sy = y; break; }
                }
            }
            if (sx == -1) {
                // Should not happen due to multiset equality and invariant
                cout << -1 << "\n";
                return 0;
            }
            // move it up to row i
            while (sx > i) {
                do_swap_up(sx, sy);
                --sx;
                if ((int)ops.size() > 400000) { cout << -1 << "\n"; return 0; }
            }
            // move it left to column j
            while (sy > j) {
                do_swap_left(sx, sy);
                --sy;
                if ((int)ops.size() > 400000) { cout << -1 << "\n"; return 0; }
            }
            // now cur[i][j] == need
        }
    }
    
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.op << " " << op.x << " " << op.y << "\n";
    }
    return 0;
}