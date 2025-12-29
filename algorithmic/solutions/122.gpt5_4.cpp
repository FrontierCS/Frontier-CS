#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> vals;
    long long x;
    while (cin >> x) vals.push_back(x);
    if (vals.empty()) return 0;
    if (vals.size() == 1) {
        cout << vals[0] << "\n";
        return 0;
    }
    if (vals[0] == (long long)vals.size() - 1) {
        for (size_t i = 1; i < vals.size(); ++i) {
            cout << vals[i] << "\n";
        }
        return 0;
    }
    int t = (int)vals[0];
    if ((int)vals.size() >= t + 1) {
        for (int i = 1; i <= t; ++i) {
            cout << vals[i] << "\n";
        }
    } else {
        for (size_t i = 0; i < vals.size(); ++i) {
            cout << vals[i] << "\n";
        }
    }
    return 0;
}