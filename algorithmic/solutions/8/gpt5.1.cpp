#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if (!(cin >> k)) return 0;

    if (k == 1) {
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }

    long long n = min<long long>(k, 512);
    cout << n << "\n";

    for (long long i = 1; i < n; ++i) {
        cout << "POP 1 GOTO " << (i + 1) << " PUSH 1 GOTO " << (i + 1) << "\n";
    }
    cout << "HALT PUSH 1 GOTO 1\n";

    return 0;
}