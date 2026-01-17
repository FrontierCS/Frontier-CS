#include <bits/stdc++.h>
using namespace std;

int gcd(int a, int b) {
    while (b) {
        int t = a % b;
        a = b;
        b = t;
    }
    return a;
}

// Returns the period and prefix sums for one period of the greedy sequence
// for forbidden distances a and b (coprime).
pair<int, vector<int>> compute_pattern(int a, int b) {
    // We'll compute the sequence long enough to detect periodicity.
    int M = 2 * (a + b) + 100;
    if (M < 100) M = 100;
    vector<char> s(M);
    for (int i = 0; i < M; ++i) {
        bool take = true;
        if (i >= a && s[i - a] == 1) take = false;
        if (i >= b && s[i - b] == 1) take = false;
        s[i] = take;
    }

    // Compute prefix function (KMP) to find the minimal period.
    vector<int> pi(M);
    pi[0] = 0;
    for (int i = 1; i < M; ++i) {
        int j = pi[i - 1];
        while (j > 0 && s[i] != s[j])
            j = pi[j - 1];
        if (s[i] == s[j])
            ++j;
        pi[i] = j;
    }
    int period = M - pi[M - 1];
    if (period <= 0) period = 1;

    // Compute prefix sums for one period.
    vector<int> pref(period + 1, 0);
    for (int i = 0; i < period; ++i)
        pref[i + 1] = pref[i] + s[i];

    return {period, pref};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    long long n;
    int x, y;
    cin >> n >> x >> y;

    int g = gcd(x, y);
    int a = x / g, b = y / g;

    auto [period, pref] = compute_pattern(a, b);
    long long total = 0;
    int sum_period = pref[period];

    for (int r = 0; r < g; ++r) {
        long long L;
        if (r == 0) {
            L = n / g;          // numbers: g, 2g, ..., floor(n/g)*g
        } else {
            if (r > n) L = 0;
            else L = (n - r) / g + 1;
        }
        if (L == 0) continue;

        long long full = L / period;
        long long rem = L % period;
        total += full * sum_period + pref[rem];
    }

    cout << total << '\n';
    return 0;
}