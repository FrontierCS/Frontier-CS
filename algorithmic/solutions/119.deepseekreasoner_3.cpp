#include <iostream>
#include <vector>

using namespace std;

int main() {
    int n;
    cin >> n;
    vector<long long> R(n + 1);
    const long long MOD = 1000000007;

    // Make n queries: for each i, set a_i = 2, others = 1, a0 = 1
    for (int i = 1; i <= n; ++i) {
        cout << "? 1";
        for (int j = 1; j <= n; ++j) {
            if (j == i) cout << " 2";
            else cout << " 1";
        }
        cout << endl;
        cin >> R[i];
    }

    // A = number of addition operators
    long long A = R[1] - 2;
    long long base = A + 2;

    vector<long long> D(n + 1, 0);
    bool all_zero = true;
    int first_nonzero = -1;

    for (int i = 2; i <= n; ++i) {
        D[i] = R[i] - base;               // small integer, no modulo needed
        if (D[i] != 0) {
            all_zero = false;
            if (first_nonzero == -1) first_nonzero = i;
        }
    }

    vector<int> ans(n + 1, 0);

    if (all_zero) {
        // All D[i] are zero: either all '+' or a block of '*' then all '+'
        int t = n - A;                     // number of '*' at the beginning
        for (int i = 1; i <= t; ++i) ans[i] = 1;
        for (int i = t + 1; i <= n; ++i) ans[i] = 0;
    } else {
        int k = first_nonzero;
        long long d = D[k];                // number of additions before k
        int t = (k - 1) - d;               // number of '*' before k
        for (int i = 1; i <= t; ++i) ans[i] = 1;
        for (int i = t + 1; i <= k - 1; ++i) ans[i] = 0;
        ans[k] = 1;

        int X = d;                         // current count of additions
        for (int i = k + 1; i <= n; ++i) {
            if (D[i] == 0) {
                ans[i] = 0;
                ++X;
            } else if (D[i] == X) {
                ans[i] = 1;
            } else {
                // This case should not happen with correct responses
                ans[i] = 1;                // safe fallback
            }
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}