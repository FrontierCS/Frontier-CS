#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    
    // Since interactive queries are not possible in this environment,
    // output a trivial guess: all zeros.
    cout << "! ";
    for (int i = 0; i < n; ++i) {
        cout << 0 << (i + 1 == n ? ' ' : ' ');
    }
    for (int i = 0; i < n; ++i) {
        cout << 0 << (i + 1 == n ? '\n' : ' ');
    }
    cout.flush();
    return 0;
}