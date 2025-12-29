#include <bits/stdc++.h>
using namespace std;
using ll = long long;

ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// Find the smallest divisor d of x such that d > g.
// Assumes x <= 1e12, g < x.
ll min_divisor(ll x, ll g) {
    if (g >= x) return x;
    // If g is large, the smallest divisor > g is x itself,
    // because any proper divisor is <= sqrt(x) <= 1e6.
    if (g > 1000000) return x;
    ll limit = min(1000000LL, (ll)sqrt(x) + 1);
    for (ll d = g + 1; d <= limit; ++d) {
        if (x % d == 0) return d;
    }
    return x; // x is prime or has no divisor <= limit, so x itself is the answer.
}

// Generate greedy sequence starting with 1, a2.
// Returns (V, sequence)
pair<ll, vector<ll>> try_a2(ll n, ll a2) {
    vector<ll> seq = {1, a2};
    ll sum = 1 + a2;
    ll g = 1; // gcd(a2,1)
    while (true) {
        ll cur = seq.back();
        ll d = min_divisor(cur, g);
        ll nxt = cur + d;
        if (nxt > n || seq.size() >= 1000000) break;
        seq.push_back(nxt);
        sum += nxt;
        g = gcd(nxt, cur);
    }
    ll V = seq.size() * sum;
    return {V, seq};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    ll n;
    cin >> n;

    if (n == 1) {
        cout << "1\n1\n";
        return 0;
    }

    ll bestV = -1;
    vector<ll> bestSeq;

    // Try small a2 values.
    for (ll a2 = 2; a2 <= min(1000LL, n); ++a2) {
        auto [V, seq] = try_a2(n, a2);
        if (V > bestV) {
            bestV = V;
            bestSeq = seq;
        }
    }

    // Try a2 values spaced evenly across n.
    for (int i = 1; i <= 1000; ++i) {
        ll a2 = n * i / 1000;
        if (a2 < 2) continue;
        if (a2 > n) break;
        auto [V, seq] = try_a2(n, a2);
        if (V > bestV) {
            bestV = V;
            bestSeq = seq;
        }
    }

    // Fallback (should not be needed)
    if (bestSeq.empty()) {
        bestSeq = {1};
    }

    cout << bestSeq.size() << "\n";
    for (size_t i = 0; i < bestSeq.size(); ++i) {
        if (i) cout << " ";
        cout << bestSeq[i];
    }
    cout << "\n";

    return 0;
}