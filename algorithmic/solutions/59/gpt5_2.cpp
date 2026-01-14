#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a;
    a.reserve(n);
    for (int i = 0; i < n; ++i) {
        int x;
        if (cin >> x) a.push_back(x);
        else break;
    }
    if ((int)a.size() != n) {
        a.clear();
        for (int i = 1; i <= n; ++i) a.push_back(i);
    }
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << a[i];
    }
    cout << '\n';
    return 0;
}