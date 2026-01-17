#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <random>
#include <chrono>

using namespace std;

typedef long long ll;

int n;
ll T;
vector<ll> a;
vector<int> best_subset;
ll best_error = -1;

void solve_small(int idx, ll current_sum, vector<int>& current_subset) {
    if (idx == n) {
        ll err = abs(current_sum - T);
        if (best_error == -1 || err < best_error) {
            best_error = err;
            best_subset = current_subset;
        }
        return;
    }

    current_subset[idx] = 0;
    solve_small(idx + 1, current_sum, current_subset);
    if (best_error == 0) return;

    current_subset[idx] = 1;
    solve_small(idx + 1, current_sum + a[idx], current_subset);
    if (best_error == 0) return;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> T)) return 0;

    a.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    best_subset.resize(n, 0);
    best_error = abs(0 - T);

    if (best_error == 0) {
        for (int i = 0; i < n; ++i) cout << best_subset[i];
        cout << endl;
        return 0;
    }

    if (n <= 20) {
        vector<int> sub(n);
        solve_small(0, 0, sub);
        for (int i = 0; i < n; ++i) cout << best_subset[i];
        cout << endl;
        return 0;
    }

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto start_time = chrono::steady_clock::now();
    double time_limit = 0.92; 

    vector<int> current_subset(n);
    vector<int> ones; ones.reserve(n);
    vector<int> zeros; zeros.reserve(n);

    while (true) {
        auto curr_time = chrono::steady_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if (elapsed.count() > time_limit) break;

        ll current_sum = 0;
        for (int i = 0; i < n; ++i) {
            current_subset[i] = rng() % 2; 
            if (current_subset[i]) current_sum += a[i];
        }

        ll current_error = abs(current_sum - T);
        
        if (current_error < best_error) {
            best_error = current_error;
            best_subset = current_subset;
            if (best_error == 0) goto end_search;
        }

        bool improved = true;
        while (improved) {
            improved = false;
            
            ll best_new_error = current_error;
            int best_flip_idx = -1;

            for (int i = 0; i < n; ++i) {
                ll val = (current_subset[i] ? -a[i] : a[i]);
                ll new_err = abs(current_sum + val - T);
                if (new_err < best_new_error) {
                    best_new_error = new_err;
                    best_flip_idx = i;
                }
            }

            if (best_flip_idx != -1 && best_new_error < current_error) {
                current_subset[best_flip_idx] = 1 - current_subset[best_flip_idx];
                current_sum += (current_subset[best_flip_idx] ? a[best_flip_idx] : -a[best_flip_idx]);
                current_error = best_new_error;
                improved = true;
                
                if (current_error < best_error) {
                    best_error = current_error;
                    best_subset = current_subset;
                    if (best_error == 0) goto end_search;
                }
                continue; 
            }

            ones.clear();
            zeros.clear();
            for(int i=0; i<n; ++i) {
                if(current_subset[i]) ones.push_back(i);
                else zeros.push_back(i);
            }

            best_new_error = current_error;
            int best_swap_one = -1;
            int best_swap_zero = -1;

            for (int i : ones) {
                for (int j : zeros) {
                    ll delta = a[j] - a[i];
                    ll new_err = abs(current_sum + delta - T);
                    if (new_err < best_new_error) {
                        best_new_error = new_err;
                        best_swap_one = i;
                        best_swap_zero = j;
                    }
                }
            }

            if (best_swap_one != -1 && best_new_error < current_error) {
                current_subset[best_swap_one] = 0;
                current_subset[best_swap_zero] = 1;
                current_sum += (a[best_swap_zero] - a[best_swap_one]);
                current_error = best_new_error;
                improved = true;

                if (current_error < best_error) {
                    best_error = current_error;
                    best_subset = current_subset;
                    if (best_error == 0) goto end_search;
                }
            }
        }
    }

    end_search:
    for (int i = 0; i < n; ++i) cout << best_subset[i];
    cout << endl;

    return 0;
}