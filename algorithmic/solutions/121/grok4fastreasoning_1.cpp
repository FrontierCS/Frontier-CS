#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<string> pat(m);
    for (int i = 0; i < m; i++) {
        cin >> pat[i];
    }
    auto get = [](char ch) -> int {
        if (ch == 'A') return 0;
        if (ch == 'C') return 1;
        if (ch == 'G') return 2;
        if (ch == 'T') return 3;
        return -1;
    };
    int MS = 1 << m;
    vector<vector<int>> survive(n, vector<int>(4, 0));
    for (int pos = 0; pos < n; pos++) {
        for (int c = 0; c < 4; c++) {
            int mask = 0;
            for (int i = 0; i < m; i++) {
                int req = get(pat[i][pos]);
                if (req == -1 || req == c) {
                    mask |= (1 << i);
                }
            }
            survive[pos][c] = mask;
        }
    }
    vector<long long> dp[2];
    dp[0] = vector<long long>(MS, 0LL);
    dp[1] = vector<long long>(MS, 0LL);
    int now = 0;
    int full = (1 << m) - 1;
    dp[now][full] = 1LL;
    for (int pos = 0; pos < n; pos++) {
        int nxt = 1 - now;
        fill(dp[nxt].begin(), dp[nxt].end(), 0LL);
        for (int mask = 0; mask < MS; mask++) {
            long long ways = dp[now][mask];
            if (ways == 0) continue;
            for (int c = 0; c < 4; c++) {
                int newm = mask & survive[pos][c];
                dp[nxt][newm] += ways;
            }
        }
        now = nxt;
    }
    long long valid = 0;
    for (int mask = 1; mask < MS; mask++) {
        valid += dp[now][mask];
    }
    long long total = 1LL;
    for (int i = 0; i < n; i++) {
        total *= 4LL;
    }
    double prob = static_cast<double>(valid) / total;
    printf("%.10f\n", prob);
    return 0;
}