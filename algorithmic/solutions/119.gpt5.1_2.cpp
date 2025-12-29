#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // op[i]: 0 for '+', 1 for '*'
    vector<int> op(n + 1, 0);

    for (int i = n; i >= 1; --i) {
        vector<long long> a(n + 1, 0);

        // Prefix: force v_{i-1} = 0 regardless of unknown operators
        a[0] = 0;
        for (int j = 1; j < i; ++j) a[j] = 0;

        // At position i: set to 1 so that
        //   if op_i = '+': v_i = 0 + 1 = 1
        //   if op_i = '*': v_i = 0 * 1 = 0
        a[i] = 1;

        // Suffix: operators op[j] (j > i) are already known
        // Make each gate act as identity:
        //   '+' with 0: v_j = v_{j-1} + 0 = v_{j-1}
        //   '*' with 1: v_j = v_{j-1} * 1 = v_{j-1}
        for (int j = i + 1; j <= n; ++j) {
            if (op[j] == 0) a[j] = 0; // '+'
            else a[j] = 1;           // '*'
        }

        // Issue query
        cout << "?";
        for (int j = 0; j <= n; ++j) cout << " " << a[j];
        cout << '\n';
        cout.flush();

        long long res;
        if (!(cin >> res)) return 0;

        // Final value is 1 if op_i is '+', 0 if op_i is '*'
        op[i] = (res == 1 ? 0 : 1);
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << op[i];
    cout << '\n';
    cout.flush();

    return 0;
}