#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    int n;
    while ( (cin >> n) ) {
        vector<string> C(n);
        for (int i = 0; i < n; ++i) {
            cin >> C[i];
        }
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << '\n';
    }
    return 0;
}