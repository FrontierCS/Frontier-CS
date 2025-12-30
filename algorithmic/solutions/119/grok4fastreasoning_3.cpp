#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<int> ops(n + 1, 0);
    const long long MOD = 1000000007LL;
    const long long A = 601LL;
    long long curr_ksuf = 0;
    for (int i = n; i >= 1; --i) {
        cout << "? 1";
        for (int j = 1; j <= n; ++j) {
            long long aj = (j == i ? A : 1LL);
            cout << " " << aj;
        }
        cout << endl;
        long long res;
        cin >> res;
        long long obs = (res - curr_ksuf + MOD) % MOD;
        bool is_mult = false;
        if (obs % A == 0) {
            long long kk = obs / A;
            if (kk >= 1 && kk <= (long long)i) {
                is_mult = true;
            }
        }
        ops[i] = is_mult ? 1 : 0;
        if (ops[i] == 0) ++curr_ksuf;
    }
    cout << "!";
    for (int j = 1; j <= n; ++j) {
        cout << " " << ops[j];
    }
    cout << endl;
    return 0;
}