#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if(!(cin >> n)) return 0;

    const long long MOD = 1000000007LL;
    const long long B = 1000000LL; // B > n ensures distinction

    vector<int> ops(n, 0); // 0 for '+', 1 for '*'

    for (int j = 1; j <= n; ++j) {
        vector<long long> a(n + 1, 1);
        a[0] = 0;
        for (int i = 1; i < j; ++i) a[i] = 0;
        a[j] = B;
        // a[i] for i > j remain 1

        cout << "?";
        for (int i = 0; i <= n; ++i) {
            cout << " " << a[i];
        }
        cout << endl;

        long long R;
        if(!(cin >> R)) return 0;

        if (R >= B) ops[j - 1] = 0; // '+'
        else ops[j - 1] = 1;        // '*'
    }

    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << ops[i];
    }
    cout << endl;
    return 0;
}