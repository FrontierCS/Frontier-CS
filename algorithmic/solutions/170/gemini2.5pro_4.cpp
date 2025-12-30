#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>
#include <set>
#include <tuple>

using namespace std;

// Globals for convenience
int N, L;
vector<int> T;

long long calculate_error(const vector<int>& a, const vector<int>& b) {
    vector<int> counts(N, 0);
    int current_cleaner = 0;
    for (int w = 0; w < L; ++w) {
        int last_cleaner = current_cleaner;
        counts[last_cleaner]++;
        if (w < L - 1) {
            int t = counts[last_cleaner];
            if (t % 2 != 0) {
                current_cleaner = a[last_cleaner];
            } else {
                current_cleaner = b[last_cleaner];
            }
        }
    }

    long long error = 0;
    for (int i = 0; i < N; ++i) {
        error += abs(counts[i] - T[i]);
    }
    return error;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::steady_clock::now();

    cin >> N >> L;
    T.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> T[i];
    }

    // --- Greedy Initial Solution ---
    vector<int> a(N), b(N);
    vector<tuple<int, int, int>> sources;
    for (int i = 0; i < N; ++i) {
        sources.emplace_back((T[i] + 1) / 2, i, 0); // for a_i
        sources.emplace_back(T[i] / 2, i, 1);       // for b_i
    }
    sort(sources.rbegin(), sources.rend());

    set<pair<int, int>> bins;
    for (int i = 0; i < N; ++i) {
        bins.insert({T[i] - (i == 0), i});
    }

    for (const auto& src : sources) {
        int size = get<0>(src);
        int j = get<1>(src);
        int type = get<2>(src);

        auto it = prev(bins.end());
        int capacity = it->first;
        int person_idx = it->second;
        bins.erase(it);

        if (type == 0) {
            a[j] = person_idx;
        } else {
            b[j] = person_idx;
        }
        bins.insert({capacity - size, person_idx});
    }

    // --- Simulated Annealing ---
    vector<int> best_a = a;
    vector<int> best_b = b;
    long long best_error = calculate_error(a, b);

    vector<int> current_a = a;
    vector<int> current_b = b;
    long long current_error = best_error;
    
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist_n(0, N - 1);
    uniform_int_distribution<int> dist_2(0, 1);
    uniform_real_distribution<double> dist_unif(0.0, 1.0);

    const double TIME_LIMIT_MS = 1950.0;
    double temp_start = 1000.0;
    double temp_end = 0.1;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed_ms = chrono::duration<double, milli>(now - start_time).count();
        if (elapsed_ms > TIME_LIMIT_MS) {
            break;
        }

        int i = dist_n(rng);
        int k = dist_n(rng);
        int type = dist_2(rng);
        
        vector<int> next_a = current_a;
        vector<int> next_b = current_b;
        int old_val;

        if (type == 0) {
            old_val = next_a[i];
            if(k == old_val) continue;
            next_a[i] = k;
        } else {
            old_val = next_b[i];
            if(k == old_val) continue;
            next_b[i] = k;
        }

        long long next_error = calculate_error(next_a, next_b);
        
        double progress = elapsed_ms / TIME_LIMIT_MS;
        double temp = temp_start * pow(temp_end / temp_start, progress);

        long long diff = next_error - current_error;
        if (diff < 0 || (temp > 1e-9 && dist_unif(rng) < exp(- (double)diff / temp))) {
            current_a = next_a;
            current_b = next_b;
            current_error = next_error;

            if (current_error < best_error) {
                best_error = current_error;
                best_a = current_a;
                best_b = current_b;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << best_a[i] << " " << best_b[i] << "\n";
    }

    return 0;
}