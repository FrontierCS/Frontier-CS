#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n;
    cin >> n;
    const long long MOD = 1000000007LL;
    vector<int> op(n + 1);
    for (int k = n; k >= 1; --k) {
        vector<long long> a(n + 1, 1LL);
        a[k] = MOD - 1;
        cout << "?";
        for (int i = 0; i <= n; ++i) {
            cout << " " << a[i];
        }
        cout << "\n";
        cout.flush();
        long long r;
        cin >> r;
        int p = 0;
        for (int i = k + 1; i <= n; ++i) {
            if (op[i] == 0) ++p;
        }
        if (r > 2000) {
            op[k] = 1;
        } else {
            long long sp = r - p + 1;
            long long ss = (long long)p - r;
            if (1 <= sp && sp <= k) {
                op[k] = 0;
            } else if (1 <= ss && ss <= k) {
                op[k] = 1;
            } else {
                op[k] = 0;
            }
        }
    }
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << op[i];
    }
    cout << "\n";
    cout.flush();
}