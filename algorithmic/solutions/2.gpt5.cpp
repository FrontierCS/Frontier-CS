#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> rest;
    int x;
    while (cin >> x) rest.push_back(x);
    
    vector<int> perm(n);
    if ((int)rest.size() >= n) {
        for (int i = 0; i < n; ++i) perm[i] = rest[i];
    } else {
        for (int i = 0; i < n; ++i) perm[i] = i + 1;
    }
    
    cout << 1;
    for (int i = 0; i < n; ++i) cout << " " << perm[i];
    cout << "\n";
    cout.flush();
    return 0;
}