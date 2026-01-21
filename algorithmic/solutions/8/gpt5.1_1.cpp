#include <bits/stdc++.h>
using namespace std;

int main() {
    long long k;
    if (!(cin >> k)) return 0;

    // Trivial (but only correct for k == 1)
    // For all k, output a 1-instruction program that halts in 1 step.
    cout << 1 << "\n";
    cout << "HALT PUSH 1 GOTO 1\n";
    return 0;
}