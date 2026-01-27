#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;
    vector<long long> vals;
    vals.reserve(1LL * n * n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            long long x;
            if (!(cin >> x)) return 0;
            vals.push_back(x);
        }
    }
    if (k < 1 || k > (long long)vals.size()) return 0;
    nth_element(vals.begin(), vals.begin() + (k - 1), vals.end());
    cout << vals[k - 1] << "\n";
    return 0;
}