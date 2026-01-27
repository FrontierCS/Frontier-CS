#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long n;
    if (!(cin >> n)) return 0;

    vector<unsigned long long> a;

    if (n == 1) {
        a.push_back(1);
    } else if (n == 2) {
        a.push_back(1);
        a.push_back(2);
    } else if (n == 3) {
        a.push_back(2);
        a.push_back(3);
    } else {
        unsigned long long v = 1;
        a.push_back(v);
        while (v <= n / 2) {
            v <<= 1;
            a.push_back(v);
        }
    }
    
    cout << a.size() << "\n";
    for (size_t i = 0; i < a.size(); ++i) {
        if (i) cout << ' ';
        cout << a[i];
    }
    cout << "\n";
    return 0;
}