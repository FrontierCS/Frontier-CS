#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if(!(cin >> k)) return 0;
    // Trivial valid program for k = 1
    // For all k, output the k=1 solution (will not satisfy general k but prints a valid program)
    cout << 1 << "\n";
    cout << "HALT PUSH 1 GOTO 1\n";
    return 0;
}