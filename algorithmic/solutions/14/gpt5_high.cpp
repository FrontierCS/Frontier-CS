#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto ask_walk = [&](int64 x) -> int64 {
        cout << "walk " << x << endl;
        cout.flush();
        int64 label;
        if (!(cin >> label)) {
            exit(0);
        }
        return label;
    };
    auto do_guess = [&](int64 g) {
        cout << "guess " << g << endl;
        cout.flush();
        exit(0);
    };

    const int MAX_WALKS = 200000;
    int walks_used = 0;

    // Get starting label
    int64 start_label = ask_walk(0);
    walks_used++;

    unordered_map<int64, int64> first_time;
    first_time.reserve(300000);
    first_time.max_load_factor(0.7f);
    first_time[start_label] = 0;

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<int64> dist(1, 1000000000LL);

    int64 total_steps = 0;
    int64 g = 0;
    int collisions = 0;
    int target_collisions = 6; // Aiming for high probability gcd(k_i)=1 while staying under query limit

    while (walks_used < MAX_WALKS && collisions < target_collisions) {
        int64 x = dist(rng);
        total_steps += x;
        int64 label = ask_walk(x);
        walks_used++;

        auto it = first_time.find(label);
        if (it == first_time.end()) {
            first_time[label] = total_steps;
        } else {
            int64 diff = total_steps - it->second;
            g = std::gcd(g, diff);
            collisions++;
        }
    }

    // If we can still afford more queries and g is suspiciously large (multiple of n),
    // try to reduce it with a few extra collisions for better confidence.
    // We won't exceed MAX_WALKS.
    int extra_attempts = 5;
    while (walks_used < MAX_WALKS && extra_attempts-- > 0) {
        int64 x = dist(rng);
        total_steps += x;
        int64 label = ask_walk(x);
        walks_used++;

        auto it = first_time.find(label);
        if (it == first_time.end()) {
            first_time[label] = total_steps;
        } else {
            int64 diff = total_steps - it->second;
            g = std::gcd(g, diff);
        }
    }

    if (g == 0) {
        // No collision found (extremely unlikely with limits). Fallback guess 1.
        do_guess(1);
    } else {
        // g is a multiple of n; with high probability equals n after several collisions
        // If g > 1e9 (invalid guess), try a few more collisions to reduce it.
        while (g > 1000000000LL && walks_used < MAX_WALKS) {
            int64 x = dist(rng);
            total_steps += x;
            int64 label = ask_walk(x);
            walks_used++;
            auto it = first_time.find(label);
            if (it == first_time.end()) {
                first_time[label] = total_steps;
            } else {
                int64 diff = total_steps - it->second;
                g = std::gcd(g, diff);
            }
        }
        if (g == 0) g = 1;
        if (g > 1000000000LL) g = 1000000000LL; // best effort fallback
        do_guess(g);
    }

    return 0;
}