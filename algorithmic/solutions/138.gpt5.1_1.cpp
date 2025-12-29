#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    
    vector<string> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    for (int i = 0; i < n; ++i) cin >> target[i];
    
    // Read and ignore presets
    for (int p = 0; p < k; ++p) {
        int np, mp;
        cin >> np >> mp;
        string s;
        for (int i = 0; i < np; ++i) cin >> s;
    }
    
    const int ALPHA = 62;
    auto idx = [&](char c)->int{
        if ('a' <= c && c <= 'z') return c - 'a';
        if ('A' <= c && c <= 'Z') return 26 + (c - 'A');
        return 52 + (c - '0');
    };
    
    vector<int> cntInit(ALPHA,0), cntTarget(ALPHA,0);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j) {
            cntInit[idx(init[i][j])]++;
            cntTarget[idx(target[i][j])]++;
        }
    if (cntInit != cntTarget) {
        cout << -1 << '\n';
        return 0;
    }
    
    int N = n * m;
    vector<pair<int,int>> path(N);
    int t = 0;
    for (int i = 0; i < n; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < m; ++j)
                path[t++] = {i, j};
        } else {
            for (int j = m - 1; j >= 0; --j)
                path[t++] = {i, j};
        }
    }
    
    vector<char> arr(N), tar(N);
    for (int i = 0; i < N; ++i) {
        auto [r, c] = path[i];
        arr[i] = init[r][c];
        tar[i] = target[r][c];
    }
    
    struct Op { int op, x, y; };
    vector<Op> ops;
    ops.reserve(200000);
    
    for (int i = 0; i < N; ++i) {
        if (arr[i] == tar[i]) continue;
        int pos = -1;
        for (int j = i + 1; j < N; ++j) {
            if (arr[j] == tar[i]) { pos = j; break; }
        }
        if (pos == -1) {
            // Should not happen since counts match
            cout << -1 << '\n';
            return 0;
        }
        for (int j = pos - 1; j >= i; --j) {
            auto [r1, c1] = path[j];
            auto [r2, c2] = path[j+1];
            int opCode = 0;
            int x = 0, y = 0;
            if (r1 == r2) {
                if (c1 + 1 == c2) {
                    // (r1,c1) left of (r2,c2)
                    opCode = -1;
                    x = r1 + 1;
                    y = c1 + 1;
                } else if (c1 == c2 + 1) {
                    // (r1,c1) right of (r2,c2)
                    opCode = -2;
                    x = r1 + 1;
                    y = c1 + 1;
                }
            } else if (c1 == c2) {
                if (r1 + 1 == r2) {
                    // (r1,c1) above (r2,c2)
                    opCode = -4;
                    x = r1 + 1;
                    y = c1 + 1;
                } else if (r1 == r2 + 1) {
                    // (r1,c1) below (r2,c2)
                    opCode = -3;
                    x = r1 + 1;
                    y = c1 + 1;
                }
            }
            ops.push_back({opCode, x, y});
            swap(arr[j], arr[j+1]);
        }
    }
    
    cout << ops.size() << '\n';
    for (auto &o : ops)
        cout << o.op << ' ' << o.x << ' ' << o.y << '\n';
    
    return 0;
}