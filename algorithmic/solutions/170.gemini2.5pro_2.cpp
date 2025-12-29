#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <random>
#include <chrono>
#include <algorithm>

// Constants are fixed as per the problem statement
const int N_CONST = 100;
const int L_CONST = 500000;
int N, L; // Read from input, but will be N_CONST, L_CONST
std::vector<int> T;

// Random Number Generator
std::mt19937 rng;

// Evaluation function: simulates the process and calculates total error
long long calculate_error(const std::vector<int>& ab) {
    std::vector<int> counts(N_CONST, 0);
    int current_employee = 0;
    for (int week = 0; week < L_CONST; ++week) {
        counts[current_employee]++;
        int t_x = counts[current_employee];
        if (t_x % 2 != 0) { // odd
            current_employee = ab[current_employee * 2];
        } else { // even
            current_employee = ab[current_employee * 2 + 1];
        }
    }
    long long error = 0;
    for (int i = 0; i < N_CONST; ++i) {
        error += std::abs(counts[i] - T[i]);
    }
    return error;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    // Seed RNG
    rng.seed(std::chrono::high_resolution_clock::now().time_since_epoch().count());

    // Read input
    std::cin >> N >> L;
    T.resize(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> T[i];
    }

    // 1. Initial solution using Largest Remainder Method
    std::vector<int> ab(2 * N);
    {
        std::vector<double> target_degrees(N);
        for (int i = 0; i < N; ++i) {
            target_degrees[i] = (double)T[i] / L * (2 * N);
        }

        std::vector<int> degrees(N);
        int current_sum = 0;
        std::vector<std::pair<double, int>> remainders;
        remainders.reserve(N);
        for (int i = 0; i < N; ++i) {
            degrees[i] = floor(target_degrees[i]);
            current_sum += degrees[i];
            remainders.push_back({target_degrees[i] - degrees[i], i});
        }

        std::sort(remainders.rbegin(), remainders.rend());

        int to_distribute = 2 * N - current_sum;
        for (int i = 0; i < to_distribute; ++i) {
            degrees[remainders[i].second]++;
        }

        std::vector<int> destinations;
        destinations.reserve(2 * N);
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < degrees[i]; ++j) {
                destinations.push_back(i);
            }
        }
        std::shuffle(destinations.begin(), destinations.end(), rng);
        ab = destinations;
    }

    long long current_error = calculate_error(ab);
    std::vector<int> best_ab = ab;
    long long best_error = current_error;

    // 2. Simulated Annealing
    double time_limit = 2.8; 
    auto start_time = std::chrono::high_resolution_clock::now();
    
    double start_temp = 500;
    double end_temp = 0.1;

    std::uniform_int_distribution<int> move_dist(0, 99);
    std::uniform_int_distribution<int> idx_dist(0, 2 * N - 1);
    std::uniform_int_distribution<int> val_dist(0, N - 1);
    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);

    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        double elapsed = std::chrono::duration<double>(current_time - start_time).count();
        if (elapsed > time_limit) break;

        double temp = start_temp * (1.0 - elapsed / time_limit) + end_temp * (elapsed / time_limit);

        std::vector<int> next_ab = ab;
        
        int move_type = move_dist(rng);
        int i, j;
        if (move_type < 90) { // Swap move (90% chance)
            i = idx_dist(rng);
            do {
                j = idx_dist(rng);
            } while (i == j);
            std::swap(next_ab[i], next_ab[j]);
        } else { // Change move (10% chance)
            i = idx_dist(rng);
            int old_val = next_ab[i];
            do {
                j = val_dist(rng);
            } while (j == old_val);
            next_ab[i] = j;
        }

        long long next_error = calculate_error(next_ab);
        
        double probability = std::exp((double)(current_error - next_error) / temp);

        if (prob_dist(rng) < probability) {
            ab = next_ab;
            current_error = next_error;
            if (current_error < best_error) {
                best_error = current_error;
                best_ab = ab;
            }
        }
    }
    
    // 3. Output
    for (int i = 0; i < N; ++i) {
        std::cout << best_ab[2 * i] << " " << best_ab[2 * i + 1] << "\n";
    }

    return 0;
}