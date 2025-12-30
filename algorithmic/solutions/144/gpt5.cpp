#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        if (!(cin >> p[i])) return 0;
    }
    vector<int> pos(n + 1, -1);
    for (int i = 0; i < n; ++i) pos[p[i]] = i + 1;
    cout << "1 " << pos[n / 2] << " " << pos[n / 2 + 1] << "\n";
    return 0;
}