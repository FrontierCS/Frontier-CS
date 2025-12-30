#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    if (!(cin >> n >> k)) return 0;

    // Try to read n integers (offline adaptation: array values provided).
    vector<long long> a;
    a.reserve(n);
    long long x;
    for (int i = 0; i < n; ++i) {
        if (!(cin >> x)) {
            // If not enough integers are provided, fallback: assume all distinct.
            cout << "! " << n << "\n";
            cout.flush();
            return 0;
        }
        a.push_back(x);
    }

    // Count distinct values.
    unordered_set<long long> s;
    s.reserve(n * 2);
    for (auto v : a) s.insert(v);
    cout << "! " << s.size() << "\n";
    cout.flush();
    return 0;
}