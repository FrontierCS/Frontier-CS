#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) {
        if (!(cin >> p[i])) return 0;
    }
    int v1 = n / 2;
    int v2 = n / 2 + 1;
    int i1 = -1, i2 = -1;
    for (int i = 1; i <= n; ++i) {
        if (p[i] == v1) i1 = i;
        if (p[i] == v2) i2 = i;
    }
    if (i1 > i2) swap(i1, i2);
    cout << i1 << " " << i2 << "\n";
    return 0;
}