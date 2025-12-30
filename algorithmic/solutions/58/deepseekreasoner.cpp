#include <bits/stdc++.h>
using namespace std;
using ull = unsigned long long;

int main() {
    ull x;
    cin >> x;
    
    if (x == 1) {
        cout << "1\n1\n";
        return 0;
    }
    
    int n = 0;
    while ((1ULL << n) < x) n++;
    n++;
    if (n < 2) n = 2;
    
    const int MAX_N = 61;
    for (; n <= MAX_N; ++n) {
        vector<vector<int>> grid(n+1, vector<int>(n+1, 0));
        for (int i = 1; i <= n; ++i) {
            grid[i][i] = 1;
            if (i < n) {
                grid[i][i+1] = 1;
                grid[i+1][i] = 1;
            }
        }
        
        auto compute_dp = [&]() -> pair<vector<vector<ull>>, vector<vector<ull>>> {
            vector<vector<ull>> dp_start(n+1, vector<ull>(n+1, 0));
            vector<vector<ull>> dp_end(n+1, vector<ull>(n+1, 0));
            dp_start[1][1] = grid[1][1];
            for (int i = 1; i <= n; ++i) {
                for (int j = 1; j <= n; ++j) {
                    if (i==1 && j==1) continue;
                    if (grid[i][j] == 0) continue;
                    ull val = 0;
                    if (i > 1) val += dp_start[i-1][j];
                    if (j > 1) val += dp_start[i][j-1];
                    dp_start[i][j] = val;
                }
            }
            dp_end[n][n] = grid[n][n];
            for (int i = n; i >= 1; --i) {
                for (int j = n; j >= 1; --j) {
                    if (i==n && j==n) continue;
                    if (grid[i][j] == 0) continue;
                    ull val = 0;
                    if (i < n) val += dp_end[i+1][j];
                    if (j < n) val += dp_end[i][j+1];
                    dp_end[i][j] = val;
                }
            }
            return {dp_start, dp_end};
        };
        
        auto [dp_start, dp_end] = compute_dp();
        ull total = dp_start[n][n];
        ull need = total - x;
        
        bool ok = true;
        while (need > 0) {
            ull best_contrib = 0;
            int best_i = -1, best_j = -1;
            for (int i = 1; i <= n; ++i) {
                for (int j = 1; j <= n; ++j) {
                    if (grid[i][j] == 0) continue;
                    if (i==1 && j==1) continue;
                    if (i==n && j==n) continue;
                    ull contrib = dp_start[i][j] * dp_end[i][j];
                    if (contrib <= need && contrib > best_contrib) {
                        best_contrib = contrib;
                        best_i = i;
                        best_j = j;
                    }
                }
            }
            if (best_contrib == 0) {
                ok = false;
                break;
            }
            grid[best_i][best_j] = 0;
            need -= best_contrib;
            tie(dp_start, dp_end) = compute_dp();
        }
        
        if (ok) {
            cout << n << "\n";
            for (int i = 1; i <= n; ++i) {
                for (int j = 1; j <= n; ++j) {
                    cout << grid[i][j] << " \n"[j==n];
                }
            }
            return 0;
        }
    }
    
    cout << "1\n1\n";
    return 0;
}