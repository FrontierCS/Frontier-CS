#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto walk = [&](long long x) -> long long {
        cout << "walk " << x << '\n' << flush;
        long long label;
        if (!(cin >> label)) exit(0);
        return label;
    };

    // Get starting label
    long long s = walk(0);

    const int MAX_Q = 200000;
    long long n = -1;
    for (int step = 1; step <= MAX_Q; ++step) {
        long long cur = walk(1);
        if (cur == s) {
            n = step;
            break;
        }
    }

    if (n == -1) n = 1; // fallback guess if limit exceeded

    cout << "guess " << n << '\n' << flush;
    return 0;
}