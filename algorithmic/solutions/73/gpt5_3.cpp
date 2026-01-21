#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> c(n, 0);
    for (int i = 0; i < n - 1; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int b;
            if (!(cin >> b)) b = 0;
            c[i] += b;
            c[j] += 1 - b;
        }
    }
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (c[i] + 1);
    }
    cout << '\n';
    return 0;
}