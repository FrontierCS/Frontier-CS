#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<int> omega(n + 1, 0);
    for (int p = 2; p <= n; ++p) {
        if (omega[p] == 0) {
            for (long long m = p; m <= n; m += p) {
                int temp = m;
                while (temp % p == 0) {
                    omega[m]++;
                    temp /= p;
                }
            }
        }
    }
    for (int i = 1; i <= n; ++i) {
        int val = (omega[i] % 2 == 0 ? 1 : -1);
        cout << val;
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}