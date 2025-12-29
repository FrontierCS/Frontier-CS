#include <iostream>
#include <unordered_map>
#include <algorithm>
#include <string>

using namespace std;

using ll = long long;

ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // initial walk to get the starting vertex label
    cout << "walk 0" << endl;
    int start_label;
    cin >> start_label;

    unordered_map<int, ll> first_seen;   // label -> total distance when first seen
    first_seen[start_label] = 0;
    ll total = 0;
    int max_label = start_label;
    int walks = 0;
    const int MAX_WALKS = 200000;

    // we will collect multiples of n from collisions
    ll multiple_gcd = 0;
    int collisions = 0;
    int unchanged = 0;

    // pseudo‑random step generator
    unsigned long long rng = 123456789;
    const ll MOD = 1000000000;

    // first, do a walk of 1 to handle very small n
    cout << "walk 1" << endl;
    int label;
    cin >> label;
    total += 1;
    walks++;
    max_label = max(max_label, label);
    if (first_seen.count(label)) {
        ll diff = total - first_seen[label];
        if (diff > 0) {
            multiple_gcd = diff;
            collisions++;
        }
    } else {
        first_seen[label] = total;
    }

    // continue with pseudo‑random steps
    while (walks < MAX_WALKS) {
        rng = rng * 1103515245ULL + 12345ULL;
        ll step = (rng % MOD) + 1;   // step in [1, 10^9]
        cout << "walk " << step << endl;
        cin >> label;
        total += step;
        walks++;
        max_label = max(max_label, label);

        if (first_seen.count(label)) {
            ll diff = total - first_seen[label];
            if (diff > 0) {
                collisions++;
                if (multiple_gcd == 0) {
                    multiple_gcd = diff;
                } else {
                    ll new_gcd = gcd(multiple_gcd, diff);
                    if (new_gcd == multiple_gcd) {
                        unchanged++;
                    } else {
                        unchanged = 0;
                    }
                    multiple_gcd = new_gcd;
                }
                // early stop if we have enough collisions and the gcd stabilises
                if (collisions >= 20 && unchanged >= 5) {
                    break;
                }
            }
        } else {
            first_seen[label] = total;
        }
    }

    ll guess = multiple_gcd;
    if (guess == 0) {
        // fallback (should rarely happen)
        guess = max_label;
    }
    cout << "guess " << guess << endl;

    return 0;
}