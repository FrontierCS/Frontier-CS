#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> cur(n), tgt(n);
    for (int i = 0; i < n; ++i) cin >> cur[i];
    for (int i = 0; i < n; ++i) cin >> tgt[i];

    // Read presets (ignored)
    for (int p = 0; p < k; ++p) {
        int np, mp; 
        cin >> np >> mp;
        string s;
        for (int i = 0; i < np; ++i) cin >> s;
    }

    // Check multiset equality
    array<int, 256> cnt1{}, cnt2{};
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j) {
            cnt1[(unsigned char)cur[i][j]]++;
            cnt2[(unsigned char)tgt[i][j]]++;
        }
    for (int c = 0; c < 256; ++c) {
        if (cnt1[c] != cnt2[c]) {
            cout << -1 << '\n';
            return 0;
        }
    }

    vector<array<int,3>> ops;
    auto add_op = [&](int code, int x, int y){
        ops.push_back({code, x+1, y+1});
    };
    auto check_limit = [&](){
        if ((int)ops.size() > 400000) {
            cout << -1 << '\n';
            exit(0);
        }
    };

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (cur[i][j] == tgt[i][j]) continue;
            char need = tgt[i][j];
            int sx = -1, sy = -1;
            // search in suffix region: rows i..n-1; in row i, cols j..m-1
            bool found = false;
            for (int x = i; x < n && !found; ++x) {
                int y0 = (x == i ? j : 0);
                for (int y = y0; y < m; ++y) {
                    if (cur[x][y] == need) {
                        sx = x; sy = y; found = true; break;
                    }
                }
            }
            if (!found) {
                cout << -1 << '\n';
                return 0;
            }

            int x = sx, y = sy;

            if (x == i) {
                // move left to j
                while (y > j) {
                    add_op(-2, x, y); // swap (x,y) with (x,y-1)
                    swap(cur[x][y], cur[x][y-1]);
                    y--;
                    check_limit();
                }
            } else {
                // first move horizontally to column j inside row x (> i)
                while (y < j) {
                    add_op(-1, x, y); // swap (x,y) with (x,y+1)
                    swap(cur[x][y], cur[x][y+1]);
                    y++;
                    check_limit();
                }
                while (y > j) {
                    add_op(-2, x, y); // swap (x,y) with (x,y-1)
                    swap(cur[x][y], cur[x][y-1]);
                    y--;
                    check_limit();
                }
                // move up to row i along column j
                while (x > i) {
                    add_op(-3, x, y); // swap (x,y) with (x-1,y)
                    swap(cur[x][y], cur[x-1][y]);
                    x--;
                    check_limit();
                }
            }
            // Now at (i,j), should match
            // assert(cur[i][j] == need);
        }
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << '\n';
    }
    return 0;
}