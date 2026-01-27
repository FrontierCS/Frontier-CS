#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> all;
    long long x;
    while (cin >> x) all.push_back(x);
    if (all.empty()) return 0;
    int n = (int)all[0];
    vector<long long> arr;
    for (size_t i = 1; i < all.size(); ++i) arr.push_back(all[i]);
    
    if ((int)arr.size() == n) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << arr[i];
        }
        cout << '\n';
    } else {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << '\n';
    }
    return 0;
}