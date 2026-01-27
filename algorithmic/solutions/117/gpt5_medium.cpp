#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) n = 1;
    
    cout << "!";
    for (long long i = 0; i < n; ++i) cout << " 0";
    for (long long i = 0; i < n; ++i) cout << " 0";
    cout << "\n";
    cout.flush();
    return 0;
}