#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s;
    getline(cin, s);
    int n = s.size();
    vector<int> pre(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        pre[i + 1] = pre[i] + (s[i] == '1');
    }
    int total_ones = pre[n];
    int total_zeros = n - total_ones;
    
    // No non-empty valid substring if there are no zeros or no ones
    if (total_ones == 0 || total_zeros == 0) {
        cout << 0 << endl;
        return 0;
    }
    
    long long ans = 0;
    for (int a = 1; ; ++a) {
        if (a > total_ones) break;
        long long L = 1LL * a * a + a;
        if (L > n) break;
        
        int cnt = pre[L] - pre[0];
        if (cnt == a) ++ans;
        for (int i = 1; i <= n - L; ++i) {
            cnt -= (s[i - 1] == '1');
            cnt += (s[i + L - 1] == '1');
            if (cnt == a) ++ans;
        }
    }
    
    cout << ans << endl;
    return 0;
}