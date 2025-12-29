#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    const int MAX_WALKS = 200000;
    long long total_steps = 0;
    int walk_count = 0;

    auto do_walk = [&](long long x) -> int {
        cout << "walk " << x << endl;
        cout.flush();
        int v;
        if (!(cin >> v)) exit(0);
        ++walk_count;
        total_steps += x;
        return v;
    };

    // Initial position (step 0)
    long long current_step = 0;
    unordered_map<int, long long> first_seen;
    first_seen.reserve(200000 * 2);
    first_seen.max_load_factor(0.7f);

    int start_label = do_walk(0);
    first_seen[start_label] = 0;

    long long g = 0;          // gcd of all found multiples of n
    int collisions = 0;

    const int TARGET_COLLISIONS = 15;  // enough for very high probability
    const int MAX_QUERIES_FOR_SEARCH = MAX_WALKS; // we can use all

    while (walk_count < MAX_QUERIES_FOR_SEARCH) {
        // random step in [1, 1e9]
        long long x = uniform_int_distribution<long long>(1, 1000000000LL)(rng);
        int label = do_walk(x);
        auto it = first_seen.find(label);
        if (it != first_seen.end()) {
            long long D = total_steps - it->second;
            if (D > 0) {
                if (g == 0) g = D;
                else g = std::gcd(g, D);
                ++collisions;
            }
        } else {
            first_seen[label] = total_steps;
        }

        if (collisions >= TARGET_COLLISIONS && g > 0 && g <= 1000000000LL) {
            break;
        }
    }

    long long guess_n;
    if (g == 0) {
        // No collision found: n is likely very large; best guess is upper bound
        guess_n = 1000000000LL;
    } else if (g > 1000000000LL) {
        // g is multiple of n, but larger than allowed maximum; clamp
        // choose random divisor <= 1e9 (simple fallback: min(g,1e9))
        guess_n = min(g, 1000000000LL);
    } else {
        guess_n = g;
    }

    cout << "guess " << guess_n << endl;
    cout.flush();

    return 0;
}