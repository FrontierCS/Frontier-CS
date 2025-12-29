#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, m;
    cin >> n >> m;
    vector<vector<unsigned char>> b(m, vector<unsigned char>(n, 0));
    for (int i = 0; i < m; i++) {
        string s;
        cin >> s;
        for (int j = 0; j < n; j++) {
            char c = s[j];
            if (c == 'A') b[i][j] = 1 << 0;
            else if (c == 'C') b[i][j] = 1 << 1;
            else if (c == 'G') b[i][j] = 1 << 2;
            else if (c == 'T') b[i][j] = 1 << 3;
            else b[i][j] = 0; // '?'
        }
    }
    int popc[16];
    for (int i = 0; i < 16; i++) popc[i] = __builtin_popcount(i);

    vector<long double> pow4(n + 1);
    pow4[0] = 1.0L;
    for (int i = 1; i <= n; i++) pow4[i] = pow4[i - 1] * 4.0L;

    int total_masks = 1 << m;
    unsigned char* dp = new unsigned char[total_masks * n];
    memset(dp, 0, total_masks * n * sizeof(unsigned char));

    for (int mask = 1; mask < total_masks; mask++) {
        int i = __builtin_ctz(mask);
        int prev = mask ^ (1 << i);
        unsigned char* prev_row = dp + prev * n;
        unsigned char* cur_row = dp + mask * n;
        for (int j = 0; j < n; j++) {
            cur_row[j] = prev_row[j] | b[i][j];
        }
    }

    long double ans = 0.0L;
    for (int mask = 1; mask < total_masks; mask++) {
        unsigned char* row = dp + mask * n;
        bool conflict = false;
        int free_cnt = 0;
        for (int j = 0; j < n; j++) {
            unsigned char val = row[j];
            if (popc[val] > 1) {
                conflict = true;
                break;
            }
            if (val == 0) free_cnt++;
        }
        if (!conflict) {
            long double term = pow4[free_cnt] / pow4[n];
            int bits = __builtin_popcount(mask);
            if (bits % 2 == 1) ans += term;
            else ans -= term;
        }
    }

    delete[] dp;
    cout << fixed << setprecision(15) << ans << endl;
    return 0;
}