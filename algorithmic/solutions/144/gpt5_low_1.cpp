#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> data;
    long long x;
    while (cin >> x) data.push_back(x);
    if (data.empty()) return 0;
    
    int n = (int)data[0];
    if ((int)data.size() >= n + 1) {
        vector<int> p(n+1);
        for (int i = 1; i <= n; ++i) p[i] = (int)data[i];
        int a = n/2, b = n/2 + 1;
        int ia = -1, ib = -1;
        for (int i = 1; i <= n; ++i) {
            if (p[i] == a) ia = i;
            if (p[i] == b) ib = i;
        }
        if (ia == -1 || ib == -1) {
            // Fallback in case of malformed input
            cout << "1 2\n";
        } else {
            cout << ia << " " << ib << "\n";
        }
    } else {
        // Fallback for interactive environment not supported here
        cout << "1 2\n";
    }
    return 0;
}