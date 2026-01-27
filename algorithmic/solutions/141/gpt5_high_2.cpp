#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    if (!(cin >> n >> k)) return 0;

    vector<long long> a(n);
    for (int i = 0; i < n; ++i) {
        if (!(cin >> a[i])) return 0;
    }
    unordered_set<long long> s;
    for (auto &x : a) s.insert(x);
    cout << s.size() << "\n";
    return 0;
}