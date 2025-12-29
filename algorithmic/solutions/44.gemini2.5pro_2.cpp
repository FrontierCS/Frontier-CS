#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

using namespace std;

struct City {
    long long x, y;
};

vector<City> cities;
vector<bool> is_prime;

inline double dist(int c1_id, int c2_id) {
    long long dx = cities[c1_id].x - cities[c2_id].x;
    long long dy = cities[c1_id].y - cities[c2_id].y;
    return sqrt((double)dx * dx + (double)dy * dy);
}

void sieve(int n) {
    is_prime.assign(n + 1, true);
    if (n >= 0) is_prime[0] = false;
    if (n >= 1) is_prime[1] = false;
    for (int p = 2; p * p <= n; ++p) {
        if (is_prime[p]) {
            for (int i = p * p; i <= n; i += p)
                is_prime[i] = false;
        }
    }
}

// Helper to get city ID from tour index, handling tour boundaries (start/end at city 0)
int get_city(int tour_idx, int n, const vector<int>& tour) {
    if (tour_idx < 0) {
        return 0;
    }
    if (tour_idx >= n - 1) {
        return 0;
    }
    return tour[tour_idx];
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    cities.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> cities[i].x >> cities[i].y;
    }

    if (n < 2) {
        cout << n + 1 << "\n";
        if (n > 0) cout << 0 << "\n";
        cout << 0 << "\n";
        return 0;
    }

    sieve(n);

    vector<int> tour(n - 1);
    iota(tour.begin(), tour.end(), 1);

    const int W = 500;

    for (int k = 1; ; ++k) {
        int step = 10 * k;
        if (step > n) break;
        int crit_tour_idx = step - 2;
        if (crit_tour_idx >= n - 1) break;

        int city_at_crit = tour[crit_tour_idx];
        if (!is_prime[city_at_crit]) {
            double best_delta = 0;
            int best_j = -1;
            
            int i = crit_tour_idx;
            int u = city_at_crit;

            int start_j = max(0, i - W);
            int end_j = min((int)tour.size() - 1, i + W);

            for (int j = start_j; j <= end_j; ++j) {
                if (i == j) continue;
                
                int city_to_swap = tour[j];
                // Path index of tour[j] is j+1. Step j+2 starts from tour[j].
                // Avoid moving a prime from another critical spot.
                int step_for_j = j + 2; 
                if (is_prime[city_to_swap] && (step_for_j % 10 != 0)) {
                    int v = city_to_swap;
                    
                    double dist_delta;
                    if (j == i + 1) { // adjacent, i then j
                        int prev_i = get_city(i - 1, n, tour);
                        int next_j = get_city(j + 1, n, tour);
                        dist_delta = dist(prev_i, v) + dist(u, next_j) - (dist(prev_i, u) + dist(v, next_j));
                    } else if (i == j + 1) { // adjacent, j then i
                        int prev_j = get_city(j - 1, n, tour);
                        int next_i = get_city(i + 1, n, tour);
                        dist_delta = dist(prev_j, u) + dist(v, next_i) - (dist(prev_j, v) + dist(u, next_i));
                    } else { // non-adjacent
                        int prev_i = get_city(i - 1, n, tour);
                        int next_i = get_city(i + 1, n, tour);
                        int prev_j = get_city(j - 1, n, tour);
                        int next_j = get_city(j + 1, n, tour);
                        dist_delta = dist(prev_i, v) + dist(v, next_i) + dist(prev_j, u) + dist(u, next_j)
                                     - (dist(prev_i, u) + dist(u, next_i) + dist(prev_j, v) + dist(v, next_j));
                    }

                    int next_i_city = get_city(i + 1, n, tour);
                    double penalty_delta = -0.1 * dist(u, next_i_city);
                    
                    double total_delta = dist_delta + penalty_delta;
                    
                    if (total_delta < best_delta) {
                        best_delta = total_delta;
                        best_j = j;
                    }
                }
            }
            if (best_j != -1) {
                swap(tour[i], tour[best_j]);
            }
        }
    }

    cout << n + 1 << "\n";
    cout << 0 << "\n";
    for (int city_id : tour) {
        cout << city_id << "\n";
    }
    cout << 0 << "\n";

    return 0;
}