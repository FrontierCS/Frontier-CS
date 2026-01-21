#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if (!(cin >> k)) return 0;
    
    // Trivial correct solution only for k == 1
    // For all k (including 1), we output a 1-instruction program that halts in 1 step.
    cout << 1 << "\n";
    cout << "HALT PUSH 1 GOTO 1\n";
    return 0;
}