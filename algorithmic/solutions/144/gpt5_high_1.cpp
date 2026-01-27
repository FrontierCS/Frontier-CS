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
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) pos[p[i]] = i;
    int m1 = n / 2;
    int m2 = m1 + 1;
    cout << pos[m1] << " " << pos[m2] << "\n";
    return 0;
}