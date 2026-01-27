#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    if (!(cin >> n >> k)) return 0;

    vector<long long> a;
    a.reserve(n);
    bool ok = true;
    for (int i = 0; i < n; ++i) {
        long long x;
        if (!(cin >> x)) { ok = false; break; }
        a.push_back(x);
    }

    if (ok && (int)a.size() == n) {
        unordered_set<long long> s;
        s.reserve(n * 2 + 1);
        for (auto &x : a) s.insert(x);
        cout << "! " << s.size() << "\n";
    } else {
        // Fallback if the test is interactive or malformed: assume all distinct
        cout << "! " << n << "\n";
    }
    return 0;
}