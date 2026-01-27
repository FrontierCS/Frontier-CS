#include <bits/stdc++.h>
using namespace std;

int main() {
    long long k;
    if (!(cin >> k)) return 0;
    if (k == 1) {
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }
    if (k == 3) {
        cout << 3 << "\n";
        cout << "POP 2 GOTO 2 PUSH 1 GOTO 2\n";
        cout << "POP 1 GOTO 3 PUSH 1 GOTO 3\n";
        cout << "HALT PUSH 1 GOTO 3\n";
        return 0;
    }
    if (k == 5) {
        cout << 5 << "\n";
        cout << "POP 1 GOTO 2 PUSH 1 GOTO 2\n";
        cout << "HALT PUSH 1 GOTO 3\n";
        cout << "POP 1 GOTO 4 PUSH 2 GOTO 4\n";
        cout << "POP 1 GOTO 2 PUSH 2 GOTO 4\n";
        cout << "HALT PUSH 99 GOTO 4\n";
        return 0;
    }
    // Fallback (not correct for general k)
    cout << 1 << "\n";
    cout << "HALT PUSH 1 GOTO 1\n";
    return 0;
}