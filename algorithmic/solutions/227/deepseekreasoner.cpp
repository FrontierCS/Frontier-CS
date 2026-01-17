#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    vector<int> a, b, c, d;
    int last_a = 0, last_c = 0;       // increasing chains, -inf as 0
    int last_b = n + 1, last_d = n + 1; // decreasing chains, +inf as n+1

    for (int x : p) {
        // Try increasing chains (need last < x)
        vector<pair<int, int>> inc;
        if (last_a < x) inc.emplace_back(last_a, 0);
        if (last_c < x) inc.emplace_back(last_c, 1);
        if (!inc.empty()) {
            // choose the chain with largest last value
            sort(inc.begin(), inc.end());
            int chain = inc.back().second;
            if (chain == 0) {
                a.push_back(x);
                last_a = x;
            } else {
                c.push_back(x);
                last_c = x;
            }
            continue;
        }

        // Try decreasing chains (need last > x)
        vector<pair<int, int>> dec;
        if (last_b > x) dec.emplace_back(last_b, 0);
        if (last_d > x) dec.emplace_back(last_d, 1);
        if (!dec.empty()) {
            // choose the chain with smallest last value (closest to x from above)
            sort(dec.begin(), dec.end());
            int chain = dec[0].second;
            if (chain == 0) {
                b.push_back(x);
                last_b = x;
            } else {
                d.push_back(x);
                last_d = x;
            }
            continue;
        }

        // Must break monotonicity: choose chain with minimal penalty
        vector<pair<int, int>> penalties;
        penalties.emplace_back(last_a - x, 0); // A (increasing)
        penalties.emplace_back(last_c - x, 1); // C (increasing)
        penalties.emplace_back(x - last_b, 2); // B (decreasing)
        penalties.emplace_back(x - last_d, 3); // D (decreasing)
        sort(penalties.begin(), penalties.end());
        int chain = penalties[0].second;
        if (chain == 0) {
            a.push_back(x);
            last_a = x;
        } else if (chain == 1) {
            c.push_back(x);
            last_c = x;
        } else if (chain == 2) {
            b.push_back(x);
            last_b = x;
        } else {
            d.push_back(x);
            last_d = x;
        }
    }

    // Output the partition
    cout << a.size() << " " << b.size() << " " << c.size() << " " << d.size() << "\n";
    for (int v : a) cout << v << " ";
    cout << "\n";
    for (int v : b) cout << v << " ";
    cout << "\n";
    for (int v : c) cout << v << " ";
    cout << "\n";
    for (int v : d) cout << v << " ";
    cout << "\n";

    return 0;
}