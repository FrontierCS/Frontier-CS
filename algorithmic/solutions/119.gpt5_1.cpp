#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    const long long MOD = 1000000007LL;

    vector<int> op(n + 1, -1); // 1..n, 0 for '+', 1 for 'x'
    vector<long long> a(n + 1, 0);

    auto query = [&](const vector<long long>& arr) -> long long {
        cout << "?";
        for (int i = 0; i <= n; ++i) {
            cout << " " << arr[i];
        }
        cout << endl;
        cout.flush();
        long long r;
        if (!(cin >> r)) exit(0);
        return r % MOD;
    };

    for (int k = n; k >= 1; --k) {
        // Prepare query:
        // a0..a_{k-1} = 0 to force S_{k-1} = 0
        // a_k = 1
        // For j>k, choose neutral values:
        //   if op_j is '+', set a_j = 0
        //   if op_j is 'x', set a_j = 1
        fill(a.begin(), a.end(), 0);
        a[k] = 1;
        for (int j = k + 1; j <= n; ++j) {
            if (op[j] == 0) a[j] = 0;
            else if (op[j] == 1) a[j] = 1;
        }
        long long res = query(a);
        // If op_k is '+', result should be 1; if 'x', result should be 0.
        if (res == 1) op[k] = 0;
        else op[k] = 1;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << op[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}