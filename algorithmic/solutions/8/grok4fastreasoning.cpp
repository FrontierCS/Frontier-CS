#include <bits/stdc++.h>

using namespace std;

struct Instr {
    bool is_halt = false;
    int a = 0, x = 0, b = 0, y = 0;
};

int main() {
    long long k;
    cin >> k;
    if (k == 1) {
        cout << 1 << endl;
        cout << "HALT PUSH 1 GOTO 1" << endl;
        return 0;
    }
    long long t_prime = k - 3;
    long long target = t_prime;
    // find best m
    long long best_m = 0;
    long long min_extra = LLONG_MAX / 2;
    long long low = max(0LL, target / 7 - 100);
    long long high = target / 7 + 100;
    for (long long mm = low; mm <= high; ++mm) {
        int bb = __builtin_popcountll(mm);
        long