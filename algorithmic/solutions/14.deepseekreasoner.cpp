#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_map>
#include <cmath>
#include <cstdlib>
#include <functional>

using namespace std;

typedef long long ll;

ll walk(ll x) {
    cout << "walk " << x << endl;
    ll res;
    cin >> res;
    return res;
}

void guess(ll g) {
    cout << "guess " << g << endl;
    exit(0);
}

int main() {
    // Initial step
    ll cur_label = walk(0);
    ll max_label = cur_label;
    unordered_map<ll, ll> seen; // label -> total steps when first seen
    seen[cur_label] = 0;
    ll total_steps = 0;
    int walks_count = 1;

    vector<ll> Ds;

    // Pseudo-random step generator
    const ll MOD = 1000000000;
    ll a = 1000000007;
    ll c = 123456789;
    ll step_seed = 123456789;

    // Collect until first collision or up to 200000 walks
    while (walks_count < 200000 && Ds.empty()) {
        step_seed = (step_seed * a + c) % MOD;
        ll x = step_seed + 1;  // in [1, MOD]
        cur_label = walk(x);
        total_steps += x;
        walks_count++;
        if (cur_label > max_label) max_label = cur_label;

        if (seen.count(cur_label)) {
            ll d = total_steps - seen[cur_label];
            if (d > 0) {
                Ds.push_back(d);
            }
        } else {
            seen[cur_label] = total_steps;
        }
    }

    // If still no collision (extremely unlikely), guess max_label as fallback
    if (Ds.empty()) {
        guess(max_label);
        return 0;
    }

    // Take the smallest D (most likely the smallest multiple of n)
    ll D = *min_element(Ds.begin(), Ds.end());

    // Factor D
    vector<pair<ll, int>> factors;
    ll temp = D;
    for (ll i = 2; i * i <= temp; ++i) {
        if (temp % i == 0) {
            int cnt = 0;
            while (temp % i == 0) {
                temp /= i;
                cnt++;
            }
            factors.emplace_back(i, cnt);
        }
    }
    if (temp > 1) {
        factors.emplace_back(temp, 1);
    }

    // Generate all divisors of D
    vector<ll> divisors;
    function<void(int, ll)> generate = [&](int idx, ll prod) {
        if (idx == (int)factors.size()) {
            divisors.push_back(prod);
            return;
        }
        ll p = factors[idx].first;
        int exp = factors[idx].second;
        ll cur = 1;
        for (int i = 0; i <= exp; ++i) {
            generate(idx + 1, prod * cur);
            cur *= p;
        }
    };
    generate(0, 1);
    sort(divisors.begin(), divisors.end());

    // Test divisors in ascending order
    for (ll d : divisors) {
        if (d < max_label) continue;
        if (walks_count >= 200000) break;   // safety
        ll before = cur_label;
        cur_label = walk(d);
        walks_count++;
        if (cur_label == before) {
            guess(d);
            return 0;
        }
        // otherwise continue with new position
    }

    // Fallback: guess D (should not happen)
    guess(D);
    return 0;
}