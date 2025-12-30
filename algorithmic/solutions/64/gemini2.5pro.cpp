#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <random>
#include <chrono>
#include <algorithm>
#include <iomanip>

// Use __int128_t for large numbers to be safe, as sums can exceed long long.
using int128 = __int128_t;

// Custom input for __int128_t, since std::cin doesn't support it.
std::istream& operator>>(std::istream& is, int128& val) {
    std::string s;
    is >> s;
    val = 0;
    bool neg = false;
    size_t start_idx = 0;
    if (s.length() > 0 && s[0] == '-') {
        neg = true;
        start_idx = 1;
    }
    for (size_t i = start_idx; i < s.length(); ++i) {
        val = val * 10 + (s[i] - '0');
    }
    if (neg) {
        val = -val;
    }
    return is;
}

// Custom output for __int128_t
std::ostream& operator<<(std::ostream& os, const int128& val) {
    if (val == 0) return os << "0";
    std::string s = "";
    int128 tmp = val;
    bool neg = false;
    if (tmp < 0) {
        neg = true;
        tmp = -tmp;
    }
    while (tmp > 0) {
        s += (tmp % 10) + '0';
        tmp /= 10;
    }
    if (neg) {
        s += '-';
    }
    std::reverse(s.begin(), s.end());
    return os << s;
}


// Custom abs for __int128_t
int128 abs128(int128 val) {
    return val < 0 ? -val : val;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    int128 T;
    std::cin >> n >> T;
    std::vector<int128> a(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
    }

    auto start_time = std::chrono::high_resolution_clock::now();
    const double TIME_LIMIT_MS = 2850.0;

    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    std::vector<bool> current_selection(n, false);
    int128 current_sum = 0;

    // Initialize with a random subset of size roughly n/2
    // which is the expected size based on problem description.
    std::vector<int> p(n);
    std::iota(p.begin(), p.end(), 0);
    std::shuffle(p.begin(), p.end(), rng);
    int initial_size = n / 2;
    if (n > 0 && rng() % 2) {
        initial_size = (n + 1) / 2;
    }
    for (int i = 0; i < initial_size; ++i) {
        current_selection[p[i]] = true;
        current_sum += a[p[i]];
    }

    std::vector<bool> best_selection = current_selection;
    int128 best_error = abs128(current_sum - T);

    if (best_error == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << (best_selection[i] ? '1' : '0');
        }
        std::cout << std::endl;
        return 0;
    }

    // Simulated Annealing parameters
    // Initial temperature should be high enough to explore.
    // A value related to the scale of numbers (B) could be a good heuristic.
    long double temperature = 1e14;
    // Cooling rate should be close to 1 for slow cooling.
    long double cooling_rate = 0.9999998;
    
    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        double elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time).count();
        if (elapsed_ms > TIME_LIMIT_MS) {
            break;
        }

        // Pick a random element to flip
        int idx = rng() % n;

        int128 next_sum = current_sum;
        if (current_selection[idx]) {
            next_sum -= a[idx];
        } else {
            next_sum += a[idx];
        }

        int128 current_error = abs128(current_sum - T);
        int128 next_error = abs128(next_sum - T);
        
        // If the new state is better, always accept it.
        if (next_error < current_error) {
            current_sum = next_sum;
            current_selection[idx] = !current_selection[idx];
            if (next_error < best_error) {
                best_error = next_error;
                best_selection = current_selection;
                if (best_error == 0) {
                    break;
                }
            }
        } else {
            // If the new state is worse, accept it with a certain probability.
            long double delta_error = (long double)(next_error - current_error);
            long double p = expl(-delta_error / temperature);
            if (std::uniform_real_distribution<long double>(0.0, 1.0)(rng) < p) {
                current_sum = next_sum;
                current_selection[idx] = !current_selection[idx];
            }
        }
        
        temperature *= cooling_rate;
    }

    for (int i = 0; i < n; ++i) {
        std::cout << (best_selection[i] ? '1' : '0');
    }
    std::cout << std::endl;

    return 0;
}