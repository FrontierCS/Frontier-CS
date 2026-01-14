#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    string s;
    getline(cin, s);
    int n = s.size();
    
    vector<int> p1(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        p1[i + 1] = p1[i] + (s[i] == '1');
    }
    int m = p1[n];
    int Z = n - m;
    
    int max_a = min(m, (int)sqrt(Z));
    int limit = (int)((sqrt(4.0 * n + 1) - 1) / 2);
    max_a = min(max_a, limit);
    
    long long ans = 0;
    const char *str = s.c_str();
    
    for (int a = 1; a <= max_a; ++a) {
        long long L = a + 1LL * a * a;
        if (L > n) break;
        int L_int = (int)L;
        int diff = p1[L_int] - p1[0];
        for (int i = 0; i <= n - L_int; ++i) {
            if (diff == a) ++ans;
            if (i < n - L_int) {
                diff += (str[i + L_int] == '1') - (str[i] == '1');
            }
        }
    }
    
    cout << ans << '\n';
    return 0;
}