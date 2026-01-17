#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <string>

using namespace std;
using ll = long long;

int n;
ll T;
vector<ll> a;

void solve_mitm() {
    int k = n / 2;
    vector<pair<ll, ll>> sums1;
    sums1.reserve(1 << k);
    for (ll i = 0; i < (1LL << k); ++i) {
        ll current_sum = 0;
        for (int j = 0; j < k; ++j) {
            if ((i >> j) & 1) {
                current_sum += a[j];
            }
        }
        sums1.push_back({current_sum, i});
    }

    int rem = n - k;
    vector<pair<ll, ll>> sums2;
    sums2.reserve(1 << rem);
    for (ll i = 0; i < (1LL << rem); ++i) {
        ll current_sum = 0;
        for (int j = 0; j < rem; ++j) {
            if ((i >> j) & 1) {
                current_sum += a[k + j];
            }
        }
        sums2.push_back({current_sum, i});
    }

    sort(sums2.begin(), sums2.end());

    ll min_diff = -1;
    ll best_mask = 0;
    ll best_sum = -1;

    for (const auto& p1 : sums1) {
        ll s1 = p1.first;
        ll m1 = p1.second;
        ll target2 = T - s1;

        auto it = lower_bound(sums2.begin(), sums2.end(), make_pair(target2, 0LL));

        if (it != sums2.end()) {
            ll s2 = it->first;
            ll m2 = it->second;
            ll current_sum = s1 + s2;
            ll current_diff = abs(current_sum - T);
            if (min_diff == -1 || current_diff < min_diff || (current_diff == min_diff && current_sum < best_sum)) {
                min_diff = current_diff;
                best_sum = current_sum;
                best_mask = (m2 << k) | m1;
            }
        }
        if (it != sums2.begin()) {
            it--;
            ll s2 = it->first;
            ll m2 = it->second;
            ll current_sum = s1 + s2;
            ll current_diff = abs(current_sum - T);
            if (min_diff == -1 || current_diff < min_diff || (current_diff == min_diff && current_sum < best_sum)) {
                min_diff = current_diff;
                best_sum = current_sum;
                best_mask = (m2 << k) | m1;
            }
        }
    }
    
    string result = "";
    for (int i = 0; i < n; ++i) {
        if ((best_mask >> i) & 1) {
            result += '1';
        } else {
            result += '0';
        }
    }
    cout << result << endl;
}

void solve_sa() {
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    string best_solution(n, '0');
    ll best_sum = 0;

    // Start with a randomized greedy solution
    vector<pair<ll, int>> a_indexed(n);
    for(int i = 0; i < n; ++i) a_indexed[i] = {a[i], i};

    shuffle(a_indexed.begin(), a_indexed.end(), rng);
    
    for (const auto& p : a_indexed) {
        if (abs(best_sum + p.first - T) < abs(best_sum - T)) {
            best_sum += p.first;
            best_solution[p.second] = '1';
        }
    }

    string current_solution = best_solution;
    ll current_sum = best_sum;
    ll min_diff = abs(best_sum - T);
    
    if (min_diff == 0) {
        cout << best_solution << endl;
        return;
    }

    double temp = 0;
    if (n > 0) {
        for(ll val : a) temp += val;
        temp /= n;
    }
    temp = max(temp, 1.0);

    double cooling_rate = 0.999995;

    auto start_time = chrono::high_resolution_clock::now();
    uniform_int_distribution<int> dist_idx(0, n - 1);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    while(chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - start_time).count() < 1900) {
        int flips = (dist_prob(rng) < 0.2 && n > 1) ? 2 : 1;
        
        string next_solution = current_solution;
        ll next_sum = current_sum;

        int idx1 = dist_idx(rng);
        if (next_solution[idx1] == '1') {
            next_solution[idx1] = '0';
            next_sum -= a[idx1];
        } else {
            next_solution[idx1] = '1';
            next_sum += a[idx1];
        }

        if (flips == 2) {
            int idx2 = dist_idx(rng);
            while (idx2 == idx1) idx2 = dist_idx(rng);
             if (next_solution[idx2] == '1') {
                next_solution[idx2] = '0';
                next_sum -= a[idx2];
            } else {
                next_solution[idx2] = '1';
                next_sum += a[idx2];
            }
        }
        
        ll current_diff = abs(current_sum - T);
        ll next_diff = abs(next_sum - T);

        if (next_diff < current_diff) {
            current_sum = next_sum;
            current_solution = next_solution;
        } else {
            double ap = exp((double)(current_diff - next_diff) / temp);
            if (dist_prob(rng) < ap) {
                current_sum = next_sum;
                current_solution = next_solution;
            }
        }
        
        if (abs(current_sum - T) < min_diff) {
            min_diff = abs(current_sum - T);
            best_solution = current_solution;
            if (min_diff == 0) break;
        }
        
        temp *= cooling_rate;
    }

    cout << best_solution << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> T;
    a.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }
    
    if (n <= 44) {
        solve_mitm();
    } else {
        solve_sa();
    }

    return 0;
}