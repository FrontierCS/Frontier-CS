#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long n;
    if (!(cin >> n)) return 0;
    
    vector<unsigned long long> a;
    unsigned long long v = 1;
    while (v <= n && a.size() < 1000000) {
        a.push_back(v);
        if (v > n / 2) break;
        v *= 2;
    }
    
    cout << a.size() << "\n";
    for (size_t i = 0; i < a.size(); ++i) {
        if (i) cout << ' ';
        cout << a[i];
    }
    cout << "\n";
    return 0;
}