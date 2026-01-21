#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        int k = 1;
        cout << k << "\n";
        cout.flush();

        // Output a simple derangement: cyclic shift by 1
        vector<int> p(n + 1);
        for (int i = 1; i <= n; i++) {
            p[i] = (i % n) + 1;
        }

        cout << "!";
        for (int i = 1; i <= n; i++) {
            cout << " " << p[i];
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}