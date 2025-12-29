#include <bits/stdc++.h>
using namespace std;
using i64 = long long;

i64 gcd(i64 a, i64 b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Get starting label
    cout << "walk 0" << endl;
    i64 start_label;
    cin >> start_label;

    unordered_map<i64, i64> seen; // label -> cumulative distance
    seen[start_label] = 0;
    i64 dist = 0;
    vector<i64> multiples;
    int walks = 0;
    const int MAX_WALKS = 200000;

    // Random number generator
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<i64> dis(1, 1000000000);

    // Perform random walks until we have enough multiples or reach the limit
    while (walks < MAX_WALKS && multiples.size() < 5) {
        i64 x = dis(rng);
        cout << "walk " << x << endl;
        i64 label;
        cin >> label;
        walks++;
        dist += x;

        if (seen.count(label)) {
            i64 diff = dist - seen[label];
            multiples.push_back(diff);
        }
        seen[label] = dist;
    }

    i64 g = 0;
    for (i64 m : multiples) {
        g = gcd(g, m);
    }

    // Fallback if no multiples found: guess the maximum label seen
    if (g == 0) {
        i64 max_label = 0;
        for (auto &p : seen) {
            if (p.first > max_label) max_label = p.first;
        }
        g = max_label;
    }

    cout << "guess " << g << endl;
    return 0;
}