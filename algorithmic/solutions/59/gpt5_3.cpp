#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<long long> tokens;
    long long x;
    while (cin >> x) tokens.push_back(x);
    
    vector<int> result(n);
    if ((int)tokens.size() >= n) {
        vector<long long> v(tokens.begin(), tokens.begin() + n);
        bool isJ = true;
        for (int i = 0; i < n; ++i) {
            long long l = i + 1;
            long long r = min(n, i + 3);
            if (v[i] < l || v[i] > r) {
                isJ = false;
                break;
            }
        }
        if (isJ) {
            vector<int> a(n);
            for (int i = 0; i < n; ++i) a[i] = i + 1;
            for (int i = 0; i < n; ++i) {
                int j = (int)v[i] - 1;
                swap(a[i], a[j]);
            }
            for (int i = 0; i < n; ++i) result[i] = a[i];
        } else {
            for (int i = 0; i < n; ++i) result[i] = (int)v[i];
        }
    } else {
        for (int i = 0; i < n; ++i) result[i] = i + 1;
    }
    
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << result[i];
    }
    cout << '\n';
    
    return 0;
}