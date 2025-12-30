#include <bits/stdc++.h>
using namespace std;
using ll = long long;

const int B = 31627; // prime near sqrt(1e9)

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll cumulative = 0;
    unordered_map<ll, ll> baby; // label -> step count from start
    vector<ll> diffs;

    // Get starting label
    cout << "walk 0" << endl;
    ll label;
    cin >> label;
    ll start_label = label;
    baby[label] = 0;

    // Baby steps: walk 1 step at a time, record labels and steps
    for (int i = 1; i < B; ++i) {
        cout << "walk 1" << endl;
        cin >> label;
        cumulative += 1;
        if (baby.count(label)) {
            ll d = cumulative - baby[label];
            if (d > 0) diffs.push_back(d);
        } else {
            baby[label] = cumulative;
        }
    }

    // Giant steps: try to find a collision with baby steps
    ll D = 0;
    for (int k = 1; k <= B; ++k) {
        ll target = k * B;
        ll step = target - cumulative;
        cout << "walk " << step << endl;
        cin >> label;
        cumulative += step; // cumulative becomes target
        if (baby.count(label)) {
            ll j = baby[label];
            D = target - j;
            diffs.push_back(D);
            break;
        }
    }

    // Choose the smallest positive multiple found
    if (diffs.empty()) {
        // Fallback (should almost never happen)
        cout << "guess 1" << endl;
        return 0;
    }
    D = *min_element(diffs.begin(), diffs.end());

    // Return to the starting vertex using D
    ll t_return = (D - (cumulative % D)) % D;
    if (t_return > 0) {
        cout << "walk " << t_return << endl;
        cin >> label; // should be start_label
        cumulative += t_return;
    }

    // Factor D and collect its divisors
    vector<ll> divisors;
    for (ll i = 1; i * i <= D; ++i) {
        if (D % i == 0) {
            divisors.push_back(i);
            if (i * i != D) {
                divisors.push_back(D / i);
            }
        }
    }
    sort(divisors.begin(), divisors.end());

    // Test divisors in increasing order until we find n
    ll n_candidate = 1;
    for (ll d : divisors) {
        if (d > 1e9) break; // n cannot exceed 1e9
        cout << "walk " << d << endl;
        cin >> label;
        if (label == start_label) {
            n_candidate = d;
            break;
        } else {
            // Go back to start
            cout << "walk " << (D - d) << endl;
            cin >> label; // should be start_label
        }
    }

    cout << "guess " << n_candidate << endl;
    return 0;
}