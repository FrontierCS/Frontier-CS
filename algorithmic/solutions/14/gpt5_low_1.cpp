#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto send_walk = [&](long long x) -> long long {
        cout << "walk " << x << endl;
        cout.flush();
        long long res;
        if (!(cin >> res)) exit(0);
        return res;
    };

    auto send_guess = [&](long long g) {
        cout << "guess " << g << endl;
        cout.flush();
        // End interaction; do not read further.
    };

    // Get starting label s without moving
    long long s = send_walk(0);
    long long T = 0; // total steps moved so far
    long long L = 0;
    long long R = 1;

    // Exponential search to find R such that position after R steps is s
    while (true) {
        long long v = send_walk(R - T);
        T = R;
        if (v == s) break;
        L = R;
        R <<= 1;
    }

    // Binary search for minimal D in (L, R] such that position after D steps is s
    while (L + 1 < R) {
        long long M = L + (R - L) / 2;
        long long v = send_walk(M - T);
        T = M;
        if (v == s) {
            R = M;
        } else {
            L = M;
        }
    }

    long long n = R;
    send_guess(n);
    return 0;
}