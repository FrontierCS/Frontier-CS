#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        long long k;
        cin >> k;
        long long T = k - 1;  // number of non-empty increasing subsequences

        vector<char> ops;
        while (T > 0) {
            if ((T & 1LL) == 0) {  // even
                T -= 1;
                ops.push_back('A'); // T_prev -> T_prev + 1
            } else {
                T = (T - 1) / 2;
                ops.push_back('B'); // T_prev -> 2*T_prev + 1
            }
        }
        reverse(ops.begin(), ops.end());
        int n = (int)ops.size();

        vector<int> valOrder;
        valOrder.reserve(n);
        for (int i = 0; i < n; ++i) {
            int idx = i + 1; // 1-based index
            if (ops[i] == 'A') {
                valOrder.insert(valOrder.begin(), idx); // smallest value
            } else {
                valOrder.push_back(idx); // largest value
            }
        }

        vector<int> perm(n);
        for (int pos = 0; pos < n; ++pos) {
            int idx = valOrder[pos];      // index at this value rank
            perm[idx - 1] = pos;          // assign value [0..n-1]
        }

        cout << n << "\n";
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}