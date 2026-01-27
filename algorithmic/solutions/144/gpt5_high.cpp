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
    int t = n / 2;
    int pos1 = -1, pos2 = -1;
    for (int i = 1; i <= n; ++i) {
        if (p[i] == t) pos1 = i;
        if (p[i] == t + 1) pos2 = i;
    }
    cout << pos1 << " " << pos2 << "\n";
    return 0;
}