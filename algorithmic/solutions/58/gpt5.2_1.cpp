#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long x;
    if (!(cin >> x)) return 0;

    const int B = 60;                 // Build values up to 2^60
    const int n = 3 * B + 2;          // 182 <= 300

    vector<vector<int>> a(n, vector<int>(n, 0));

    auto set1 = [&](int r, int c) {
        if (1 <= r && r <= n && 1 <= c && c <= n) a[r - 1][c - 1] = 1;
    };

    // Collector: bottom row all ones, sink at (n,n)
    for (int c = 1; c <= n; c++) set1(n, c);

    // Backbone that creates dp(V_i) = 2^i at V_i = (i+1, 3i+1)
    set1(1, 1);
    for (int i = 0; i < B; i++) {
        int r = i + 1;
        int c = 3 * i + 1;

        // V_i
        set1(r, c);

        // Unique path to split node S_i (two steps right)
        set1(r, c + 1);      // bridge
        set1(r, c + 2);      // S_i

        // Diamond to double: S_i -> V_{i+1}
        set1(r, c + 3);      // top-right
        set1(r + 1, c + 2);  // bottom-left
        set1(r + 1, c + 3);  // V_{i+1}
    }

    // Exit corridors for bits set: from V_i go down into a private vertical corridor,
    // then to bottom row, then right to sink. Exactly adds 2^i paths.
    for (int i = 0; i <= B; i++) {
        if ((x >> i) & 1ULL) {
            int r = i + 1;
            int c = 3 * i + 1;
            for (int rr = r + 1; rr <= n; rr++) set1(rr, c);
        }
    }

    cout << n << "\n";
    for (int r = 0; r < n; r++) {
        for (int c = 0; c < n; c++) {
            if (c) cout << ' ';
            cout << a[r][c];
        }
        cout << "\n";
    }

    return 0;
}