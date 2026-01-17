#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    string s;
    cin >> s;
    int N = s.size();
    vector<int> prefix(N + 1, 0);
    for (int i = 0; i < N; i++) {
        prefix[i + 1] = prefix[i] + (s[i] == '1' ? 1 : 0);
    }
    long long ans = 0;
    for (int k = 1;; k++) {
        long long L = (long long)k * (k + 1);
        if (L > N) break;
        int len = (int)L;
        for (int i = 0; i <= N - len; i++) {
            int ones = prefix[i + len] - prefix[i];
            if (ones == k) {
                ans++;
            }
        }
    }
    cout << ans << endl;
    return 0;
}