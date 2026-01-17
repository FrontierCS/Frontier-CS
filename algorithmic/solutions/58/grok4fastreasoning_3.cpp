#include <bits/stdc++.h>
using namespace std;

int main() {
    long long x;
    cin >> x;
    vector<long long> B(301, 0);
    B[1] = 1;
    for (int nn = 2; nn <= 300; ++nn) {
        __int128 res = 1;
        int a = 2 * nn - 2;
        int b = nn - 1;
        if (b > a - b) b = a - b;
        bool over = false;
        for (int t = 1; t <= b; ++t) {
            res *= (__int128)(a - t + 1);
            res /= (__int128)t;
            if (res > (__int128)2000000000000000000LL) {
                over = true;
                break;
            }
        }
        if (over) {
            B[nn] = 2000000000000000000LL;
        } else {
            B[nn] = (long long)res;
        }
    }
    vector<int> ks;
    long long current = x;
    while (current > 0) {
        int best_k = 1;
        long long best_b = B[1];
        for (int t = 1; t <= 300; ++t) {
            if (B[t] <= current && B[t] > best_b) {
                best_b = B[t];
                best_k = t;
            }
        }
        ks.push_back(best_k);
        current -= best_b;
    }
    int num_blocks = ks.size();
    if (num_blocks == 0) {
        // x=0 not possible
        num_blocks = 1;
        ks = {1};
        current = 1;
    }
    int max_k = 0;
    int total_width = 0;
    for (int k : ks) {
        max_k = max(max_k, k);
        total_width += k;
    }
    // now place with gaps: total columns = total_width + (num_blocks - 1) for gaps
    int n = max(max_k, total_width + num_blocks - 1);
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, 0));
    int cur_col = 1;
    for (int i = 0; i < num_blocks; ++i) {
        int k = ks[i];
        int start_col = cur_col;
        // place block
        for (int rr = 1; rr <= k; ++rr) {
            for (int cc = 0; cc < k; ++cc) {
                grid[rr][start_col + cc] = 1;
            }
        }
        // exit route
        int exit_r = k;
        int exit_c = start_col + k - 1;
        for (int rr = exit_r; rr <= n; ++rr) {
            grid[rr][exit_c] = 1;
        }
        for (int cc = exit_c; cc <= n; ++cc) {
            grid[n][cc] = 1;
        }
        cur_col = start_col + k;
        if (i < num_blocks - 1) {
            // gap column cur_col
            grid[1][cur_col] = 1;
            // others 0 already
            cur_col++;
        }
    }
    // set row 1 bus up to the last used col
    int last_used_col = cur_col - 1;
    for (int cc = 1; cc <= last_used_col; ++cc) {
        grid[1][cc] = 1;
    }
    // if last_used_col < n, row1 after 0 already
    // ensure (n,n)=1
    grid[n][n] = 1;
    cout << n << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j];
            if (j < n) cout << " ";
        }
        cout << endl;
    }
    return 0;
}