#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;

    vector<string> A(n), B(n);
    for (int i = 0; i < n; ++i) cin >> A[i];
    for (int i = 0; i < n; ++i) cin >> B[i];

    struct Preset {
        int r, c;
        vector<string> mat;
    };
    vector<Preset> presets(k);
    for (int i = 0; i < k; ++i) {
        int r, c;
        cin >> r >> c;
        presets[i].r = r;
        presets[i].c = c;
        presets[i].mat.resize(r);
        for (int x = 0; x < r; ++x) cin >> presets[i].mat[x];
    }

    auto idx = [](char ch)->int{
        if ('a' <= ch && ch <= 'z') return ch - 'a';
        if ('A' <= ch && ch <= 'Z') return 26 + (ch - 'A');
        return 52 + (ch - '0'); // '0'..'9'
    };

    vector<int> cntA(62, 0), cntB(62, 0);
    for (int i = 0; i < n; ++i) for (int j = 0; j < m; ++j) cntA[idx(A[i][j])]++, cntB[idx(B[i][j])]++;

    // map 1x1 presets
    vector<int> one1_id(62, -1);
    for (int i = 0; i < k; ++i) {
        if (presets[i].r == 1 && presets[i].c == 1) {
            one1_id[idx(presets[i].mat[0][0])] = i + 1; // op index is 1-based
        }
    }

    vector<tuple<int,int,int>> ops;

    auto apply_preset_cell = [&](int op, int x, int y, char ch) {
        // op is 1..k, preset of size 1x1
        ops.emplace_back(op, x, y);
        A[x-1][y-1] = ch;
    };

    bool counts_equal = true;
    for (int t = 0; t < 62; ++t) if (cntA[t] != cntB[t]) { counts_equal = false; break; }

    if (!counts_equal) {
        bool can_all = true;
        for (int i = 0; i < n && can_all; ++i) {
            for (int j = 0; j < m && can_all; ++j) {
                int t = idx(B[i][j]);
                if (one1_id[t] == -1) can_all = false;
            }
        }
        if (!can_all) {
            cout << -1 << "\n";
            return 0;
        }
        // set each cell directly to target using 1x1 presets
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < m; ++j) {
                if (A[i][j] != B[i][j]) {
                    int op = one1_id[idx(B[i][j])];
                    apply_preset_cell(op, i+1, j+1, B[i][j]);
                }
            }
        }
        // Output
        if ((int)ops.size() > 400000) {
            cout << -1 << "\n";
            return 0;
        }
        cout << ops.size() << "\n";
        for (auto &t : ops) {
            int a,b,c; tie(a,b,c)=t;
            cout << a << " " << b << " " << c << "\n";
        }
        return 0;
    }

    // counts equal: use only swaps to rearrange
    auto swap_left = [&](int x, int y){ // swap (x,y) with (x,y-1)
        swap(A[x-1][y-1], A[x-1][y-2]);
        ops.emplace_back(-2, x, y);
    };
    auto swap_right = [&](int x, int y){ // swap (x,y) with (x,y+1)
        swap(A[x-1][y-1], A[x-1][y]);
        ops.emplace_back(-1, x, y);
    };
    auto swap_up = [&](int x, int y){ // swap (x,y) with (x-1,y)
        swap(A[x-1][y-1], A[x-2][y-1]);
        ops.emplace_back(-3, x, y);
    };

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= m; ++j) {
            if (i == n && j == m) continue;
            char need = B[i-1][j-1];
            if (A[i-1][j-1] == need) continue;

            bool found = false;
            int xi = -1, yi = -1;
            // search in same row i, columns j+1..m
            for (int y = j+1; y <= m; ++y) {
                if (A[i-1][y-1] == need) { xi = i; yi = y; found = true; break; }
            }
            // search rows below
            if (!found) {
                for (int x = i+1; x <= n; ++x) {
                    for (int y = 1; y <= m; ++y) {
                        if (A[x-1][y-1] == need) { xi = x; yi = y; found = true; break; }
                    }
                    if (found) break;
                }
            }
            if (!found) {
                // Should not happen since counts equal and we maintain suffix invariant
                cout << -1 << "\n";
                return 0;
            }
            // Move horizontally to column j
            while (yi > j) {
                swap_left(xi, yi);
                yi--;
                if ((int)ops.size() > 400000) { cout << -1 << "\n"; return 0; }
            }
            while (yi < j) {
                swap_right(xi, yi);
                yi++;
                if ((int)ops.size() > 400000) { cout << -1 << "\n"; return 0; }
            }
            // Move vertically up to row i
            while (xi > i) {
                swap_up(xi, yi);
                xi--;
                if ((int)ops.size() > 400000) { cout << -1 << "\n"; return 0; }
            }
        }
    }

    if ((int)ops.size() > 400000) {
        cout << -1 << "\n";
        return 0;
    }
    // Optional final check A==B
    // for (int i = 0; i < n; ++i) if (A[i] != B[i]) { cout << -1 << "\n"; return 0; }

    cout << ops.size() << "\n";
    for (auto &t : ops) {
        int a,b,c; tie(a,b,c)=t;
        cout << a << " " << b << " " << c << "\n";
    }
    return 0;
}