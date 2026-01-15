#include <iostream>
using namespace std;

int main() {
    int k;
    cin >> k;
    int c = (k - 1) / 2;
    int n = k; // because k = 2c + 1
    cout << n << "\n";
    for (int i = 1; i <= c; ++i) {
        int next = i + 1;
        if (i == c) next = c + 1;
        cout << "POP 2 GOTO " << c + 1 << " PUSH 1 GOTO " << next << "\n";
    }
    for (int i = c + 1; i <= 2 * c; ++i) {
        cout << "POP 1 GOTO " << i + 1 << " PUSH 2 GOTO " << i << "\n";
    }
    cout << "HALT PUSH 1 GOTO 1\n";
    return 0;
}