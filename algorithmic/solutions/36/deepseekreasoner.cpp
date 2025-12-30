#include <iostream>
#include <vector>
#include <cmath>
using namespace std;

int main() {
    int m = 1000000;
    cout << "0 " << m;
    for (int i = 1; i <= m; ++i) {
        cout << " " << i;
    }
    cout << endl;
    cout.flush();
    
    long long C;
    cin >> C;
    
    // Find n such that inserting 1..m gives C collisions.
    for (int n = 2; n <= m; ++n) {
        long long q = m / n;
        long long r = m % n;
        long long calc = n * q * (q - 1) / 2 + r * q;
        if (calc == C) {
            cout << "1 " << n << endl;
            cout.flush();
            return 0;
        }
    }
    // If not found, n > m. We must still guess; guess a reasonable value.
    // Since n > 1e6 and <= 1e9, guess n = 1000000000 (a common upper bound).
    // This guess may be wrong, but we have no further information.
    cout << "1 1000000000" << endl;
    cout.flush();
    return 0;
}