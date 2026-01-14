#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    string s;
    cin >> s;
    int n = s.size();
    vector<int> prefix(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        prefix[i] = prefix[i - 1] + (s[i - 1] == '1' ? 1 : 0);
    }
    long long ans = 0;
    for (int k = 1;; k++) {
        long long L = (long long)k * (k + 1);
        if (L > n) break;
        int LL = (int)L;
        int max_i = n - LL;
        if (max_i < 0) continue;
        long long cnt = 0;
        int target = k;
        for (int i = 0; i <= max_i; i++) {
            int diff = prefix[i + LL] - prefix[i];
            if (diff == target) cnt++;
        }
        ans += cnt;
    }
    cout << ans << endl;
    return 0;
}