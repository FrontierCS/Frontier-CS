#include <bits/stdc++.h>
using namespace std;

int charToIndex(char c) {
    if ('a' <= c && c <= 'z') return c - 'a';
    if ('A' <= c && c <= 'Z') return 26 + (c - 'A');
    if ('0' <= c && c <= '9') return 52 + (c - '0');
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> A(n), B(n);
    for (int i = 0; i < n; ++i) cin >> A[i];
    for (int i = 0; i < n; ++i) cin >> B[i];
    // Read presets (but we won't use them)
    for (int p = 0; p < k; ++p) {
        int np, mp;
        cin >> np >> mp;
        string tmp;
        for (int i = 0; i < np; ++i) cin >> tmp;
    }
    
    int N = n * m;
    vector<pair<int,int>> pos(N);
    vector<vector<int>> id(n, vector<int>(m, -1));
    int idx = 0;
    for (int r = 0; r < n; ++r) {
        if (r % 2 == 0) {
            for (int c = 0; c < m; ++c) {
                pos[idx] = {r, c};
                id[r][c] = idx++;
            }
        } else {
            for (int c = m - 1; c >= 0; --c) {
                pos[idx] = {r, c};
                id[r][c] = idx++;
            }
        }
    }
    
    vector<char> s(N), t(N);
    for (int i = 0; i < N; ++i) {
        auto [r, c] = pos[i];
        s[i] = A[r][c];
        t[i] = B[r][c];
    }
    
    // Check counts
    vector<long long> cntS(62, 0), cntT(62, 0);
    for (int i = 0; i < N; ++i) {
        int si = charToIndex(s[i]);
        int ti = charToIndex(t[i]);
        if (si < 0 || ti < 0) { cout << -1 << "\n"; return 0; }
        cntS[si]++; cntT[ti]++;
    }
    if (cntS != cntT) {
        cout << -1 << "\n";
        return 0;
    }
    
    vector<tuple<int,int,int>> ops;
    auto applySwap = [&](int id1, int id2) {
        // id1 and id2 are neighbors in the grid
        auto [r1, c1] = pos[id1];
        auto [r2, c2] = pos[id2];
        if (r1 == r2) {
            if (c1 + 1 == c2) {
                // swap (r1,c1) with (r1,c2) where c2 = c1+1
                ops.emplace_back(-1, r1 + 1, c1 + 1);
            } else if (c2 + 1 == c1) {
                // swap (r1,c1) with (r1,c2) where c1 = c2+1
                ops.emplace_back(-2, r1 + 1, c1 + 1);
            } else {
                // not neighbors
            }
        } else if (c1 == c2) {
            if (r1 + 1 == r2) {
                // swap (r1,c1) with (r2,c1) where r2 = r1+1
                ops.emplace_back(-4, r1 + 1, c1 + 1);
            } else if (r2 + 1 == r1) {
                // swap (r1,c1) with (r2,c1) where r1 = r2+1
                ops.emplace_back(-3, r1 + 1, c1 + 1);
            } else {
                // not neighbors
            }
        } else {
            // not neighbors
        }
        swap(s[id1], s[id2]);
    };
    
    for (int i = 0; i < N; ++i) {
        if (s[i] == t[i]) continue;
        int j = i + 1;
        while (j < N && s[j] != t[i]) ++j;
        if (j == N) {
            // should not happen because counts are equal
            cout << -1 << "\n";
            return 0;
        }
        for (int kpos = j; kpos > i; --kpos) {
            applySwap(kpos, kpos - 1);
        }
    }
    
    if ((int)ops.size() > 400000) {
        // Should not happen with n,m <= 20
        cout << -1 << "\n";
        return 0;
    }
    
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        int code, x, y;
        tie(code, x, y) = op;
        cout << code << " " << x << " " << y << "\n";
    }
    return 0;
}