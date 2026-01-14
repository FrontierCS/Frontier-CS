#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    string s;
    cin >> s;
    int n = s.size();
    vector<int> pref(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        pref[i] = pref[i - 1] + (s[i - 1] == '1');
    }
    long long ans = 0;
    int maxo = 0;
    for (int oo = 1;; oo++) {
        long long len = (long long)oo * (oo + 1);
        if (len > n) {
            maxo = oo - 1;
            break;
        }
    }
    for (int o = 1; o <= maxo; o++) {
        int len = o * (o + 1);
        if (len > n) continue;
        for (int i = 0; i + len <= n; i++) {
            if (pref[i + len] - pref[i] == o) ans++;
        }
    }
    cout << ans << endl;
    return 0;
}