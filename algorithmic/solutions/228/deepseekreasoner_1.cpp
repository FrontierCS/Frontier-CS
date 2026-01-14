#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    cin >> s;
    int n = s.size();
    vector<int> arr(n);
    int total_ones = 0;
    for (int i = 0; i < n; i++) {
        arr[i] = s[i] - '0';
        total_ones += arr[i];
    }
    long long ans = 0;
    for (int t = 1; t * (t + 1) <= n; t++) {
        if (t > total_ones) continue;
        int L = t * t + t;
        if (L > n) break;
        int ones = 0;
        for (int i = 0; i < L; i++) ones += arr[i];
        if (ones == t) ans++;
        for (int i = 0; i < n - L; i++) {
            ones = ones - arr[i] + arr[i + L];
            if (ones == t) ans++;
        }
    }
    cout << ans << '\n';
    return 0;
}